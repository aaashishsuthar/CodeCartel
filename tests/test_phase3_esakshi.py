"""
Agent Kautilya — Phase 3 MoSPI eSAKSHI Harvester & State Telemetry Automated Verification Script
Tests the EsakshiConnector against official MoSPI endpoints, snapshot caching, state aggregation,
FastAPI REST endpoints, and schema integrity.
"""

import sys
import os
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.main import app
from backend.models.scrape_log import ScrapeLog
from backend.ingestion.connectors.esakshi import EsakshiConnector, CACHE_DIR


def test_phase3():
    print("=" * 70)
    print("   PHASE 3: OFFICIAL MoSPI eSAKSHI HARVESTER & TELEMETRY VERIFICATION  ")
    print("=" * 70)

    connector = EsakshiConnector()

    # -------------------------------------------------------------------------
    # 1. Test Live Call to MoSPI eSAKSHI getStateData
    # -------------------------------------------------------------------------
    print("\n[Step 1] Connecting to official MoSPI eSAKSHI portal...")
    states = connector.fetch_official_states()
    assert len(states) == 36, f"Expected 36 official States/UTs, got {len(states)}"
    sample_state = states[0]
    print(f"  [OK] Successfully retrieved {len(states)} official States and Union Territories from MoSPI.")
    print(f"       Sample State: {sample_state.get('STATE_NAME')} (State ID: {sample_state.get('STATE_ID')})")
    assert "STATE_NAME" in sample_state and "STATE_ID" in sample_state

    # -------------------------------------------------------------------------
    # 2. Test Snapshot Archiving & Cache
    # -------------------------------------------------------------------------
    print("\n[Step 2] Verifying raw snapshot caching for forensic audit trail...")
    assert os.path.exists(CACHE_DIR), f"Cache directory {CACHE_DIR} does not exist"
    snapshot = connector.get_latest_snapshot("state_data")
    assert snapshot is not None, "Snapshot was not saved to disk!"
    assert snapshot.get("source") == "https://mplads.mospi.gov.in"
    assert len(snapshot.get("data", [])) == 36
    print(f"  [OK] Snapshot verified on disk in {CACHE_DIR}")
    print(f"       Snapshot Timestamp: {snapshot.get('timestamp')} | Items: {len(snapshot['data'])}")

    # -------------------------------------------------------------------------
    # 3. Test State-Level Forensic Telemetry Aggregation
    # -------------------------------------------------------------------------
    print("\n[Step 3] Testing state-level forensic telemetry aggregation...")
    db: Session = SessionLocal()
    try:
        telemetry = connector.aggregate_state_telemetry(db, states)
        assert len(telemetry) > 0, "Telemetry aggregation produced 0 states!"
        print(f"  [OK] State telemetry generated across {len(telemetry)} states/UTs:")
        
        top_state = telemetry[0]
        print(f"       Top Allocated State: {top_state['state_name']} (State ID: {top_state['state_id']})")
        print(f"       Total MPs: {top_state['total_mps']} | Allocation: INR {top_state['total_allocated']:,.2f}")
        print(f"       Expenditure: INR {top_state['total_expenditure']:,.2f} (Util: {top_state['avg_utilization_pct']}%)")
        print(f"       Projects Tracked: {top_state['total_projects_tracked']} | High Risk: {top_state['high_risk_projects']}")

        # -------------------------------------------------------------------------
        # 4. Test Master Sync Pipeline and Audit Logging
        # -------------------------------------------------------------------------
        print("\n[Step 4] Testing sync_and_audit master pipeline...")
        sync_result = connector.sync_and_audit(db)
        assert sync_result["success"] is True, f"Sync and audit failed: {sync_result}"
        print(f"  [OK] Live MoSPI audit sync completed. Scrape ID: {sync_result['scrape_id']}")

        # Verify in scrape_logs table
        s_log = db.query(ScrapeLog).filter(ScrapeLog.scrape_id == sync_result["scrape_id"]).first()
        assert s_log is not None, "eSAKSHI scrape log entry not found in database!"
        assert s_log.source_name == "eSAKSHI (MoSPI)"
        assert s_log.status == "SUCCESS"
        print(f"       Verified in scrape_logs: {s_log.source_name} | Status: {s_log.status} | States: {s_log.records_fetched}")

    finally:
        db.close()

    # -------------------------------------------------------------------------
    # 5. Test FastAPI eSAKSHI REST Endpoints
    # -------------------------------------------------------------------------
    print("\n[Step 5] Testing eSAKSHI FastAPI REST Endpoints...")
    client = TestClient(app)

    # 5a: GET /api/esakshi/states
    res_states = client.get("/api/esakshi/states")
    assert res_states.status_code == 200
    states_data = res_states.json()
    assert len(states_data) == 36
    print(f"  [OK] GET /api/esakshi/states returned {len(states_data)} official States/UTs")

    # 5b: GET /api/esakshi/telemetry
    res_telem = client.get("/api/esakshi/telemetry")
    assert res_telem.status_code == 200
    telem_data = res_telem.json()
    assert len(telem_data) > 0
    print(f"  [OK] GET /api/esakshi/telemetry returned {len(telem_data)} state telemetry profiles")

    # 5c: GET /api/esakshi/snapshots
    res_snap = client.get("/api/esakshi/snapshots")
    assert res_snap.status_code == 200
    snap_data = res_snap.json()
    assert len(snap_data) > 0
    print(f"  [OK] GET /api/esakshi/snapshots returned {len(snap_data)} archived snapshots")

    # 5d: POST /api/esakshi/sync
    res_sync = client.post("/api/esakshi/sync")
    assert res_sync.status_code == 200
    print(f"  [OK] POST /api/esakshi/sync successfully triggered live synchronization")

    print("\n" + "=" * 70)
    print("      ALL PHASE 3 MoSPI eSAKSHI VERIFICATION TESTS PASSED!        ")
    print("=" * 70)


if __name__ == "__main__":
    try:
        test_phase3()
    except Exception as e:
        print(f"\n[FAIL] Phase 3 Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
