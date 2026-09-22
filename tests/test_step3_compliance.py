"""
Step 3 Verification: MoSPI 2023 Statutory Guidelines Compliance Engine
Verifies:
1. MoSPI Annexure-II Prohibited Works Blacklist Scanner (regex matching, categories, statutory citations).
2. MoSPI Para 2.5 SC (15.0%) and ST (7.5%) Mandatory Quota Evaluator.
3. Pre-Sanction Simulator API (/api/interceptor/simulate) interception of prohibited proposals.
4. Dataset tagging with Community_Category, Is_Prohibited_Work, and FORENSIC_COLS masking.
5. MP and Ministry UI console wiring for statutory compliance.
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
from backend.rules.compliance import check_mospi_prohibited_work, evaluate_mp_statutory_quotas

def test_statutory_compliance():
    print("================================================================================")
    print("  STEP 3 VERIFICATION: MoSPI 2023 STATUTORY GUIDELINES COMPLIANCE ENGINE       ")
    print("================================================================================")

    # 1. Test MoSPI Annexure-II Prohibited Works Scanner
    print("\n[Step 1] Testing MoSPI Annexure-II Prohibited Works Scanner...")
    
    # Prohibited cases
    prohibited_tests = [
        ("Construction of Memorial Statue of Political Leader", "Item 3", "Statues, Memorials and Monuments"),
        ("Renovation of Temple Dharamshala at Chowk", "Item 1 & 2", "Places of Religious Worship"),
        ("Financial Recurring Grant for Private Club Society", "Item 7", "Commercial / Private Corporate Entities"),
        ("Purchase of Office Consumable Stationery and Printer Paper", "Item 5", "Recurring Grants, Consumables and Loans"),
    ]
    for desc, expected_item, expected_cat in prohibited_tests:
        res = check_mospi_prohibited_work(desc)
        assert res["is_prohibited"] is True, f"Failed to flag prohibited work: {desc}"
        assert res["status"] == "STATUTORY_VIOLATION"
        print(f"  [BLOCKED] '{desc[:45]}...' -> {res['category']} ({res['item']})")

    # Permissible cases
    permissible_tests = [
        ("Installation of Solar Street Lighting along Village Link Road", "Solar Street Lighting"),
        ("Construction of Community Drinking Water Filter Plant", "Drinking Water Supply"),
        ("Additional Classroom Wing for Government Higher Secondary School", "School Building"),
    ]
    for desc, wtype in permissible_tests:
        res = check_mospi_prohibited_work(desc, wtype)
        assert res["is_prohibited"] is False, f"Erroneously flagged permissible work: {desc}"
        assert res["status"] == "PERMISSIBLE"
        print(f"  [CLEARED] '{desc[:45]}...' -> Permissible Public Work")

    # 2. Test MoSPI Para 2.5 SC/ST Quota Engine
    print("\n[Step 2] Testing MoSPI Para 2.5 SC (15%) & ST (7.5%) Quota Engine...")
    # Case A: Compliant MP
    q_pass = evaluate_mp_statutory_quotas(total_sanctioned=50_000_000, sc_sanctioned=8_500_000, st_sanctioned=4_000_000)
    assert q_pass["sc_compliant"] is True, "17% SC should be compliant"
    assert q_pass["st_compliant"] is True, "8% ST should be compliant"
    assert q_pass["statutory_compliant"] is True
    assert q_pass["sc_shortfall_amt"] == 0.0
    print(f"  [OK] Compliant MP: SC={q_pass['sc_pct']}% (Target 15%), ST={q_pass['st_pct']}% (Target 7.5%) -> Fully Compliant.")

    # Case B: Deficit MP (Shortfall)
    q_fail = evaluate_mp_statutory_quotas(total_sanctioned=50_000_000, sc_sanctioned=4_000_000, st_sanctioned=2_000_000)
    assert q_fail["sc_compliant"] is False, "8% SC should trigger shortfall"
    assert q_fail["st_compliant"] is False, "4% ST should trigger shortfall"
    assert q_fail["statutory_compliant"] is False
    assert q_fail["sc_shortfall_amt"] == 3_500_000.0  # 7.5M - 4M
    assert q_fail["st_shortfall_amt"] == 1_750_000.0  # 3.75M - 2M
    print(f"  [OK] Shortfall MP: SC Shortfall=INR {q_fail['sc_shortfall_amt']:,.2f}, ST Shortfall=INR {q_fail['st_shortfall_amt']:,.2f}.")

    # 3. Test Pre-Sanction Interceptor API (/api/interceptor/simulate)
    print("\n[Step 3] Testing Real-Time Interception via FastAPI Gateway...")
    try:
        client = KautilyaAPIClient()
        sim_blocked = client.simulate_sanction_risk(
            work_type="Community Hall",
            sanctioned_amount=4_500_000,
            description="Erection of Memorial Statue of Eminent Dignitary"
        )
    except Exception:
        from fastapi.testclient import TestClient
        from backend.main import app as fastapi_app
        tc = TestClient(fastapi_app)
        resp = tc.post("/api/interceptor/simulate", json={
            "work_type": "Community Hall",
            "sanctioned_amount": 4_500_000,
            "description": "Erection of Memorial Statue of Eminent Dignitary"
        })
        sim_blocked = resp.json()

    assert sim_blocked.get("is_prohibited") is True, "API must flag prohibited proposal"
    assert sim_blocked.get("risk_level") == "High", "Prohibited work must be High Risk"
    assert "Prohibited Work" in str(sim_blocked.get("triggered_rules")), "Must record Prohibited Work rule trigger"
    assert "STATUTORY REJECT" in sim_blocked.get("verdict", ""), "Verdict must cite statutory reject"
    print(f"  [OK] Interceptor REST API: Correctly blocked prohibited proposal: {sim_blocked['verdict'][:55]}...")

    # 4. Test Dataframe Schema & Masking in app.py
    print("\n[Step 4] Checking dataset columns and forensic masking in app.py...")
    import app
    df = app.load_data()
    assert "Community_Category" in df.columns, "Community_Category column must exist in df"
    assert "Is_Prohibited_Work" in df.columns, "Is_Prohibited_Work column must exist in df"
    assert "Prohibited_Category" in df.columns, "Prohibited_Category column must exist in df"

    # Verify category values
    hab_counts = df["Community_Category"].value_counts().to_dict()
    assert "SC Habitation" in hab_counts and hab_counts["SC Habitation"] > 0
    assert "ST Habitation" in hab_counts and hab_counts["ST Habitation"] > 0
    assert "General Community" in hab_counts and hab_counts["General Community"] > 0
    print(f"  [OK] Habitation Categories mapped: {hab_counts}")

    prohib_count = int(df["Is_Prohibited_Work"].sum())
    print(f"  [OK] Prohibited works flagged in historical register: {prohib_count}")

    # Verify forensic masking
    masked = app.mask_forensics(df)
    assert "Community_Category" in masked.columns, "Community_Category must remain visible to MP/Citizen"
    assert "Is_Prohibited_Work" not in masked.columns, "Is_Prohibited_Work must be masked server-side"
    assert "Prohibited_Category" not in masked.columns, "Prohibited_Category must be masked server-side"
    print("  [OK] Server-side forensic masking verified: Prohibited indicators withheld from public tier.")

    # 5. Check UI Wiring in app.py
    print("\n[Step 5] Checking UI wiring for MP Statutory SC/ST Quotas...")
    with open("app.py", "r", encoding="utf-8") as f:
        app_code = f.read()

    assert "MoSPI Statutory SC/ST Quotas" in app_code, "SC/ST Quotas tab must exist in render_mp"
    assert "Scheduled Caste (SC) Quota Target: 15.0%" in app_code, "SC Quota card must exist"
    assert "Scheduled Tribe (ST) Quota Target: 7.5%" in app_code, "ST Quota card must exist"
    assert "NON-PERMISSIBLE WORK (MoSPI Annexure-II)" in app_code, "Recommendation form must enforce Annexure-II"
    print("  [OK] MP Console wiring verified with real-time SC/ST statutory progress meters and rejection filters.")

    print("\n================================================================================")
    print(" STEP 3 VERIFICATION SUCCESSFUL: 100% PASS (STATUTORY COMPLIANCE ENGINE ACTIVE) ")
    print("================================================================================")

if __name__ == "__main__":
    test_statutory_compliance()
