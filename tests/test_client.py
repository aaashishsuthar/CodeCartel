import os
import pandas as pd
from client import (
    KautilyaAPIClient,
    AuthenticationError,
    PermissionDeniedError,
    NotFoundError,
    ValidationError,
    BackendUnavailableError
)

client = KautilyaAPIClient(base_url="http://127.0.0.1:8000")

print("--- Test 1: Health Check (Unauthenticated) ---")
health = client.check_health()
print("Health:", health)
assert health["status"] == "ok"

print("\n--- Test 2: Unauthenticated Protected Call ---")
try:
    client.get_me()
    assert False, "Should have raised AuthenticationError"
except AuthenticationError as e:
    print("Caught expected AuthenticationError:", e)

print("\n--- Test 3: CAG Authentication ---")
user = client.login("auditor@mospi.gov.in", "SIH2026Kautilya")
print("Logged in user:", user)
assert user["role"] == "CAG"
assert client.is_authenticated()

print("\n--- Test 4: Fetch Projects as DataFrame ---")
df_projects = client.get_projects(limit=15, as_df=True)
print(f"Retrieved {len(df_projects)} projects as DataFrame. Columns: {list(df_projects.columns)}")
assert isinstance(df_projects, pd.DataFrame)
assert not df_projects.empty

pid = df_projects.iloc[0]["project_id"]
print(f"Sample Project ID: {pid}")

print("\n--- Test 5: Fetch Project Details ---")
detail = client.get_project(pid)
print(f"Project Detail: ID={detail['project_id']}, Work={detail['work_type']}, Risk={detail['risk_level']}")
assert detail["project_id"] == pid

print("\n--- Test 6: Fetch Vendors as DataFrame ---")
df_vendors = client.get_vendors(as_df=True)
print(f"Retrieved {len(df_vendors)} vendors as DataFrame. Top vendor: {df_vendors.iloc[0]['Vendor']} (VCI={df_vendors.iloc[0]['VCI']})")
assert isinstance(df_vendors, pd.DataFrame)
assert "VCI" in df_vendors.columns

print("\n--- Test 7: ML Scoring & Formal Audit Execution ---")
score_res = client.score_project(pid)
print("Risk assessment:", score_res["risk_assessment"])

audit_res = client.run_audit(pid)
print("Audit run response:", audit_res)
assert audit_res["status"] == "success"

history = client.get_audit_history(pid)
print(f"Audit history count for {pid}: {len(history)}")
assert len(history) >= 1

print("\n--- Test 8: Download PDF Memo via Client ---")
memo_path = "client_download_memo.pdf"
client.download_memo(pid, save_path=memo_path)
assert os.path.exists(memo_path) and os.path.getsize(memo_path) > 0
print(f"PDF Memo downloaded successfully ({os.path.getsize(memo_path)} bytes)")

print("\n--- Test 9: Model Evaluation Metrics ---")
metrics = client.get_model_metrics()
print("Model accuracy:", metrics.get("accuracy"), "F1:", metrics.get("f1"))
assert "accuracy" in metrics

print("\n--- Test 10: Switch to MP Login and Test Client RBAC Exceptions ---")
mp_user = client.login("MP001", "CF766A")
print("Logged in as MP:", mp_user["username"], mp_user["name"])
assert mp_user["role"] == "MP"

try:
    client.get_vendors()
    assert False, "Should have raised PermissionDeniedError on vendors for MP"
except PermissionDeniedError as e:
    print("Caught expected PermissionDeniedError on /api/vendors for MP:", e)

try:
    client.run_audit("MPLAD-1000")
    assert False, "Should have raised PermissionDeniedError on run_audit for MP"
except PermissionDeniedError as e:
    print("Caught expected PermissionDeniedError on run_audit for MP:", e)

# Test scoping
mp_df = client.get_projects(limit=50, as_df=True)
print(f"MP's visible projects: {len(mp_df)}")
for name in mp_df["mp_name"]:
    assert name == mp_user["name"]

client.logout()
assert not client.is_authenticated()
print("\n=== ALL PHASE 7 CLIENT ADAPTER TESTS PASSED PERFECTLY ===")
