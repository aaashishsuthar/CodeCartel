"""
Agent Kautilya — Real-Time Anomaly & Fraud Interceptor REST API Router
Exposes endpoints to trigger live anomaly evaluation on ingested sanctions,
simulate forensic risk for proposed works before approval, and review automated audit markers.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from ..database import get_db
from ..models.project import ProjectModel
from ..models.risk_score import RiskScoreRecord
from ..models.audit import AuditRun
from ..services.live_interceptor import LiveAnomalyInterceptor
from ..services.risk_fusion import calculate_risk

router = APIRouter()


class SimulateProjectPayload(BaseModel):
    work_type: str = Field(..., description="Type of work (e.g. Road Construction, School Building)")
    sanctioned_amount: float = Field(..., gt=0, description="Proposed budget amount in INR")
    days_to_completion: int = Field(default=180, ge=1, description="Expected duration in days")
    vendor: Optional[str] = Field(default="Standard Executing Agency", description="Implementing agency or contractor")
    allocated_ceiling: Optional[float] = Field(default=50000000.0, description="MP allocation ceiling")
    cumulative_sanctioned: Optional[float] = Field(default=0.0, description="Cumulative sanctioned to date")
    description: Optional[str] = Field(default=None, description="Detailed project description")
    district: Optional[str] = Field(default=None, description="Target district")


class InterceptorStatsResponse(BaseModel):
    total_live_works: int
    high_risk_flagged: int
    medium_risk_flagged: int
    low_risk_flagged: int
    automated_audits_active: int
    interception_mode: str = "REAL_TIME_AUTONOMOUS"


@router.post("/evaluate-batch")
def evaluate_batch_interceptions(
    filter_source: Optional[str] = Query("EmpoweredIndian API", description="Data source to evaluate"),
    auto_audit: bool = Query(True, description="Automatically initiate audit runs for high-risk sanctions"),
    db: Session = Depends(get_db)
):
    """
    Executes the full forensic evaluation pipeline across ingested government works:
      - Runs Calibrated SVM inference
      - Runs Statutory Rules (Ceiling breach, duplicate detection, rate inflation)
      - Synchronizes relational risk_scores
      - Automatically launches audit investigations for high-risk items
    """
    result = LiveAnomalyInterceptor.intercept_batch(
        db=db,
        filter_source=filter_source,
        auto_audit=auto_audit
    )
    return result


@router.post("/simulate")
def simulate_project_risk(payload: SimulateProjectPayload):
    """
    Simulates real-time forensic interception for a proposed project BEFORE sanctioning:
      - Computes ML probability of overrun using pre-trained Calibrated SVM
      - Checks statutory compliance against ceilings and benchmarks
      - Returns immediate risk tier and forensic recommendations
    """
    return LiveAnomalyInterceptor.simulate_proposal(
        work_type=payload.work_type,
        sanctioned_amount=payload.sanctioned_amount,
        days_to_completion=payload.days_to_completion,
        vendor=payload.vendor,
        allocated_ceiling=payload.allocated_ceiling,
        cumulative_sanctioned=payload.cumulative_sanctioned,
        description=payload.description,
        district=payload.district
    )


@router.get("/anomalies")
def get_live_anomalies(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Returns live government projects flagged as High Risk with their audit tracking IDs.
    """
    high_projects = db.query(ProjectModel).filter(
        ProjectModel.data_source == "EmpoweredIndian API",
        ProjectModel.risk_level == "High"
    ).order_by(desc(ProjectModel.risk_score)).limit(limit).all()

    items = []
    for p in high_projects:
        rs = db.query(RiskScoreRecord).filter(RiskScoreRecord.project_id == p.project_id).first()
        audit = db.query(AuditRun).filter(AuditRun.project_id == p.project_id).first()
        items.append({
            "project_id": p.project_id,
            "mp_name": p.mp_name,
            "district": p.district,
            "work_type": p.work_type,
            "description": p.description,
            "vendor": p.vendor,
            "sanctioned_amount": p.sanctioned_amount,
            "risk_score": p.risk_score,
            "risk_level": p.risk_level,
            "triggered_rules": rs.triggered_rules if rs else None,
            "audit_id": audit.audit_id if audit else None,
            "ingested_at": p.ingested_at
        })

    return {
        "total_anomalies": len(items),
        "items": items
    }


@router.get("/stats", response_model=InterceptorStatsResponse)
def get_interceptor_stats(db: Session = Depends(get_db)):
    """
    Returns real-time summary statistics of live government works and anomaly detections.
    """
    base_query = db.query(ProjectModel).filter(ProjectModel.data_source == "EmpoweredIndian API")
    total_live = base_query.count()
    high = base_query.filter(ProjectModel.risk_level == "High").count()
    med = base_query.filter(ProjectModel.risk_level == "Medium").count()
    low = base_query.filter(ProjectModel.risk_level == "Low").count()

    total_audits = db.query(func.count(AuditRun.id)).scalar() or 0

    return InterceptorStatsResponse(
        total_live_works=total_live,
        high_risk_flagged=high,
        medium_risk_flagged=med,
        low_risk_flagged=low,
        automated_audits_active=total_audits
    )
