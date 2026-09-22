"""
Agent Kautilya — Unified Verification & Regression Test Suite Runner
Smart India Hackathon (SIH 2026) | Problem Statement SIH26102
"""

import os
import sys
import subprocess
import time

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
TESTS_DIR = os.path.join(ROOT_DIR, "tests")

# Primary verification test suites
PRIMARY_SUITES = [
    ("tests/test_step1_sna.py", "Step 1: State Nodal Authority (SNA) Console & Leaderboard"),
    ("tests/test_step2_ghost_asset.py", "Step 2: Ghost Asset & Progress Divergence Engine"),
    ("tests/test_step3_compliance.py", "Step 3: MoSPI 2023 Statutory Compliance (Annexure-II, SC/ST)"),
    ("tests/test_step4_early_warning.py", "Step 4: Early Warning Delay Radar & Lapse Risk"),
    ("tests/parity_check.py", "Step 5: Mathematical & ML Parity Benchmark Suite"),
    ("tests/test_autonomous_and_escalation.py", "Step 6: Autonomous Vigilance, Auto-Refresh & Authority Escalation"),
]

# Additional deep phase tests
PHASE_SUITES = [
    ("tests/test_phase1_db.py", "Phase 1: Database & ORM Integrity"),
    ("tests/test_phase2_harvester.py", "Phase 2: Live Ingestion Harvester"),
    ("tests/test_phase3_esakshi.py", "Phase 3: MoSPI eSAKSHI Integration"),
    ("tests/test_phase4_cleaner.py", "Phase 4: LGD Cleaner & Standardization"),
    ("tests/test_phase5_scheduler.py", "Phase 5: Background Scheduler"),
    ("tests/test_phase6_interceptor.py", "Phase 6: Pre-Sanction Interceptor"),
    ("tests/test_phase7_ui.py", "Phase 7: Live Ingestion UI Connectors"),
    ("tests/test_phase8_e2e.py", "Phase 8: End-to-End Pipeline Integrity"),
]

def run_suite(rel_path, description):
    script_path = os.path.join(ROOT_DIR, rel_path)
    if not os.path.exists(script_path):
        return False, 0.0, f"File not found: {rel_path}"

    start_time = time.time()
    env = os.environ.copy()
    env["PYTHONPATH"] = ROOT_DIR + (os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else "")
    try:
        res = subprocess.run(
            [sys.executable, script_path],
            cwd=ROOT_DIR,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        duration = time.time() - start_time
        passed = (res.returncode == 0)
        output = res.stdout if passed else (res.stdout + "\n" + res.stderr)
        return passed, duration, output
    except Exception as e:
        return False, time.time() - start_time, str(e)

def main():
    print("=" * 80)
    print("           AGENT KAUTILYA — AUTOMATED TEST & BENCHMARK SUITE")
    print("=" * 80)

    suites_to_run = PRIMARY_SUITES
    if "--all" in sys.argv:
        suites_to_run = PRIMARY_SUITES + PHASE_SUITES

    passed_count = 0
    failed_count = 0
    results = []

    for rel_path, desc in suites_to_run:
        print(f"\n[RUNNING] {desc}...")
        passed, duration, output = run_suite(rel_path, desc)
        if passed:
            passed_count += 1
            status = "PASS"
            print(f"  --> [PASS] Completed in {duration:.2f}s")
        else:
            failed_count += 1
            status = "FAIL"
            print(f"  --> [FAIL] Failed after {duration:.2f}s")
            print("--- Output ---")
            print(output[-500:] if len(output) > 500 else output)
            print("--------------")

        results.append((desc, status, duration))

    print("\n" + "=" * 80)
    print("                           SUMMARY SCORECARD")
    print("=" * 80)
    for desc, status, duration in results:
        status_str = "[PASS]" if status == "PASS" else "[FAIL]"
        print(f"  {status_str:8} | {duration:5.2f}s | {desc}")

    print("-" * 80)
    print(f"Total: {len(results)} | Passed: {passed_count} | Failed: {failed_count}")
    print("=" * 80)

    if failed_count > 0:
        sys.exit(1)
    else:
        print("\nAll verification suites executed successfully with 100% pass rate.\n")
        try:
            from package_zip import make_archive
            make_archive()
        except Exception as e:
            print(f"Archive refresh note: {e}")

if __name__ == "__main__":
    main()
