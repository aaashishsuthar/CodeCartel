"""
Agent Kautilya — Phase 4 Data Validator, Cleaner & LGD Matcher Automated Verification Script
Tests DataSanitizer, LGDDirectoryMatcher (exact, alias, fuzzy), database-wide enrichment,
FastAPI endpoints, and system parity.
"""

import sys
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.main import app
from backend.models.project import ProjectModel
from backend.ingestion.cleaner import DataCleanerEngine, LGDDirectoryMatcher, DataSanitizer


def test_phase4():
    print("=" * 70)
    print("   PHASE 4: DATA VALIDATOR, CLEANER & LGD MATCHER VERIFICATION     ")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # 1. Test DataSanitizer
    # -------------------------------------------------------------------------
    print("\n[Step 1] Testing DataSanitizer string, currency, and date cleaning...")
    sanitizer = DataSanitizer()

    # Text
    noisy_text = "   Construction of CC road \r\n\t with drain & naali nirman;;   "
    clean_text = sanitizer.clean_text(noisy_text)
    assert "\n" not in clean_text and "\r" not in clean_text
    assert clean_text == "Construction of CC road with drain & naali nirman"
    print(f"  [OK] Text Sanitized: '{clean_text}'")

    # Currency
    assert sanitizer.clean_currency("₹ 12,50,000.00") == 1250000.0
    assert sanitizer.clean_currency("Rs. 450,000") == 450000.0
    assert sanitizer.clean_currency(995562) == 995562.0
    print("  [OK] Currency Sanitized: Correctly parsed INR and Rs. currency strings to float.")

    # Agency
    raw_agency = "Office of the District Magistrate Gautam Buddha Nagar"
    clean_agency = sanitizer.clean_agency_name(raw_agency)
    assert "Office of the" not in clean_agency
    print(f"  [OK] Agency Sanitized: '{clean_agency}'")

    # -------------------------------------------------------------------------
    # 2. Test LGDDirectoryMatcher (Exact, Alias, Fuzzy)
    # -------------------------------------------------------------------------
    print("\n[Step 2] Testing Local Government Directory (LGD) Matcher...")
    
    # 2a: Exact match
    d_code, s_code, canonical = LGDDirectoryMatcher.match_district("Varanasi", "Uttar Pradesh")
    assert d_code == 178 and s_code == 9
    print(f"  [OK] Exact Match: 'Varanasi' -> District Code: {d_code}, State Code: {s_code}")

    # 2b: Alias match
    d_code, s_code, canonical = LGDDirectoryMatcher.match_district("Noida", "Uttar Pradesh")
    assert d_code == 140 and s_code == 9
    print(f"  [OK] Alias Match: 'Noida' -> Canonical: {canonical}, LGD Code: {d_code}")

    # 2c: Fuzzy match
    d_code, s_code, canonical = LGDDirectoryMatcher.match_district("Gautambudhnagar")
    assert d_code == 140
    print(f"  [OK] Fuzzy Match: 'Gautambudhnagar' -> Canonical: {canonical}, LGD Code: {d_code}")

    # 2d: Shillong / East Khasi Hills
    d_code, s_code, canonical = LGDDirectoryMatcher.match_district("Shillong", "Meghalaya")
    assert d_code == 274 and s_code == 17
    print(f"  [OK] LGD Match: 'Shillong' -> LGD District Code: {d_code}, State: {s_code}")

    # -------------------------------------------------------------------------
    # 3. Test Database Cleaning and LGD Geo-Coding Enrichment
    # -------------------------------------------------------------------------
    print("\n[Step 3] Running database-wide cleaning and LGD enrichment...")
    db: Session = SessionLocal()
    cleaner = DataCleanerEngine()
    try:
        enrichment_report = cleaner.clean_and_enrich_database(db)
        print(f"  [OK] Processed {enrichment_report['total_projects_processed']} projects.")
        print(f"       LGD District Matched: {enrichment_report['lgd_district_matched']} ({enrichment_report['lgd_match_rate_pct']}%)")
        print(f"       Data Quality Health Score: {enrichment_report['data_quality_score']}%")
        assert enrichment_report["total_projects_processed"] > 0

        # Verify a live project has LGD code assigned
        shillong_proj = db.query(ProjectModel).filter(
            ProjectModel.project_id.like("EI-%")
        ).first()
        if shillong_proj:
            print(f"       Verified Live Project: {shillong_proj.project_id}")
            print(f"       District: {shillong_proj.district} | LGD District Code: {shillong_proj.lgd_district_code} | LGD State: {shillong_proj.lgd_state_code}")
            assert shillong_proj.lgd_district_code is not None, "Live project missing LGD district code!"

    finally:
        db.close()

    # -------------------------------------------------------------------------
    # 4. Test Cleaner FastAPI REST Endpoints
    # -------------------------------------------------------------------------
    print("\n[Step 4] Testing Cleaner FastAPI REST Endpoints...")
    client = TestClient(app)

    # 4a: GET /api/cleaner/lgd-match
    res_match = client.get("/api/cleaner/lgd-match?district=Varanasi&state=Uttar%20Pradesh")
    assert res_match.status_code == 200
    match_data = res_match.json()
    assert match_data["lgd_district_code"] == 178
    print(f"  [OK] GET /api/cleaner/lgd-match: Varanasi -> Code {match_data['lgd_district_code']}")

    # 4b: GET /api/cleaner/stats
    res_stats = client.get("/api/cleaner/stats")
    assert res_stats.status_code == 200
    stats_data = res_stats.json()
    print(f"  [OK] GET /api/cleaner/stats:")
    print(f"       Total Projects: {stats_data['total_projects']}")
    print(f"       LGD Coded: {stats_data['lgd_district_coded_count']} ({stats_data['lgd_district_match_rate_pct']}%)")
    print(f"       Data Quality Score: {stats_data['data_quality_score']}% ({stats_data['cleanliness_status']})")
    assert stats_data["total_projects"] > 0

    # 4c: POST /api/cleaner/sanitize
    res_san = client.post("/api/cleaner/sanitize", json={
        "raw_text": "Bad \r\n format   text;;",
        "raw_amount": "₹ 9,96,582.00",
        "raw_agency": "Office of the District Magistrate"
    })
    assert res_san.status_code == 200
    san_data = res_san.json()
    assert san_data["cleaned_amount"] == 996582.0
    print("  [OK] POST /api/cleaner/sanitize returned sanitized values correctly")

    print("\n" + "=" * 70)
    print("     ALL PHASE 4 DATA CLEANER & LGD MATCHER TESTS PASSED!         ")
    print("=" * 70)


if __name__ == "__main__":
    try:
        test_phase4()
    except Exception as e:
        print(f"\n[FAIL] Phase 4 Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
