"""
Step 6 Verification: Autonomous AI Vigilance Agent, Scheduled Government Data Pile-Up,
and Multi-Tier Authority Escalation Lifecycle.
"""

import sys
import os
import json
import pandas as pd
from datetime import datetime

# Fix Windows console UTF-8 encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.database import SessionLocal, Base, engine
from backend.models.vendor import AuthorityNotice
from backend.services.autonomous_agent import autonomous_agent, AutonomousVigilanceAgent
from backend.services.vendor_service import (
    escalate_vendor_to_all_authorities,
    get_authority_notices,
    record_authority_action,
)
from backend.services.scheduler import scheduler_daemon
from client.api_client import KautilyaAPIClient


def test_autonomous_investigate_high_risk():
    """Verifies autonomous evaluation flags suspect vendor & document divergence as High Risk."""
    print("  [1/6] Testing Autonomous AI High-Risk Evaluation & Auto-Flagging...")
    test_record = {
        "Project_ID": "TEST-PRJ-HIGH-01",
        "Work_Type": "Road Construction",
        "Sanctioned_Amount": 8500000.0,
        "Bill_Amount": 8500000.0,
        "UC_Amount": 11500000.0,  # +35.3% gap
        "Allocated_Ceiling": 50000000.0,
        "Cumulative_Sanctioned": 65000000.0,  # Ceiling breach
        "Vendor": "M/s Cartel Syndicate 004 (Suspect Flagged)",
        "Constituency": "Test Constituency",
        "State": "Test State",
        "Vendor_Is_Suspect": 1,
        "Is_Duplicate": 1,
        "Ghost_Asset_Risk": 1,
    }

    result = autonomous_agent.investigate_project_record(test_record)

    assert result["project_id"] == "TEST-PRJ-HIGH-01"
    assert result["risk_level"] == "High"
    assert result["risk_score"] >= 0.67
    assert result["authorities_notified"] is True
    assert "divergence" in result["finding_summary"].lower()
    assert "cartel" in result["finding_summary"].lower()
    assert result["directive"] != ""
    print(f"    [OK] Evaluated as {result['risk_level']} Risk ({result['risk_score']:.2f}); Authorities Notified: {result['authorities_notified']}")


def test_autonomous_investigate_low_risk():
    """Verifies autonomous evaluation passes fully compliant projects as Low Risk."""
    print("  [2/6] Testing Autonomous AI Low-Risk Evaluation...")
    test_record = {
        "Project_ID": "TEST-PRJ-LOW-01",
        "Work_Type": "Drinking Water Supply",
        "Sanctioned_Amount": 2100000.0,
        "Bill_Amount": 2100000.0,
        "UC_Amount": 2100000.0,
        "Allocated_Ceiling": 50000000.0,
        "Cumulative_Sanctioned": 15000000.0,
        "Vendor": "Standard Cooperative Society",
        "Constituency": "Test Compliant",
        "State": "Test State",
        "Vendor_Is_Suspect": 0,
        "Is_Duplicate": 0,
        "Ghost_Asset_Risk": 0,
    }

    result = autonomous_agent.investigate_project_record(test_record)

    assert result["project_id"] == "TEST-PRJ-LOW-01"
    assert result["risk_level"] == "Low"
    assert result["risk_score"] <= 0.35
    assert result["authorities_notified"] is False
    assert result["flags_count"] == 0
    print(f"    [OK] Evaluated as {result['risk_level']} Risk ({result['risk_score']:.2f}); Compliant flags: 0")


def test_autonomous_sweep_next_case():
    """Verifies autonomous agent sweeps next case across a project dataframe."""
    print("  [3/6] Testing Autonomous Sweep & Investigation History...")
    df_sample = pd.DataFrame([
        {
            "Project_ID": "PRJ-SWEEP-01",
            "Work_Type": "School Building",
            "Sanctioned_Amount": 5200000.0,
            "Bill_Amount": 5200000.0,
            "UC_Amount": 5200000.0,
            "Allocated_Ceiling": 50000000.0,
            "Cumulative_Sanctioned": 22000000.0,
            "Vendor": "State Construction Corp",
            "Constituency": "Varanasi",
            "State": "Uttar Pradesh",
            "Vendor_Is_Suspect": 0,
            "Is_Duplicate": 0,
            "Ghost_Asset_Risk": 0,
            "Risk_Score": 0.22,
            "Risk_Level": "Low",
        },
        {
            "Project_ID": "PRJ-SWEEP-02",
            "Work_Type": "Community Hall",
            "Sanctioned_Amount": 4800000.0,
            "Bill_Amount": 4800000.0,
            "UC_Amount": 6500000.0,
            "Allocated_Ceiling": 50000000.0,
            "Cumulative_Sanctioned": 49000000.0,
            "Vendor": "Vendor_017 Suspect",
            "Constituency": "Patna Sahib",
            "State": "Bihar",
            "Vendor_Is_Suspect": 1,
            "Is_Duplicate": 0,
            "Ghost_Asset_Risk": 1,
            "Risk_Score": 0.88,
            "Risk_Level": "High",
        }
    ])

    res1 = autonomous_agent.sweep_next_case(df_projects=df_sample)
    assert res1["project_id"] in ["PRJ-SWEEP-01", "PRJ-SWEEP-02"]

    res2 = autonomous_agent.sweep_next_case(df_projects=df_sample)
    assert res2["project_id"] in ["PRJ-SWEEP-01", "PRJ-SWEEP-02"]

    # Test circular rotation when all sample projects are investigated
    res3 = autonomous_agent.sweep_next_case(df_projects=df_sample)
    res4 = autonomous_agent.sweep_next_case(df_projects=df_sample)
    assert res3["project_id"] != res4["project_id"], "Circular rotation must alternate/cycle across dataset without getting stuck"

    history = autonomous_agent.get_investigations_history(limit=5)
    assert len(history) >= 1
    print(f"    [OK] Swept cases (Circular rotation verified: {res3['project_id']} -> {res4['project_id']}); History count: {len(history)}")


def test_vendor_escalation_to_all_authorities():
    """Verifies vendor escalation dispatches structured notices to all 4 authority tiers."""
    print("  [4/6] Testing Vendor Escalation to 4 Administrative Tiers...")
    db = SessionLocal()
    try:
        vendor_test = "TEST_CARTEL_ENTERPRISE_XYZ"
        reason_test = "Detected 4-constituency single-bid clustering with 2.2x rate inflation"

        notices = escalate_vendor_to_all_authorities(db=db, vendor_name=vendor_test, reason=reason_test)

        assert len(notices) == 4
        tiers = [n["authority_tier"] for n in notices]
        assert "Ministry / CAG Auditors" in tiers
        assert "State Nodal Authorities (SNA)" in tiers
        assert "District Authorities / Collectors" in tiers
        assert "CVC & GeM Procurement Vigilance" in tiers

        for n in notices:
            assert n["vendor_name"] == vendor_test
            assert n["status"] in ["DISPATCHED", "PENDING_ACTION"]
            assert n["recommended_action"] != ""
            assert n["notice_id"].startswith("ESC-")

        # Test retrieval
        retrieved = get_authority_notices(db=db, vendor_name=vendor_test)
        assert len(retrieved) >= 4

        # Test recording authority action
        target_notice = notices[0]
        act_res = record_authority_action(
            db=db,
            notice_id=target_notice["notice_id"],
            action="National Procurement Debarment Enforced under CVC Guidelines",
            actor_email="cag.principal@gov.in"
        )
        assert act_res["status"] in ["ACTION_TAKEN", "RESOLVED"]
        assert act_res["action_taken"] == "National Procurement Debarment Enforced under CVC Guidelines"
        assert act_res["action_taken_by"] == "cag.principal@gov.in"
        assert act_res["action_taken_at"] is not None
        print(f"    [OK] Dispatched {len(notices)} notices. Recorded resolution on {target_notice['notice_id']}")
    finally:
        db.close()


def test_scheduler_pile_up_and_curiosities():
    """Verifies scheduled case pile-up produces interesting forensic insights."""
    print("  [5/6] Testing Scheduled Case Pile-Up & Forensic Curiosity Stream...")
    db = SessionLocal()
    try:
        new_batch, insights = scheduler_daemon._pile_up_live_government_cases(db, inserted_from_api=0)
        assert len(new_batch) >= 2
        assert len(insights) >= 2

        for case in new_batch:
            assert "project_id" in case
            assert "interesting_insight" in case
            assert len(case["interesting_insight"]) > 10
            assert "risk_score" in case
            assert "data_source" in case

        # Check API client method
        api = KautilyaAPIClient()
        piled = api.get_newly_piled_cases(limit=10)
        assert len(piled) >= 2
        print(f"    [OK] Harvested {len(new_batch)} new live cases with {len(insights)} forensic curiosities")
    finally:
        db.close()


def test_api_client_offline_escalation_flow():
    """Verifies KautilyaAPIClient escalation and notice action methods work in offline mode."""
    print("  [6/6] Testing API Client Multi-Tier Escalation Dispatcher...")
    api = KautilyaAPIClient()
    res = api.escalate_vendor("TEST_VENDOR_OFFLINE", reason="Offline test escalation")
    assert res["success"] is True
    assert res["dispatched_count"] == 4

    notices = api.get_authority_notices(vendor_name="TEST_VENDOR_OFFLINE")
    assert len(notices) >= 4

    nid = notices[0]["notice_id"]
    action_res = api.record_authority_action(
        notice_id=nid,
        action="Statewide Procurement Freeze",
        actor="sna.up@state.gov.in"
    )
    assert action_res["status"] in ["ACTION_TAKEN", "RESOLVED"]
    print(f"    [OK] Client successfully escalated offline vendor and recorded action {nid} -> RESOLVED")


def run_all():
    print("================================================================================")
    print(" STEP 6: AUTONOMOUS VIGILANCE, AUTO-REFRESH & AUTHORITY ESCALATION VERIFICATION")
    print("================================================================================")
    Base.metadata.create_all(bind=engine)
    test_autonomous_investigate_high_risk()
    test_autonomous_investigate_low_risk()
    test_autonomous_sweep_next_case()
    test_vendor_escalation_to_all_authorities()
    test_scheduler_pile_up_and_curiosities()
    test_api_client_offline_escalation_flow()
    print("================================================================================")
    print("   ALL STEP 6 AUTONOMOUS AI & ESCALATION VERIFICATIONS PASSED [100% OK]")
    print("================================================================================")


if __name__ == "__main__":
    run_all()
