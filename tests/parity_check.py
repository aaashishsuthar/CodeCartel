"""
Agent Kautilya — Parity & Verification Suite (Phase 9)
Compares the SQLite + FastAPI Backend outputs against the original baseline data
to verify 100% mathematical, statistical, and forensic parity.
"""

import os
import json
import pandas as pd
import numpy as np
import sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from client import KautilyaAPIClient

BASE_DIR = r"c:/Users/Dream Different/OneDrive/Documents/vscode/New folder"
CSV_PATH = os.path.join(BASE_DIR, "projects.csv")
METRICS_PATH = os.path.join(BASE_DIR, "model_metrics.json")

def run_parity_tests():
    print("=" * 65)
    print("      AGENT KAUTILYA — PHASE 9 PARITY VERIFICATION SUITE       ")
    print("=" * 65)

    from fastapi.testclient import TestClient
    from backend.main import app as fastapi_app
    tc = TestClient(fastapi_app)
    
    class InProcessClient:
        def __init__(self):
            self.token = None
        def _h(self):
            return {"Authorization": f"Bearer {self.token}"} if self.token else {}
        def check_health(self):
            return tc.get("/api/health").json()
        def login(self, u, p):
            r = tc.post("/api/auth/login", data={"username": u, "password": p}).json()
            self.token = r["access_token"]
            return tc.get("/api/auth/me", headers=self._h()).json()
        def get_projects(self, limit=10000, as_df=False):
            res = tc.get("/api/projects", params={"limit": limit}, headers=self._h()).json()
            data = res if isinstance(res, list) else res.get("items", [])
            return pd.DataFrame(data) if as_df else data
        def score_project(self, pid):
            return tc.get(f"/api/audits/score/{pid}", headers=self._h()).json()
        def get_model_metrics(self):
            return tc.get("/api/model/metrics", headers=self._h()).json()
        def get_vendors(self, as_df=False):
            res = tc.get("/api/vendors", headers=self._h()).json()
            return pd.DataFrame(res) if as_df else res
        def run_audit(self, pid):
            return tc.post(f"/api/audits/run/{pid}", headers=self._h()).json()
        def get_evidence(self, pid):
            return tc.get(f"/api/evidence/{pid}", headers=self._h()).json()

    client = InProcessClient()
    health = client.check_health()
    assert health["status"] == "ok", "Backend health check failed!"
    print("\n[OK] 1. Backend Server is Online (In-Process FastAPI + SQLite).")
    user = client.login("auditor@mospi.gov.in", "SIH2026Kautilya")
    assert user["role"] == "CAG", "CAG login failed"
    print("[OK] 2. Authenticated as CAG Central Auditor.")

    # 3. Load Baseline Data
    assert os.path.exists(CSV_PATH), f"Missing {CSV_PATH}"
    df_baseline = pd.read_csv(CSV_PATH)
    print(f"\n[OK] 3. Baseline Dataset Loaded: {len(df_baseline)} rows.")

    # 4. Fetch Backend Data
    df_backend = client.get_projects(limit=10000, as_df=True)
    col_map = {
        "project_id": "Project_ID", "mp_name": "MP_Name", "state": "State",
        "constituency": "Constituency", "district": "District", "work_type": "Work_Type",
        "vendor": "Vendor", "sanctioned_amount": "Sanctioned_Amount",
        "allocated_ceiling": "Allocated_Ceiling", "bill_amount": "Bill_Amount",
        "uc_amount": "UC_Amount", "cumulative_sanctioned": "Cumulative_Sanctioned",
        "days_to_completion": "Days_to_Completion", "is_overrun": "Is_Overrun",
        "is_duplicate": "Is_Duplicate", "is_delayed": "Is_Delayed",
        "has_doc_mismatch": "Has_Doc_Mismatch", "duplicate_group_id": "Duplicate_Group_ID",
        "ceiling_breach": "Ceiling_Breach", "vendor_is_suspect": "Vendor_Is_Suspect",
        "model_risk_prob": "Model_Risk_Prob", "risk_score": "Risk_Score",
        "risk_level": "Risk_Level",
    }
    df_backend = df_backend.rename(columns=col_map)
    df_backend_base = df_backend[df_backend["Project_ID"].isin(df_baseline["Project_ID"])]
    df_backend_live = df_backend[~df_backend["Project_ID"].isin(df_baseline["Project_ID"])]
    print(f"[OK] 4. Backend Database Queried: {len(df_backend)} total rows returned ({len(df_backend_base)} baseline + {len(df_backend_live)} live government works).")

    # Check 1: Record Count Parity on Baseline Dataset
    assert len(df_baseline) == len(df_backend_base), f"Count mismatch! Baseline: {len(df_baseline)}, Backend Base: {len(df_backend_base)}"
    print(f"   --> Baseline Records Parity: EXACT MATCH ({len(df_backend_base)} records)")
    if len(df_backend_live) > 0:
        print(f"   --> Live Government Works Ingested: {len(df_backend_live)} records (Source: EmpoweredIndian API)")

    # Check 2: Financial Aggregation Parity
    base_sanc_sum = df_baseline["Sanctioned_Amount"].sum()
    back_sanc_sum = df_backend_base["Sanctioned_Amount"].sum()
    diff_sanc = abs(base_sanc_sum - back_sanc_sum)
    assert diff_sanc < 1.0, f"Sanctioned amount sum mismatch! Delta: {diff_sanc}"
    print(f"   --> Baseline Sanctioned Value: INR {back_sanc_sum:,.2f} (Delta: INR {diff_sanc:.2f})")

    # Check 3: Risk Level Distribution Parity
    base_counts = df_baseline["Risk_Level"].value_counts().to_dict()
    back_counts = df_backend_base["Risk_Level"].value_counts().to_dict()
    print("\n[OK] 5. Risk Tier Distribution (Baseline Dataset):")
    for tier in ["Low", "Medium", "High"]:
        b_c = base_counts.get(tier, 0)
        k_c = back_counts.get(tier, 0)
        assert b_c == k_c, f"Mismatch in {tier} risk count: Baseline {b_c} vs Backend {k_c}"
        print(f"   --> Tier {tier:6s}: Baseline={b_c:<5d} | Backend={k_c:<5d} [MATCH]")

    # Check 4: Anomaly Trigger Counts Parity
    print("\n[OK] 6. Anomaly Signal Frequency Parity:")
    for col in ["Is_Overrun", "Is_Duplicate", "Has_Doc_Mismatch", "Ceiling_Breach"]:
        b_sum = int(df_baseline[col].sum())
        k_sum = int(df_backend_base[col].sum())
        assert b_sum == k_sum, f"Mismatch in {col}: Baseline {b_sum} vs Backend {k_sum}"
        print(f"   --> {col:20s}: Baseline={b_sum:<5d} | Backend={k_sum:<5d} [MATCH]")

    # Check 5: Live Scoring Engine Parity
    print("\n[OK] 7. Live Hybrid Inference Parity (Testing 25 Random Projects):")
    sample_ids = df_baseline["Project_ID"].sample(25, random_state=42).tolist()
    max_score_delta = 0.0
    for pid in sample_ids:
        base_row = df_baseline[df_baseline["Project_ID"] == pid].iloc[0]
        base_score = round(float(base_row["Risk_Score"]), 3)
        score_res = client.score_project(pid)
        back_score = score_res["risk_assessment"]["risk_score"]
        delta = abs(base_score - back_score)
        if delta > max_score_delta:
            max_score_delta = delta
        assert delta < 0.01, f"Scoring discrepancy on {pid}: Baseline={base_score}, Backend={back_score}"

    print(f"   --> 25 Sample Projects Re-Scored in Real-Time.")
    print(f"   --> Max Scoring Delta: {max_score_delta:.4f} (Under tolerance of 0.01)")

    # Check 6: Model Evaluation Metrics Parity
    with open(METRICS_PATH, "r") as f:
        stored_metrics = json.load(f)
    api_metrics = client.get_model_metrics()
    print("\n[OK] 8. ML Model Metrics Parity:")
    for metric in ["accuracy", "precision", "recall", "f1"]:
        s_val = stored_metrics.get(metric)
        a_val = api_metrics.get(metric)
        assert s_val == a_val, f"Metrics mismatch on {metric}: {s_val} vs {a_val}"
        print(f"   --> Metric {metric.capitalize():10s}: {s_val} [MATCH]")

    # Check 7: Vendor Intelligence Parity
    df_vendors = client.get_vendors(as_df=True)
    assert not df_vendors.empty, "Vendor API returned empty"
    top_vendor = df_vendors.iloc[0]
    print(f"\n[OK] 9. Vendor Collusion Surveillance Parity:")
    print(f"   --> Total Monitored Vendors: {len(df_vendors)}")
    print(f"   --> Highest Risk Syndicate: {top_vendor['Vendor']} (VCI: {top_vendor['VCI']}, High Risk Projects: {top_vendor['High_Risk_Count']})")

    # Check 8: Official Audit & Evidence System
    high_risk_p = df_backend[df_backend["Risk_Level"] == "High"].iloc[0]
    hr_pid = high_risk_p["Project_ID"]
    audit_res = client.run_audit(hr_pid)
    assert audit_res["status"] == "success"
    evidence = client.get_evidence(hr_pid)
    print(f"\n[OK] 10. Audit & Evidence Generation:")
    print(f"   --> Project: {hr_pid}")
    print(f"   --> Formal Audit Run ID: {audit_res['audit_id']}")
    print(f"   --> Evidence Markers Created: {len(evidence)}")

    print("\n" + "=" * 65)
    print("     ALL 10 PARITY & VERIFICATION CHECKS PASSED WITH 100% ACCURACY!    ")
    print("=" * 65)

if __name__ == "__main__":
    run_parity_tests()
