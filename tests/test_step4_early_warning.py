"""
Step 4 Verification: Early Warning Delay Radar & Fund Lapse Forecasting
Verifies:
1. MoSPI 2023 Para 4.6 Statutory 18-Month (540-Day) Horizon Evaluator.
2. Fiscal Year-End Fund Lapse Risk Forecasting Model.
3. Pre-Sanction Simulator API (/api/interceptor/simulate) blocking horizon breaches (>540 days).
4. Dataset columns, distributions, and server-side forensic masking.
5. Multi-tier UI wiring in Ministry, State Nodal, and District consoles.
"""

import sys
import os
import pandas as pd

# Fix Windows console UTF-8 encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from client import KautilyaAPIClient
from backend.rules.compliance import evaluate_execution_horizon, forecast_fund_lapse_risk

def test_early_warning_delay_radar():
    print("================================================================================")
    print("  STEP 4 VERIFICATION: EARLY WARNING DELAY RADAR & FUND LAPSE FORECASTING       ")
    print("================================================================================")

    # 1. Test MoSPI Para 4.6 Statutory Horizon Evaluator
    print("\n[Step 1] Testing MoSPI Para 4.6 Statutory 18-Month (540-Day) Horizon Engine...")
    
    # Case A: Statutory Horizon Breach (>540 Days)
    h_breach = evaluate_execution_horizon(days=580, status="In Progress")
    assert h_breach["horizon_breach"] is True, "580 days must trigger horizon breach"
    assert h_breach["status_code"] == "STATUTORY_BREACH"
    assert h_breach["days_over_limit"] == 40
    print(f"  [OK] Statutory Breach (580d): Flagged breach with {h_breach['days_over_limit']} days over limit.")

    # Case B: Critical Delay (365 - 540 Days)
    h_crit = evaluate_execution_horizon(days=420, status="In Progress")
    assert h_crit["horizon_breach"] is False
    assert h_crit["status_code"] == "CRITICAL_DELAY"
    assert "Critical Delay" in h_crit["delay_severity"]
    print(f"  [OK] Critical Delay (420d): Categorized as {h_crit['delay_severity']}.")

    # Case C: Milestone Watchlist (270 - 365 Days)
    h_watch = evaluate_execution_horizon(days=310, status="In Progress")
    assert h_watch["horizon_breach"] is False
    assert h_watch["status_code"] == "WATCHLIST"
    print(f"  [OK] Milestone Watchlist (310d): Categorized as {h_watch['delay_severity']}.")

    # Case D: On Schedule (<270 Days)
    h_norm = evaluate_execution_horizon(days=160, status="In Progress")
    assert h_norm["horizon_breach"] is False
    assert h_norm["status_code"] == "NORMAL"
    print(f"  [OK] On Schedule (160d): Categorized as {h_norm['delay_severity']}.")

    # Case E: Completed project (never flags breach)
    h_comp = evaluate_execution_horizon(days=620, status="Completed")
    assert h_comp["horizon_breach"] is False
    assert h_comp["status_code"] == "COMPLETED"
    print("  [OK] Completed Project (620d): Cleared with status COMPLETED.")

    # 2. Test Fiscal Year-End Fund Lapse Risk Forecasting Model
    print("\n[Step 2] Testing Fiscal Year-End Fund Lapse Risk Forecasting Model...")
    
    # Case A: High Lapse Risk (Breached + Stalled + High Unspent + Suspect Vendor)
    lapse_high = forecast_fund_lapse_risk(
        sanctioned_amount=5_000_000,
        uc_amount=1_000_000,
        execution_days=580,
        status="Stalled",
        risk_level="High",
        vendor_is_suspect=1
    )
    assert lapse_high["lapse_risk_level"] == "High"
    assert lapse_high["lapse_risk_pct"] >= 65.0
    assert lapse_high["surrender_risk"] is True
    print(f"  [OK] High Lapse Risk Case: Score={lapse_high['lapse_risk_pct']}% (Level: {lapse_high['lapse_risk_level']}), Unspent=INR {lapse_high['unspent_balance']:,.2f}.")

    # Case B: Completed Project (Zero Lapse Risk)
    lapse_comp = forecast_fund_lapse_risk(
        sanctioned_amount=5_000_000,
        uc_amount=5_000_000,
        execution_days=180,
        status="Completed"
    )
    assert lapse_comp["lapse_risk_pct"] == 0.0
    assert lapse_comp["lapse_risk_level"] == "Low"
    assert lapse_comp["surrender_risk"] is False
    print(f"  [OK] Completed Work Case: Score={lapse_comp['lapse_risk_pct']}% (Level: {lapse_comp['lapse_risk_level']}).")

    # 3. Test Pre-Sanction Interceptor API (/api/interceptor/simulate)
    print("\n[Step 3] Testing Real-Time Interceptor Timeline Validation...")
    try:
        client = KautilyaAPIClient()
        sim_breach = client.simulate_sanction_risk(
            work_type="School Building",
            sanctioned_amount=3_500_000,
            days_to_completion=600,
            description="Construction of Senior Secondary School Wing"
        )
    except Exception:
        from fastapi.testclient import TestClient
        from backend.main import app as fastapi_app
        tc = TestClient(fastapi_app)
        resp = tc.post("/api/interceptor/simulate", json={
            "work_type": "School Building",
            "sanctioned_amount": 3_500_000,
            "days_to_completion": 600,
            "description": "Construction of Senior Secondary School Wing"
        })
        sim_breach = resp.json()

    assert sim_breach.get("is_horizon_breach") is True, "Must flag horizon breach when days > 540"
    assert sim_breach.get("risk_level") == "High", "Horizon breach must escalate to High Risk"
    assert "Statutory Horizon Breach" in str(sim_breach.get("triggered_rules")), "Must record Horizon Breach rule trigger"
    assert "STATUTORY REJECT" in sim_breach.get("verdict", ""), "Verdict must cite statutory rejection"
    print(f"  [OK] Interceptor API: Blocked proposed 600-day project: {sim_breach['verdict'][:55]}...")

    # 4. Test Dataframe Schema & Masking in app.py
    print("\n[Step 4] Checking dataset schema, distributions, and forensic masking in app.py...")
    import app
    df = app.load_data()
    
    expected_cols = [
        "Execution_Days", "Horizon_Breach", "Delay_Severity",
        "Unspent_Balance", "Unspent_Balance_Pct", "Lapse_Risk_Pct", "Lapse_Risk_Level"
    ]
    for col in expected_cols:
        assert col in df.columns, f"Missing expected column in df: {col}"

    breach_count = int(df["Horizon_Breach"].sum())
    assert breach_count > 0, "Must detect historical horizon breaches (>540 days)"
    high_lapse_count = int((df["Lapse_Risk_Level"] == "High").sum())
    assert high_lapse_count > 0, "Must detect projects with high fund lapse risk"
    print(f"  [OK] Historical Breaches Detected: {breach_count} works (>540 Days)")
    print(f"  [OK] High Fund Lapse Risk Works: {high_lapse_count} works")

    # Test server-side masking
    masked = app.mask_forensics(df)
    for hidden_col in ["Horizon_Breach", "Delay_Severity", "Lapse_Risk_Pct", "Lapse_Risk_Level"]:
        assert hidden_col not in masked.columns, f"Forensic column {hidden_col} must be masked from citizen tier"
    assert "Unspent_Balance" in masked.columns, "Operational Unspent_Balance should remain visible"
    print("  [OK] Server-side forensic masking verified: Delay horizon alerts withheld from public tier.")

    # 5. Check UI Wiring across All Dashboards in app.py
    print("\n[Step 5] Checking UI Wiring in app.py...")
    with open("app.py", "r", encoding="utf-8") as f:
        app_code = f.read()

    assert "Early Warning Delay & Fund Lapse Radar" in app_code, "Delay radar tab must exist in render_ministry_macro"
    assert "Project Execution Horizon Distribution" in app_code, "Histogram must exist in delay radar tab"
    assert "Capital Lapse Risk Matrix" in app_code, "Scatter plot must exist in delay radar tab"
    assert "STATUTORY HORIZON ALERT" in app_code, "State Nodal console must feature delay alert banner"
    assert "STATUTORY HORIZON BREACH (MoSPI Para 4.6)" in app_code, "District console must feature statutory breach escalation"
    print("  [OK] All UI tabs, visual charts, and role-specific escalation banners verified.")

    print("\n================================================================================")
    print(" STEP 4 VERIFICATION SUCCESSFUL: 100% PASS (DELAY RADAR & LAPSE ENGINE ACTIVE) ")
    print("================================================================================")

if __name__ == "__main__":
    test_early_warning_delay_radar()
