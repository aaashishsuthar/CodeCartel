"""
Step 2 Verification: Physical vs. Financial Progress Divergence ("Ghost Asset" Anomaly Indicator)
Verifies:
1. Deterministic calculation of Financial_Disbursed_Pct, Progress_Divergence_Pct, and Ghost_Asset_Risk.
2. Flagging of 34 ghost assets with premature disbursements (>= 70%) and lagging physical milestones (<= 35%).
3. FORENSIC_COLS inclusion and server-side masking in mask_forensics().
4. National, State, and District console wiring for Ghost Asset vigilance.
"""

import sys
import os
import pandas as pd

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

def test_ghost_asset_divergence():
    print("================================================================================")
    print(" STEP 2 VERIFICATION: PHYSICAL VS FINANCIAL PROGRESS DIVERGENCE (GHOST ASSETS)  ")
    print("================================================================================")

    # 1. Verify app.py imports and load_data() output
    print("\n[Step 1] Testing load_data() output schema in app.py...")
    import app
    df = app.load_data()
    assert isinstance(df, pd.DataFrame), "load_data() must return a DataFrame"
    assert not df.empty, "Dataset must not be empty"

    required_cols = ["Financial_Disbursed_Pct", "Progress_Divergence_Pct", "Ghost_Asset_Risk", "Milestone_Pct", "Disbursed_Amount"]
    for col in required_cols:
        assert col in df.columns, f"Missing required forensic column: {col}"
    print(f"  [OK] Successfully loaded {len(df)} projects with all Ghost Asset forensic columns.")

    # 2. Verify Ghost Asset Flagging Criteria
    print("\n[Step 2] Validating Ghost Asset anomaly detection...")
    ghosts = df[df["Ghost_Asset_Risk"] == 1]
    ghost_count = len(ghosts)
    base_ghosts = df[(df["Project_ID"].astype(str).str.startswith("MPLAD-")) & (df["Ghost_Asset_Risk"] == 1)]
    print(f"  --> Total Ghost Assets Detected: {ghost_count} ({len(base_ghosts)} baseline + {ghost_count - len(base_ghosts)} newly piled live cases)")
    assert len(base_ghosts) == 34, f"Expected exactly 34 baseline ghost assets, found {len(base_ghosts)}"
    assert ghost_count >= 34, f"Expected at least 34 ghost assets, found {ghost_count}"

    # Verify physical vs financial thresholds
    for _, r in ghosts.iterrows():
        assert r["Financial_Disbursed_Pct"] >= 70.0, f"Ghost asset {r['Project_ID']} disbursed < 70%: {r['Financial_Disbursed_Pct']}%"
        assert r["Milestone_Pct"] <= 35.0, f"Ghost asset {r['Project_ID']} milestone > 35%: {r['Milestone_Pct']}%"
        assert r["Progress_Divergence_Pct"] >= 35.0, f"Ghost asset {r['Project_ID']} divergence < 35%: {r['Progress_Divergence_Pct']}%"

    avg_div = ghosts["Progress_Divergence_Pct"].mean()
    min_div = ghosts["Progress_Divergence_Pct"].min()
    max_div = ghosts["Progress_Divergence_Pct"].max()
    total_trapped = ghosts["Disbursed_Amount"].sum()
    print(f"  [OK] Anomaly Thresholds Verified: 100% of ghost assets have Disbursed >= 70% & Physical <= 35%.")
    print(f"       Average Divergence Gap: {avg_div:.1f}% (Min: {min_div:.1f}%, Max: {max_div:.1f}%)")
    print(f"       Total Public Outlay at Risk: INR {total_trapped:,.2f}")

    # 3. Verify FORENSIC_COLS & Server-Side Role Masking
    print("\n[Step 3] Checking FORENSIC_COLS and server-side masking...")
    assert "Ghost_Asset_Risk" in app.FORENSIC_COLS, "Ghost_Asset_Risk must be in FORENSIC_COLS"
    assert "Progress_Divergence_Pct" in app.FORENSIC_COLS, "Progress_Divergence_Pct must be in FORENSIC_COLS"
    assert "Financial_Disbursed_Pct" in app.FORENSIC_COLS, "Financial_Disbursed_Pct must be in FORENSIC_COLS"

    masked_df = app.mask_forensics(df)
    assert "Ghost_Asset_Risk" not in masked_df.columns, "Ghost_Asset_Risk must be masked for citizen/MP"
    assert "Progress_Divergence_Pct" not in masked_df.columns, "Progress_Divergence_Pct must be masked"
    assert "Financial_Disbursed_Pct" not in masked_df.columns, "Financial_Disbursed_Pct must be masked"
    print("  [OK] Server-side forensic masking verified: all Ghost Asset signals withheld from public tier.")

    # 4. Verify UI Wiring across Governance Consoles
    print("\n[Step 4] Checking UI wiring across Ministry, State, and District tiers...")
    with open("app.py", "r", encoding="utf-8") as f:
        app_code = f.read()

    assert "Ghost Assets Detected" in app_code, "Ghost Assets KPI card must be in render_ministry_macro"
    assert "Ghost Asset Radar (Physical vs Financial)" in app_code, "Ghost Asset Radar tab must exist in ministry console"
    assert "CRITICAL GHOST ASSET ZONE" in app_code, "Radar scatter plot must highlight critical ghost asset quadrant"
    assert "Ghost Asset Risk" in app_code, "Ghost Asset Risk card must be in render_state_nodal"
    assert "CRITICAL GHOST ASSET VIGILANCE" in app_code, "District Collector console must alert on ghost assets"
    print("  [OK] All 3 governance tiers (Ministry, State Nodal, District Collector) wired with Ghost Asset intelligence.")

    print("\n================================================================================")
    print(" STEP 2 VERIFICATION SUCCESSFUL: 100% PASS (34 GHOST ASSETS DETECTED & MAPPED)   ")
    print("================================================================================")

if __name__ == "__main__":
    test_ghost_asset_divergence()
