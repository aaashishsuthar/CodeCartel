"""
Step 1 Verification: Dedicated State Nodal Authority (SNA) Role & Dashboard
Verifies SNA authentication, state slicing, district leaderboard ranking,
and MoSPI eSAKSHI telemetry connection.
"""

import sys
import os
import json
import pandas as pd

# Fix Windows console UTF-8 encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from client import KautilyaAPIClient

def test_sna_integration():
    print("================================================================================")
    print("   STEP 1 VERIFICATION: STATE NODAL AUTHORITY (SNA) ROLE & CONSOLE    ")
    print("================================================================================")

    # 1. Verify portal_credentials.json
    print("\n[Step 1] Checking portal_credentials.json...")
    with open("portal_credentials.json", "r", encoding="utf-8") as f:
        creds = json.load(f)
    assert "State Nodal Authorities (SNA)" in creds, "SNA credentials missing from portal_credentials.json"
    sna_cred = creds["State Nodal Authorities (SNA)"]
    print(f"  [OK] Found SNA credentials: username='{sna_cred['username']}', password='{sna_cred['password']}'")

    # 2. Verify SNA Login via Backend API
    print("\n[Step 2] Authenticating as State Nodal Authority via KautilyaAPIClient...")
    try:
        api = KautilyaAPIClient()
        user = api.login(sna_cred["username"], sna_cred["password"])
        df_projects = api.get_projects(limit=10000, as_df=True)
        state_telemetry = api.get_mospi_telemetry(state="Uttar Pradesh", as_df=True)
    except Exception:
        from fastapi.testclient import TestClient
        from backend.main import app as fastapi_app
        tc = TestClient(fastapi_app)
        resp = tc.post("/api/auth/login", data={"username": sna_cred["username"], "password": sna_cred["password"]})
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        user = tc.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
        resp_proj = tc.get("/api/projects", params={"limit": 10000}).json()
        df_projects = pd.DataFrame(resp_proj if isinstance(resp_proj, list) else resp_proj.get("items", []))
        resp_t = tc.get("/api/esakshi/telemetry", params={"state": "Uttar Pradesh"}).json()
        state_telemetry = pd.DataFrame(resp_t if isinstance(resp_t, list) else resp_t.get("items", []))

    assert user.get("role") == "SNA", f"Expected role 'SNA', got '{user.get('role')}'"
    print(f"  [OK] Successfully authenticated as '{user.get('name')}' (Role: {user.get('role')})")

    # 3. Verify State Slicing & District Leaderboard Aggregation
    print("\n[Step 3] Testing State Slicing & Inter-District Aggregation...")
    assert not df_projects.empty, "Database must return projects"
    
    # Check Uttar Pradesh slice
    up_slice = df_projects[df_projects["state"] == "Uttar Pradesh"]
    assert len(up_slice) > 0, "Must have records for Uttar Pradesh"
    districts = up_slice["district"].fillna(up_slice["constituency"]).dropna().unique()
    assert len(districts) >= 70, f"Expected >= 70 districts in UP, got {len(districts)}"
    print(f"  [OK] Uttar Pradesh State Slice: {len(up_slice)} projects across {len(districts)} districts.")

    # 4. Verify MoSPI eSAKSHI State Telemetry Integration
    print("\n[Step 4] Querying official MoSPI eSAKSHI state telemetry...")
    assert not state_telemetry.empty, "Must return MoSPI telemetry for Uttar Pradesh"
    up_mospi = state_telemetry.iloc[0]
    print(f"  [OK] MoSPI State ID: {up_mospi['state_id']}")
    print(f"       Official Allocation: Rs. {up_mospi['total_allocated']:,.2f}")
    print(f"       Official Disbursed: Rs. {up_mospi['total_expenditure']:,.2f}")
    print(f"       Utilization Rate: {up_mospi['avg_utilization_pct']:.1f}%")

    # 5. Verify app.py Wiring
    print("\n[Step 5] Checking app.py role mapping and routing...")
    with open("app.py", "r", encoding="utf-8") as f:
        app_code = f.read()

    assert '"State Nodal Authorities (SNA)"' in app_code, "SNA must be in ROLES"
    assert 'def render_state_nodal():' in app_code, "render_state_nodal function must be defined"
    assert '"State Nodal Authorities (SNA)": render_state_nodal' in app_code, "render_state_nodal must be in ROLE_RENDERERS"
    assert 'btn_pick_sna' in app_code, "SNA portal card button must be on Landing page"
    assert 'authenticate_sna' in app_code, "SNA authentication callback must exist"
    print("  [OK] app.py Wiring: SNA role, render function, Landing card, and Login form verified.")

    print("\n================================================================================")
    print("STEP 1 VERIFICATION SUCCESSFUL: 100% PASS")
    print("================================================================================")

if __name__ == "__main__":
    test_sna_integration()
