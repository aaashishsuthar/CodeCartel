"""
Agent Kautilya — Live Government Harvester REST API Router
Exposes endpoints to trigger real-time harvesting from Empowered Indian & eSAKSHI,
inspect live MP allocation summaries, view harvester sync state, and review scrape logs.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from ..database import get_db
from ..ingestion.connectors.empowered_indian import EmpoweredIndianConnector
from ..models.allocation import MPAllocation
from ..models.project import ProjectModel
from ..models.scrape_log import ScrapeLog
from ..models.vendor import Vendor

router = APIRouter()


class HarvestTriggerRequest(BaseModel):
    sync_mps: bool = Field(default=True, description="Whether to harvest MP allocation summaries")
    max_constituencies: int = Field(default=3, ge=1, le=50, description="Max constituencies to fetch completed works for")
    constituencies: Optional[List[str]] = Field(default=None, description="Explicit list of constituencies to harvest")


class ScrapeLogResponse(BaseModel):
    scrape_id: str
    source_name: str
    endpoint_url: Optional[str] = None
    status: str
    records_fetched: int
    records_inserted: int
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class HarvesterStatusResponse(BaseModel):
    service: str = "Agent Kautilya Live Government Harvester"
    database_connected: bool = True
    total_mps_stored: int
    total_projects_stored: int
    live_government_works_stored: int
    total_vendors_tracked: int
    last_scrape_log: Optional[ScrapeLogResponse] = None
    available_connectors: List[str] = ["EmpoweredIndian", "eSAKSHI"]


@router.get("/status", response_model=HarvesterStatusResponse)
def get_harvester_status(db: Session = Depends(get_db)):
    """
    Returns telemetry on live ingestion status, stored records count, and last scrape run.
    """
    total_mps = db.query(func.count(MPAllocation.id)).scalar() or 0
    total_projects = db.query(func.count(ProjectModel.id)).scalar() or 0
    live_works = db.query(func.count(ProjectModel.id)).filter(
        ProjectModel.data_source == "EmpoweredIndian API"
    ).scalar() or 0
    total_vendors = db.query(func.count(Vendor.id)).scalar() or 0

    last_log = db.query(ScrapeLog).order_by(desc(ScrapeLog.created_at)).first()

    return HarvesterStatusResponse(
        total_mps_stored=total_mps,
        total_projects_stored=total_projects,
        live_government_works_stored=live_works,
        total_vendors_tracked=total_vendors,
        last_scrape_log=last_log
    )


@router.post("/empowered-indian")
def trigger_empowered_indian_harvest(
    payload: HarvestTriggerRequest = HarvestTriggerRequest(),
    db: Session = Depends(get_db)
):
    """
    Triggers on-demand harvesting from the live Empowered Indian REST API:
      - Pulls latest MP allocation and expenditure summaries
      - Pulls itemized completed works with descriptions and costs
      - Upserts records into normalized relational tables
      - Logs audit metrics in scrape_logs
    """
    connector = EmpoweredIndianConnector()
    result = connector.harvest_batch(
        db=db,
        sync_mps=payload.sync_mps,
        constituencies=payload.constituencies,
        max_constituencies=payload.max_constituencies
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=502,
            detail=f"Empowered Indian harvesting failed: {result.get('error')}"
        )
    return result


@router.get("/mps")
def list_mp_allocations(
    state: Optional[str] = Query(None, description="Filter by State"),
    constituency: Optional[str] = Query(None, description="Filter by Constituency"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=800),
    db: Session = Depends(get_db)
):
    """
    Retrieves stored MP allocations with utilization metrics and completed works counts.
    """
    query = db.query(MPAllocation)
    if state:
        query = query.filter(MPAllocation.state.ilike(f"%{state}%"))
    if constituency:
        query = query.filter(MPAllocation.constituency.ilike(f"%{constituency}%"))

    total = query.count()
    records = query.order_by(desc(MPAllocation.utilization_pct)).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [
            {
                "mp_id": r.mp_id,
                "mp_name": r.mp_name,
                "house": r.house,
                "state": r.state,
                "constituency": r.constituency,
                "allocated_amount": r.allocated_amount,
                "total_expenditure": r.total_expenditure,
                "total_recommended": r.total_recommended,
                "utilization_pct": r.utilization_pct,
                "completed_works": r.completed_works,
                "recommended_works": r.recommended_works,
                "data_source": r.data_source,
                "updated_at": r.updated_at
            }
            for r in records
        ]
    }


@router.get("/logs", response_model=List[ScrapeLogResponse])
def get_scrape_logs(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Returns recent scrape history from scrape_logs.
    """
    logs = db.query(ScrapeLog).order_by(desc(ScrapeLog.created_at)).limit(limit).all()
    return logs


@router.get("/live-works")
def get_live_government_works(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Returns works harvested directly from external government APIs.
    """
    works = db.query(ProjectModel).filter(
        ProjectModel.data_source == "EmpoweredIndian API"
    ).order_by(desc(ProjectModel.ingested_at)).limit(limit).all()

    return {
        "count": len(works),
        "items": [
            {
                "project_id": w.project_id,
                "mp_name": w.mp_name,
                "state": w.state,
                "constituency": w.constituency,
                "district": w.district,
                "work_type": w.work_type,
                "description": w.description,
                "vendor": w.vendor,
                "sanctioned_amount": w.sanctioned_amount,
                "completion_date": w.completion_date,
                "risk_score": w.risk_score,
                "risk_level": w.risk_level,
                "data_source": w.data_source,
                "ingested_at": w.ingested_at
            }
            for w in works
        ]
    }
