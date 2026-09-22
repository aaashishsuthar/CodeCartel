"""
Agent Kautilya — Phase 2 Live Harvester Automated Verification Script
Tests the EmpoweredIndianConnector, database upsertion across all 7 normalized tables,
FastAPI REST endpoints, and schema integrity.
"""

import sys
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.main import app
from backend.models.allocation import MPAllocation
from backend.models.project import ProjectModel
from backend.models.fund_release import FundRelease
from backend.models.certificate import UtilizationCertificate
from backend.models.risk_score import RiskScoreRecord
from backend.models.vendor import Vendor
from backend.models.scrape_log import ScrapeLog
from backend.ingestion.connectors.empowered_indian import EmpoweredIndianConnector


def test_phase2():
    print("=" * 70)
    print("     PHASE 2: LIVE WORKS API HARVESTER AUTOMATED VERIFICATION       ")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # 1. Test Live API Fetchers
    # -------------------------------------------------------------------------
    print("\n[Step 1] Testing live network calls to Empowered Indian API...")
    connector = EmpoweredIndianConnector()
    
    # 1a: MP Summaries
    mp_resp = connector.fetch_mp_summaries(page=1, limit=5)
    assert mp_resp.get("success") is True or len(mp_resp.get("data", [])) > 0, "Failed to fetch MP summaries"
    sample_mp = mp_resp["data"][0]
    print(f"  [OK] Live MP Summaries fetched successfully: {len(mp_resp['data'])} records")
    print(f"       Sample MP: {sample_mp.get('mpName')} | State: {sample_mp.get('state')} | Const: {sample_mp.get('constituency')}")
    assert "allocatedAmount" in sample_mp, "Missing allocatedAmount in MP record"

    # 1b: Completed Works
    works_resp = connector.fetch_completed_works("SHILLONG", page=1, limit=5)
    assert works_resp.get("success") is True, f"Failed to fetch completed works: {works_resp.get('error')}"
    works = works_resp.get("data", [])
    assert len(works) > 0, "No completed works returned for SHILLONG"
    sample_work = works[0]
    print(f"  [OK] Live Completed Works fetched for SHILLONG: {len(works)} records")
    print(f"       Sample Work ID: {sample_work.get('work_id')}")
    print(f"       Description: {sample_work.get('work_description')[:50]}...")
    print(f"       Cost: Rs. {sample_work.get('cost'):,}")

    # -------------------------------------------------------------------------
    # 2. Test Normalization & Relational DB Synchronization
    # -------------------------------------------------------------------------
    print("\n[Step 2] Testing Relational DB synchronization...")
    db: Session = SessionLocal()
    try:
        # 2a: Sync MP Allocations
        updated_mps, inserted_mps = connector.sync_mp_allocations(db, mp_resp["data"])
        print(f"  [OK] MP Allocations sync: {updated_mps} updated, {inserted_mps} inserted")
        
        # Verify in DB
        first_mp_name = sample_mp.get("mpName")
        mp_in_db = db.query(MPAllocation).filter(MPAllocation.mp_name == first_mp_name).first()
        assert mp_in_db is not None, f"MP {first_mp_name} not found in DB!"
        assert mp_in_db.data_source == "EmpoweredIndian API"
        print(f"       Verified in mp_allocations table: {mp_in_db.mp_name} (Util: {mp_in_db.utilization_pct}%)")

        # 2b: Sync Completed Works for SHILLONG
        fetched, synced = connector.sync_completed_works(db, "SHILLONG", works, "RUN-TEST-001")
        print(f"  [OK] Completed Works sync: {fetched} fetched, {synced} synced")

        # Verify in projects table
        sample_pid = f"EI-{sample_work.get('work_id')}"
        project_in_db = db.query(ProjectModel).filter(ProjectModel.project_id == sample_pid).first()
        assert project_in_db is not None, f"Project {sample_pid} not found in projects table!"
        assert project_in_db.description is not None, "Project description was not saved!"
        assert project_in_db.data_source == "EmpoweredIndian API"
        print(f"       Verified in projects table: {project_in_db.project_id} | Type: {project_in_db.work_type} | Vendor: {project_in_db.vendor[:30]}")

        # Verify in fund_releases table
        tranche = db.query(FundRelease).filter(FundRelease.project_id == sample_pid).first()
        assert tranche is not None, f"Tranche not created for {sample_pid}"
        print(f"       Verified in fund_releases: {tranche.tranche_id} | Disbursed: Rs. {tranche.disbursed_amount:,}")

        # Verify in utilization_certificates table
        uc = db.query(UtilizationCertificate).filter(UtilizationCertificate.project_id == sample_pid).first()
        assert uc is not None, f"UC not created for {sample_pid}"
        print(f"       Verified in utilization_certificates: {uc.uc_id} | UC Amount: Rs. {uc.uc_amount:,}")

        # Verify in risk_scores table
        rs = db.query(RiskScoreRecord).filter(RiskScoreRecord.project_id == sample_pid).first()
        assert rs is not None, f"Risk score not created for {sample_pid}"
        print(f"       Verified in risk_scores: Score {rs.composite_risk} ({rs.risk_level})")

        # Verify in vendors table
        vendor_rec = db.query(Vendor).filter(Vendor.vendor_name == project_in_db.vendor).first()
        assert vendor_rec is not None, f"Vendor {project_in_db.vendor} not created in vendors table!"
        print(f"       Verified in vendors: {vendor_rec.vendor_name} (Works: {vendor_rec.total_works})")

        # 2c: Test full batch harvest pipeline
        print("\n[Step 3] Testing harvest_batch pipeline with scrape logging...")
        batch_result = connector.harvest_batch(
            db=db,
            sync_mps=True,
            constituencies=["SHILLONG"],
            max_constituencies=1
        )
        assert batch_result["success"] is True, f"Harvest batch failed: {batch_result}"
        print(f"  [OK] Batch Harvest completed: {batch_result['total_records_fetched']} fetched, {batch_result['total_records_inserted']} inserted/updated")
        print(f"       Scrape Log ID: {batch_result['scrape_id']}")

        # Verify scrape_logs entry
        s_log = db.query(ScrapeLog).filter(ScrapeLog.scrape_id == batch_result["scrape_id"]).first()
        assert s_log is not None, "Scrape log entry not found!"
        assert s_log.status in ["SUCCESS", "PARTIAL"]
        print(f"       Verified in scrape_logs: {s_log.scrape_id} | Status: {s_log.status} | Inserted: {s_log.records_inserted}")

    finally:
        db.close()

    # -------------------------------------------------------------------------
    # 4. Test FastAPI Harvester Endpoints
    # -------------------------------------------------------------------------
    print("\n[Step 4] Testing Harvester FastAPI REST Endpoints...")
    client = TestClient(app)

    # 4a: GET /api/harvester/status
    res_status = client.get("/api/harvester/status")
    assert res_status.status_code == 200, f"Failed: {res_status.text}"
    status_data = res_status.json()
    print(f"  [OK] GET /api/harvester/status returned 200:")
    print(f"       Total MPs: {status_data['total_mps_stored']}")
    print(f"       Total Projects: {status_data['total_projects_stored']}")
    print(f"       Live Government Works: {status_data['live_government_works_stored']}")
    assert status_data["live_government_works_stored"] > 0, "No live works registered in status"

    # 4b: GET /api/harvester/mps
    res_mps = client.get("/api/harvester/mps?limit=5")
    assert res_mps.status_code == 200
    mps_data = res_mps.json()
    print(f"  [OK] GET /api/harvester/mps returned {len(mps_data['items'])} items (Total: {mps_data['total']})")

    # 4c: GET /api/harvester/live-works
    res_live = client.get("/api/harvester/live-works?limit=5")
    assert res_live.status_code == 200
    live_data = res_live.json()
    print(f"  [OK] GET /api/harvester/live-works returned {live_data['count']} items")
    assert live_data["count"] > 0

    # 4d: GET /api/harvester/logs
    res_logs = client.get("/api/harvester/logs?limit=5")
    assert res_logs.status_code == 200
    logs_data = res_logs.json()
    print(f"  [OK] GET /api/harvester/logs returned {len(logs_data)} log entries")

    print("\n" + "=" * 70)
    print("      ALL PHASE 2 LIVE HARVESTER VERIFICATION TESTS PASSED!       ")
    print("=" * 70)


if __name__ == "__main__":
    try:
        test_phase2()
    except Exception as e:
        print(f"\n[FAIL] Phase 2 Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
