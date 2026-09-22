"""
Agent Kautilya — Data Cleaning & LGD Geo-Coding REST API Router
Exposes endpoints to lookup Local Government Directory (LGD) district/state codes,
trigger database-wide cleaning and LGD enrichment, and inspect dataset health metrics.
"""

from typing import Dict, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..ingestion.cleaner import DataCleanerEngine, LGDDirectoryMatcher, DataSanitizer
from ..models.project import ProjectModel

router = APIRouter()


class LGDMatchResponse(BaseModel):
    query_district: str
    query_state: Optional[str] = None
    canonical_name: str
    lgd_district_code: Optional[int] = None
    lgd_state_code: Optional[int] = None
    match_status: str


class DataQualityStatsResponse(BaseModel):
    total_projects: int
    lgd_district_coded_count: int
    lgd_state_coded_count: int
    lgd_district_match_rate_pct: float
    data_quality_score: float
    cleanliness_status: str


class SanitizeRequest(BaseModel):
    raw_text: Optional[str] = None
    raw_amount: Optional[str] = None
    raw_agency: Optional[str] = None


@router.get("/lgd-match", response_model=LGDMatchResponse)
def lookup_lgd_district(
    district: str = Query(..., description="District or Constituency name"),
    state: Optional[str] = Query(None, description="State name for bounded matching")
):
    """
    Looks up official Local Government Directory (LGD) district and state codes
    using exact dictionary matching, alias crosswalks, and fuzzy string distance.
    """
    d_code, s_code, canonical = LGDDirectoryMatcher.match_district(district, state)
    status = "EXACT_OR_ALIAS" if d_code is not None else ("STATE_ONLY" if s_code is not None else "UNMATCHED")

    return LGDMatchResponse(
        query_district=district,
        query_state=state,
        canonical_name=canonical,
        lgd_district_code=d_code,
        lgd_state_code=s_code,
        match_status=status
    )


@router.post("/clean-database")
def trigger_database_clean_and_enrich(db: Session = Depends(get_db)):
    """
    Scans all projects in the database:
      - Sanitizes text, removes embedded newlines and noise characters
      - Enriches records with official LGD district and state codes
      - Calculates overall database data quality score
    """
    cleaner = DataCleanerEngine()
    result = cleaner.clean_and_enrich_database(db)
    return result


@router.get("/stats", response_model=DataQualityStatsResponse)
def get_data_quality_stats(db: Session = Depends(get_db)):
    """
    Returns current database-wide LGD code coverage and data quality score.
    """
    total = db.query(func.count(ProjectModel.id)).scalar() or 0
    d_coded = db.query(func.count(ProjectModel.id)).filter(
        ProjectModel.lgd_district_code.isnot(None)
    ).scalar() or 0
    s_coded = db.query(func.count(ProjectModel.id)).filter(
        ProjectModel.lgd_state_code.isnot(None)
    ).scalar() or 0

    match_rate = round((d_coded / total * 100), 2) if total > 0 else 0.0
    quality = min(100.0, round(70.0 + (match_rate * 0.3), 1))
    status = "EXCELLENT" if quality >= 85 else ("GOOD" if quality >= 70 else "NEEDS_CLEANING")

    return DataQualityStatsResponse(
        total_projects=total,
        lgd_district_coded_count=d_coded,
        lgd_state_coded_count=s_coded,
        lgd_district_match_rate_pct=match_rate,
        data_quality_score=quality,
        cleanliness_status=status
    )


@router.post("/sanitize")
def sanitize_sample_data(payload: SanitizeRequest):
    """
    Utility endpoint to test string, currency, and agency cleaning.
    """
    sanitizer = DataSanitizer()
    return {
        "cleaned_text": sanitizer.clean_text(payload.raw_text),
        "cleaned_amount": sanitizer.clean_currency(payload.raw_amount),
        "cleaned_agency": sanitizer.clean_agency_name(payload.raw_agency),
    }
