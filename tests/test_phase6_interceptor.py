"""
Agent Kautilya — Phase 6 Real-Time Anomaly & Fraud Interceptor Automated Verification Script
Tests the LiveAnomalyInterceptor, automated audit creation for high-risk sanctions,
pre-sanction simulation API, and system parity.
"""

import sys
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.main import app
from backend.models.project import ProjectModel
from backend.models.risk_score import RiskScoreRecord
from backend.models.audit import AuditRun, Evidence
from backend.services.live_interceptor import LiveAnomalyInterceptor


def test_phase6():
    print("=" * 70)
    print("   PHASE 6: REAL-TIME ANOMALY & FRAUD INTERCEPTOR VERIFICATION     ")
    print("=" * 70)

    db: Session = SessionLocal()
    try:
        # -------------------------------------------------------------------------
        # 1. Test Single Project Interception & Scoring
        # -------------------------------------------------------------------------
        print("\n[Step 1] Testing single project real-time interception...")
        sample_live = db.query(ProjectModel).filter(
            ProjectModel.data_source == "EmpoweredIndian API"
        ).first()
        assert sample_live is not None, "No live projects found in database!"

        verdict = LiveAnomalyInterceptor.intercept_project(sample_live, db, auto_audit_high_risk=True)
        assert "composite_risk_score" in verdict
        assert "ml_probability" in verdict
        print(f"  [OK] Intercepted Project: {sample_live.project_id}")
        print(f"       ML Probability: {verdict['ml_probability']} | Rule Signal: {verdict['rule_signal']}")
        print(f"       Composite Score: {verdict['composite_risk_score']} ({verdict['risk_level']})")
        print(f"       Triggered Rules: {verdict['triggered_rules']}")

        # Verify in risk_scores table
        rs_rec = db.query(RiskScoreRecord).filter(
            RiskScoreRecord.project_id == sample_live.project_id
        ).first()
        assert rs_rec is not None, "Risk score record missing in database!"
        assert rs_rec.composite_risk == verdict["composite_risk_score"]
        print("  [OK] Verified risk_scores table updated with real-time evaluation.")

        # -------------------------------------------------------------------------
        # 2. Test High-Risk Interception with Automated Audit & Evidence Generation
        # -------------------------------------------------------------------------
        print("\n[Step 2] Testing automated audit investigation for high-risk sanction...")
        # Create an inflated suspect project
        test_pid = "TEST-INTERCEPT-999"
        mock_high = db.query(ProjectModel).filter(ProjectModel.project_id == test_pid).first()
        if not mock_high:
            mock_high = ProjectModel(
                project_id=test_pid,
                mp_name="Test MP",
                state="Uttar Pradesh",
                constituency="VARANASI",
                district="VARANASI",
                work_type="Road Construction",
                description="Inflated Road Construction test work",
                vendor="Vendor_017",  # Suspect vendor
                allocated_ceiling=50000000.0,
                sanctioned_amount=35000000.0,  # 10x benchmark
                bill_amount=35000000.0,
                uc_amount=35000000.0,
                cumulative_sanctioned=55000000.0,  # Ceiling breach
                days_to_completion=450,
                amount_ratio=10.0,
                data_source="EmpoweredIndian API"
            )
            db.add(mock_high)
            db.commit()

        high_verdict = LiveAnomalyInterceptor.intercept_project(mock_high, db, auto_audit_high_risk=True)
        db.commit()

        assert high_verdict["risk_level"] == "High"
        assert high_verdict["audit_initiated"] is True
        print(f"  [OK] High-risk sanction detected! Risk Score: {high_verdict['composite_risk_score']}")
        print(f"       Auto-Initiated Audit ID: {high_verdict['audit_id']}")
        print(f"       Auto-Created Evidence ID: {high_verdict['evidence_id']}")

        # Verify AuditRun in database
        audit_rec = db.query(AuditRun).filter(AuditRun.project_id == test_pid).first()
        assert audit_rec is not None, "AuditRun not found in database!"
        print(f"  [OK] Verified AuditRun table contains record: {audit_rec.audit_id}")

        # Verify Evidence in database
        evid_rec = db.query(Evidence).filter(Evidence.project_id == test_pid).first()
        assert evid_rec is not None, "Evidence marker not found in database!"
        print(f"  [OK] Verified Evidence table contains marker: {evid_rec.evidence_id}")

        # Clean up test project
        db.delete(mock_high)
        if audit_rec:
            db.delete(audit_rec)
        if evid_rec:
            db.delete(evid_rec)
        db.commit()

        # -------------------------------------------------------------------------
        # 3. Test Batch Interception
        # -------------------------------------------------------------------------
        print("\n[Step 3] Running batch interception across all live works...")
        batch_res = LiveAnomalyInterceptor.intercept_batch(db, filter_source="EmpoweredIndian API", auto_audit=True)
        print(f"  [OK] Evaluated {batch_res['total_evaluated']} live works:")
        print(f"       High Risk: {batch_res['high_risk_flagged']}")
        print(f"       Medium Risk: {batch_res['medium_risk_flagged']}")
        print(f"       Low Risk: {batch_res['low_risk_flagged']}")
        print(f"       Audits Initiated: {batch_res['audits_initiated']}")
        assert batch_res["total_evaluated"] > 0

    finally:
        db.close()

    # -------------------------------------------------------------------------
    # 4. Test Interceptor FastAPI REST Endpoints
    # -------------------------------------------------------------------------
    print("\n[Step 4] Testing Interceptor FastAPI REST Endpoints...")
    client = TestClient(app)

    # 4a: POST /api/interceptor/simulate (Nominal proposal)
    res_sim_low = client.post("/api/interceptor/simulate", json={
        "work_type": "Drinking Water Supply",
        "sanctioned_amount": 1500000.0,
        "days_to_completion": 120,
        "vendor": "Local Water Authority"
    })
    assert res_sim_low.status_code == 200
    sim_low_data = res_sim_low.json()
    assert sim_low_data["risk_level"] in ["Low", "Medium"]
    print(f"  [OK] Simulated Nominal Project: Score {sim_low_data['composite_risk_score']} -> Verdict: '{sim_low_data['verdict']}'")

    # 4b: POST /api/interceptor/simulate (Inflated proposal)
    res_sim_high = client.post("/api/interceptor/simulate", json={
        "work_type": "Road Construction",
        "sanctioned_amount": 25000000.0,  # 7x benchmark
        "days_to_completion": 600,
        "vendor": "Vendor_004",  # Suspect vendor
        "cumulative_sanctioned": 48000000.0
    })
    assert res_sim_high.status_code == 200
    sim_high_data = res_sim_high.json()
    assert sim_high_data["risk_level"] == "High"
    assert "REJECT" in sim_high_data["verdict"]
    print(f"  [OK] Simulated Overrun Proposal: Score {sim_high_data['composite_risk_score']} -> Verdict: '{sim_high_data['verdict']}'")

    # 4c: GET /api/interceptor/stats
    res_stats = client.get("/api/interceptor/stats")
    assert res_stats.status_code == 200
    stats = res_stats.json()
    print("  [OK] GET /api/interceptor/stats:")
    print(f"       Live Works Tracked: {stats['total_live_works']}")
    print(f"       High Risk Flags: {stats['high_risk_flagged']}")
    print(f"       Medium Risk Flags: {stats['medium_risk_flagged']}")
    print(f"       Low Risk Flags: {stats['low_risk_flagged']}")
    print(f"       Active Automated Audits: {stats['automated_audits_active']}")

    # 4d: GET /api/interceptor/anomalies
    res_anom = client.get("/api/interceptor/anomalies")
    assert res_anom.status_code == 200
    anom_data = res_anom.json()
    print(f"  [OK] GET /api/interceptor/anomalies returned {anom_data['total_anomalies']} flagged items")

    print("\n" + "=" * 70)
    print("    ALL PHASE 6 REAL-TIME ANOMALY INTERCEPTOR TESTS PASSED!       ")
    print("=" * 70)


if __name__ == "__main__":
    try:
        test_phase6()
    except Exception as e:
        print(f"\n[FAIL] Phase 6 Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
