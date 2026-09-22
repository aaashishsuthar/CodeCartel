import requests
import json

BASE_URL = "http://127.0.0.1:8000"

print("--- 1. Authenticating as CAG ---")
cag_res = requests.post(f"{BASE_URL}/api/auth/login", data={"username": "auditor@mospi.gov.in", "password": "SIH2026Kautilya"})
assert cag_res.status_code == 200, f"CAG login failed: {cag_res.text}"
cag_token = cag_res.json()["access_token"]
cag_headers = {"Authorization": f"Bearer {cag_token}"}
print("CAG Login OK")

print("\n--- 2. Authenticating as MP (MP001) ---")
mp_res = requests.post(f"{BASE_URL}/api/auth/login", data={"username": "MP001", "password": "CF766A"})
assert mp_res.status_code == 200, f"MP login failed: {mp_res.text}"
mp_token = mp_res.json()["access_token"]
mp_headers = {"Authorization": f"Bearer {mp_token}"}
print("MP Login OK")

print("\n--- 3. Testing RBAC: MP trying to access restricted Vendors endpoint ---")
vendor_mp_res = requests.get(f"{BASE_URL}/api/vendors", headers=mp_headers)
print(f"MP status on /api/vendors: {vendor_mp_res.status_code}")
assert vendor_mp_res.status_code == 403, f"Expected 403, got {vendor_mp_res.status_code}"
print("403 Forbidden correctly enforced on MP for /api/vendors!")

print("\n--- 4. Testing RBAC: MP trying to run formal Audit ---")
audit_mp_res = requests.post(f"{BASE_URL}/api/audits/run/MPLAD-1000", headers=mp_headers)
print(f"MP status on /api/audits/run: {audit_mp_res.status_code}")
assert audit_mp_res.status_code == 403, f"Expected 403, got {audit_mp_res.status_code}"
print("403 Forbidden correctly enforced on MP for running audits!")

print("\n--- 5. Testing MP Scoping on /api/projects ---")
mp_projects_res = requests.get(f"{BASE_URL}/api/projects", headers=mp_headers)
assert mp_projects_res.status_code == 200
mp_projects = mp_projects_res.json()
print(f"Projects returned for MP001: {len(mp_projects)}")
for p in mp_projects:
    assert p["mp_name"] == "AASHTIKAR PATIL NAGESH BAPURAO", f"Unexpected project leaked: {p['mp_name']}"
print("MP scoping verified: only projects belonging to MP001 returned!")

print("\n--- 6. Testing MP Cross-Constituency Project Detail Access ---")
# Find a project NOT belonging to MP001 using CAG
cag_projects_res = requests.get(f"{BASE_URL}/api/projects?limit=50", headers=cag_headers)
other_project = None
for p in cag_projects_res.json():
    if p["mp_name"] != "AASHTIKAR PATIL NAGESH BAPURAO":
        other_project = p
        break

assert other_project is not None
other_pid = other_project["project_id"]
print(f"Testing MP access to other MP's project: {other_pid} ({other_project['mp_name']})")
cross_res = requests.get(f"{BASE_URL}/api/projects/{other_pid}", headers=mp_headers)
print(f"Status: {cross_res.status_code}, Detail: {cross_res.json().get('detail')}")
assert cross_res.status_code == 403, f"Expected 403 for cross-MP access, got {cross_res.status_code}"
print("Cross-constituency access blocked with 403 Forbidden!")

print("\n--- 7. Testing CAG Access to restricted endpoints ---")
cag_vendor_res = requests.get(f"{BASE_URL}/api/vendors", headers=cag_headers)
assert cag_vendor_res.status_code == 200
print(f"CAG /api/vendors returned {len(cag_vendor_res.json())} vendors.")

cag_detail_res = requests.get(f"{BASE_URL}/api/projects/{other_pid}", headers=cag_headers)
assert cag_detail_res.status_code == 200
print(f"CAG successfully accessed project detail for {other_pid}.")

print("\n--- 8. Testing Input Validation Hardening ---")
invalid_param_res = requests.get(f"{BASE_URL}/api/projects?limit=9999", headers=cag_headers)
print(f"Status for limit=9999: {invalid_param_res.status_code}")
assert invalid_param_res.status_code == 422
print("Invalid pagination limit (le=500) correctly rejected with 422 Unprocessable Entity!")

invalid_risk_res = requests.get(f"{BASE_URL}/api/projects?risk_level=SuperHighRisk", headers=cag_headers)
print(f"Status for invalid risk_level: {invalid_risk_res.status_code}")
assert invalid_risk_res.status_code == 422
print("Invalid enum risk_level correctly rejected with 422 Unprocessable Entity!")

print("\nALL PHASE 6 API HARDENING & VALIDATION TESTS PASSED SUCCESSFULLY!")
