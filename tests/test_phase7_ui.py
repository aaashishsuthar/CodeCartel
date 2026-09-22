"""
Phase 7 Verification: Live Government Telemetry & Ingestion Console in Streamlit
Tests all UI-backend connectors, live government telemetry endpoints, LGD match sandbox,
and pre-sanction fraud interceptor simulation.
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

def test_phase7_frontend_integration():
    print("================================================================================")
    print("PHASE 7 VERIFICATION: STREAMLIT LIVE TELEMETRY & INGESTION CONSOLE")
    print("================================================================================")

    api = KautilyaAPIClient()

    # 1. Verify Harvester Status Telemetry
    print("\n[Step 1] Testing get_harvester_status()...")
    h_stat = api.get_harvester_status()
    assert h_stat.get("database_connected") is True, "Database must be connected"
    assert h_stat.get("total_mps_stored", 0) >= 620, "Must track at least 620 MPs"
    assert h_stat.get("live_government_works_stored", 0) >= 180, "Must have live harvested works"
    print(f"  --> Harvester Telemetry OK: {h_stat['total_mps_stored']} MPs, {h_stat['live_government_works_stored']} live works.")

    # 2. Verify Cleaner & LGD Statistics
    print("\n[Step 2] Testing get_cleaner_stats()...")
    c_stat = api.get_cleaner_stats()
    assert c_stat.get("data_quality_score", 0) > 60.0, "Quality score must be acceptable"
    assert c_stat.get("lgd_district_coded_count", 0) > 0, "Must have LGD district coded records"
    print(f"  --> Cleaner Stats OK: Quality Score = {c_stat['data_quality_score']}, LGD Match Rate = {c_stat['lgd_district_match_rate_pct']}%.")

    # 3. Verify Live Works DataFrame Retrieval
    print("\n[Step 3] Testing get_live_works(limit=10, as_df=True)...")
    live_df = api.get_live_works(limit=10, as_df=True)
    assert isinstance(live_df, pd.DataFrame), "Result must be a DataFrame"
    assert len(live_df) > 0, "Must return at least 1 live work"
    required_cols = ["project_id", "mp_name", "constituency", "sanctioned_amount", "risk_score", "risk_level"]
    for col in required_cols:
        assert col in live_df.columns, f"Missing required column {col}"
    print(f"  --> Live Works OK: Fetched {len(live_df)} records with full forensic schema.")

    # 4. Verify MoSPI eSAKSHI State Telemetry
    print("\n[Step 4] Testing get_mospi_telemetry(as_df=True)...")
    mospi_df = api.get_mospi_telemetry(as_df=True)
    assert isinstance(mospi_df, pd.DataFrame), "Result must be a DataFrame"
    assert len(mospi_df) >= 36, "Must cover all 36 States/UTs"
    assert "avg_utilization_pct" in mospi_df.columns, "Must have utilization percentage"
    print(f"  --> MoSPI Telemetry OK: Ingested {len(mospi_df)} States/UTs from mplads.mospi.gov.in.")

    # 5. Verify Interactive LGD Matcher Sandbox
    print("\n[Step 5] Testing lookup_lgd('Varanasi')...")
    lgd_res = api.lookup_lgd("Varanasi", "Uttar Pradesh")
    assert lgd_res.get("lgd_district_code") == 178, f"Expected 178 for Varanasi, got {lgd_res.get('lgd_district_code')}"
    print(f"  --> LGD Sandbox OK: Matched '{lgd_res['query_district']}' -> Code {lgd_res['lgd_district_code']} ({lgd_res['match_status']}).")

    # 6. Verify Real-Time Pre-Sanction Interceptor Simulation
    print("\n[Step 6] Testing simulate_sanction_risk() for High-Risk and Compliant Cases...")
    high_risk_sim = api.simulate_sanction_risk(
        work_type="Road Construction",
        sanctioned_amount=9500000.0, # Benchmark is 3.5M -> 2.7x inflation
        days_to_completion=220,
        vendor="Vendor_004" # Suspect vendor
    )
    assert high_risk_sim.get("risk_level") == "High", "Must flag inflated cost as High risk"
    assert "Cost Ratio Outlier" in high_risk_sim.get("triggered_rules", []), "Must trigger Cost Ratio Outlier"
    print(f"  --> High-Risk Simulation OK: Verdict = {high_risk_sim['verdict']}, Ratio = {high_risk_sim['cost_ratio']}x.")

    compliant_sim = api.simulate_sanction_risk(
        work_type="Solar Street Lighting",
        sanctioned_amount=1400000.0, # Benchmark is 1.5M -> Compliant
        days_to_completion=90,
        vendor="Standard Public Agency"
    )
    assert compliant_sim.get("risk_level") == "Low", "Must pass compliant project as Low risk"
    print(f"  --> Compliant Simulation OK: Verdict = {compliant_sim['verdict']}, Ratio = {compliant_sim['cost_ratio']}x.")

    # 7. Verify app.py Code Structure
    print("\n[Step 7] Checking app.py code wiring...")
    with open("app.py", "r", encoding="utf-8") as f:
        app_code = f.read()

    assert "def render_live_ingestion_console():" in app_code, "render_live_ingestion_console must be defined"
    assert '("Gov Data Harvester", "Live Ingestion")' in app_code, "Gov Data Harvester must be in sidebar"
    assert 'elif st.session_state.page == "Live Ingestion":' in app_code, "Live Ingestion page route must exist"
    assert 'MoSPI eSAKSHI' in app_code, "MoSPI branding must be present"
    assert 'Pre-Sanction Fraud Interceptor' in app_code, "Pre-Sanction Interceptor tab must exist"
    print("  --> app.py Wiring OK: All navigation links, page routes, and forensic tabs verified.")

    print("\n================================================================================")
    print("PHASE 7 VERIFICATION SUCCESSFUL: 100% PASS")
    print("================================================================================")

if __name__ == "__main__":
    test_phase7_frontend_integration()
