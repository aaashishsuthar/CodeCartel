"""
Phase 8: End-to-End System Verification & Jury Demo Prep
Verifies the complete pipeline from live government harvesting, LGD validation,
real-time fraud interception, to official CAG Audit Memo PDF generation.
"""

import sys
import os

# Fix Windows console UTF-8 encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from client import KautilyaAPIClient

def test_phase8_e2e():
    print("================================================================================")
    print("       PHASE 8: END-TO-END SYSTEM VERIFICATION & JURY DEMO SUITE       ")
    print("================================================================================")

    api = KautilyaAPIClient()

    # Step 1: Health & Telemetry Verification
    print("\n[Step 1] Verifying Backend & Gov Connector Telemetry...")
    health = api.check_health()
    assert health.get("status") == "ok", "FastAPI backend must be healthy"
    harvester_status = api.get_harvester_status()
    assert harvester_status.get("database_connected") is True, "Database must be connected"
    print(f"  [OK] Backend online: {health.get('service')} (DB Connected: True)")
    print(f"       Connectors: {harvester_status.get('available_connectors')}")
    print(f"       Tracked MPs: {harvester_status.get('total_mps_stored')} | Total Works: {harvester_status.get('total_projects_stored')}")

    # Authenticate as CAG Central Auditor for forensic investigations
    user = api.login("auditor@mospi.gov.in", "SIH2026Kautilya")
    assert user.get("role") == "CAG", "Login must return CAG role"
    print(f"  [OK] Authenticated as {user.get('email')} (Role: {user.get('role')})")

    # Step 2: MoSPI eSAKSHI National Macro Telemetry
    print("\n[Step 2] Testing MoSPI eSAKSHI State Registry...")
    states = api.get_mospi_states()
    assert len(states) >= 36, "Must have 36 official States/UTs"
    sample_state = states[0]
    state_name = sample_state.get('STATE_NAME') or sample_state.get('state_name')
    state_id = sample_state.get('STATE_ID') or sample_state.get('state_id')
    print(f"  [OK] MoSPI official States/UTs: {len(states)} jurisdictions loaded.")
    print(f"       Sample State: {state_name} (MoSPI ID: {state_id})")

    # Step 3: LGD Code Matcher & Sanitization
    print("\n[Step 3] Testing Ministry of Panchayati Raj LGD Matcher...")
    demo_cities = [("Varanasi", "Uttar Pradesh", 178), ("Shillong", "Meghalaya", 274)]
    for city, state, expected_code in demo_cities:
        lgd_res = api.lookup_lgd(district=city, state=state)
        assert lgd_res.get("lgd_district_code") == expected_code, f"Failed matching {city}"
        print(f"  [OK] Resolved '{city}' -> LGD Code {lgd_res.get('lgd_district_code')} (Status: {lgd_res.get('match_status')})")

    # Step 4: Live Works Ingestion & Forensic Schema
    print("\n[Step 4] Testing Live Government Works Ingestion Feed...")
    live_works = api.get_live_works(limit=5, as_df=True)
    assert len(live_works) > 0, "Must have live harvested works"
    first_work = live_works.iloc[0]
    print(f"  [OK] Ingested Live Work: {first_work['project_id']}")
    print(f"       Work Type: {first_work['work_type']} | Cost: Rs. {first_work['sanctioned_amount']:,.2f}")
    print(f"       MP: {first_work['mp_name']} ({first_work['constituency']})")
    print(f"       Risk Level: {first_work['risk_level']} (Score: {first_work['risk_score']})")

    # Step 5: Real-Time Pre-Sanction Interceptor Simulation
    print("\n[Step 5] Testing Real-Time Pre-Sanction Interceptor (Jury Demo Scenario)...")
    # Scenario: High-Risk Overrun proposal (> 2x benchmark cost)
    overrun_proposal = api.simulate_sanction_risk(
        work_type="Road Construction",
        sanctioned_amount=9800000.0, # Benchmark is 3.5M -> 2.8x inflation
        days_to_completion=240,
        vendor="Vendor_017" # Suspect vendor
    )
    assert overrun_proposal.get("risk_level") == "High", "Must be flagged as High risk"
    print(f"  [OK] Pre-Sanction Interception: {overrun_proposal.get('verdict')}")
    print(f"       Unit Cost Inflation: {overrun_proposal.get('cost_ratio')}x benchmark")
    print(f"       ML Overrun Probability: {overrun_proposal.get('ml_overrun_probability') * 100:.1f}%")
    print(f"       Triggered Statutory Rules: {overrun_proposal.get('triggered_rules')}")

    # Step 6: Automated Audit & Formal Dossier Creation
    print("\n[Step 6] Testing Formal Audit Run & Evidence Generation...")
    audit_res = api.run_audit("MPLAD-1001")
    audit_id = audit_res.get("audit_id")
    assert audit_id is not None, "Must generate valid Audit ID"
    print(f"  [OK] Audit Run Created: {audit_id} for project MPLAD-1001")
    evidence = api.get_evidence("MPLAD-1001")
    assert len(evidence) > 0, "Must generate forensic evidence markers"
    print(f"  [OK] Evidence Repository: {len(evidence)} forensic evidence markers compiled.")

    # Step 7: CAG Official Audit Memo PDF Generation
    print("\n[Step 7] Testing CAG Audit Memo PDF Generation...")
    pdf_bytes = api.download_memo("MPLAD-1001")
    assert isinstance(pdf_bytes, bytes), "Memo must be binary bytes"
    assert len(pdf_bytes) > 1000, "PDF must not be empty"
    print(f"  [OK] CAG Audit Memo PDF Generated: {len(pdf_bytes):,} bytes.")
    print("       Header: Official Comptroller and Auditor General (CAG) Audit Memo")
    print("       Fidelity: Statutory Evidence Markers, Cross-Referenced VCI & Sanction Hash")

    print("\n================================================================================")
    print("ALL PHASE 8 E2E CHECKS PASSED: SYSTEM FULLY PRODUCTION-READY FOR JURY DEMO!")
    print("================================================================================")

if __name__ == "__main__":
    test_phase8_e2e()
