"""
Agent Kautilya — Phase 5 Automated Scheduler & Background Harvester Verification Script
Tests the HarvesterScheduler daemon, automated harvest cycle execution,
FastAPI REST endpoints, and system parity.
"""

import sys
import time
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.scheduler import scheduler_daemon


def test_phase5():
    print("=" * 70)
    print("   PHASE 5: AUTOMATED SCHEDULER & BACKGROUND HARVESTER VERIFICATION ")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # 1. Test HarvesterScheduler Lifecycle
    # -------------------------------------------------------------------------
    print("\n[Step 1] Testing HarvesterScheduler lifecycle...")
    scheduler_daemon.start()
    assert scheduler_daemon.is_running is True, "Scheduler failed to start!"
    print(f"  [OK] Scheduler daemon active: {scheduler_daemon.is_running}")
    print(f"       Default Interval: every {scheduler_daemon.interval_minutes} minutes")

    # -------------------------------------------------------------------------
    # 2. Test Automated Harvest Cycle
    # -------------------------------------------------------------------------
    print("\n[Step 2] Executing automated harvest cycle...")
    t0 = time.time()
    cycle_res = scheduler_daemon.execute_harvest_cycle()
    elapsed = round(time.time() - t0, 2)
    assert cycle_res.get("status") == "SUCCESS", f"Cycle failed: {cycle_res}"
    print(f"  [OK] Harvest cycle completed in {elapsed}s with status: {cycle_res['status']}")
    print(f"       Empowered Indian: {cycle_res['empowered_indian']}")
    print(f"       MoSPI eSAKSHI: {cycle_res['esakshi_mospi']}")
    print(f"       Cleaner LGD Quality Score: {cycle_res['cleaner_lgd']['quality_score']}%")
    assert scheduler_daemon.total_automated_runs >= 1

    # -------------------------------------------------------------------------
    # 3. Test Reconfiguration & Async Trigger
    # -------------------------------------------------------------------------
    print("\n[Step 3] Testing dynamic interval reconfiguration & non-blocking trigger...")
    scheduler_daemon.set_interval(45)
    assert scheduler_daemon.interval_minutes == 45
    print("  [OK] Successfully rescheduled interval to 45 minutes.")

    async_res = scheduler_daemon.trigger_async()
    assert async_res.get("status") == "QUEUED"
    print(f"  [OK] Asynchronous trigger returned: {async_res}")

    # -------------------------------------------------------------------------
    # 4. Test Scraper FastAPI REST Endpoints
    # -------------------------------------------------------------------------
    print("\n[Step 4] Testing Scraper FastAPI REST Endpoints...")
    client = TestClient(app)

    # 4a: GET /api/scraper/status
    res_status = client.get("/api/scraper/status")
    assert res_status.status_code == 200
    telemetry = res_status.json()
    print("  [OK] GET /api/scraper/status:")
    print(f"       Daemon Active: {telemetry['daemon_active']}")
    print(f"       Interval: {telemetry['interval_minutes']} mins")
    print(f"       Last Run Status: {telemetry['last_run_status']}")
    print(f"       Total Completed Runs: {telemetry['total_runs_completed']}")
    assert telemetry["daemon_active"] is True

    # 4b: POST /api/scraper/configure
    res_conf = client.post("/api/scraper/configure", json={"interval_minutes": 30})
    assert res_conf.status_code == 200
    print("  [OK] POST /api/scraper/configure: updated to 30 mins")

    # 4c: POST /api/scraper/trigger
    res_trig = client.post("/api/scraper/trigger")
    assert res_trig.status_code == 202
    print("  [OK] POST /api/scraper/trigger returned HTTP 202 Accepted")

    # 4d: GET /api/scraper/logs
    res_logs = client.get("/api/scraper/logs?limit=5")
    assert res_logs.status_code == 200
    logs_data = res_logs.json()
    print(f"  [OK] GET /api/scraper/logs returned {len(logs_data)} audit records")
    assert len(logs_data) > 0

    print("\n" + "=" * 70)
    print("   ALL PHASE 5 AUTOMATED SCHEDULER & HARVESTER TESTS PASSED!      ")
    print("=" * 70)


if __name__ == "__main__":
    try:
        test_phase5()
    except Exception as e:
        print(f"\n[FAIL] Phase 5 Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
