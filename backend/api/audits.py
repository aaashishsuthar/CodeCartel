from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models.project import ProjectModel
from ..models.audit import AuditRun
from ..models.user import User
from ..services.risk_fusion import calculate_risk
from ..services.audit_service import run_project_audit
from ..security import get_current_user, require_roles, validate_project_access

router = APIRouter()

@router.get("/score/{project_id}")
def score_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(ProjectModel).filter(ProjectModel.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        
    validate_project_access(project, current_user)
    risk_data = calculate_risk(project)
    return {"project_id": project.project_id, "risk_assessment": risk_data}

@router.post("/run/{project_id}")
def run_audit(
    project_id: str,
    current_user: User = Depends(require_roles("CAG", "COLLECTOR")),
    db: Session = Depends(get_db)
):
    project = db.query(ProjectModel).filter(ProjectModel.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    validate_project_access(project, current_user)
    audit = run_project_audit(project_id, db)
    return {"status": "success", "audit_id": audit.audit_id, "triggered_by": current_user.username}
    
@router.get("/history/{project_id}")
def get_audit_history(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(ProjectModel).filter(ProjectModel.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    validate_project_access(project, current_user)
    return db.query(AuditRun).filter(AuditRun.project_id == project_id).order_by(AuditRun.run_date.desc()).all()
