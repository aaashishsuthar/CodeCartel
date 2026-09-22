from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.project import ProjectModel
from ..models.user import User
from ..services.risk_fusion import calculate_risk
from ..services.report_service import generate_audit_memo
from ..security import get_current_user, validate_project_access

router = APIRouter()

@router.get("/memo/{project_id}")
def download_memo(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(ProjectModel).filter(ProjectModel.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    validate_project_access(project, current_user)
    risk_data = calculate_risk(project)
    
    project_data = {c.name: getattr(project, c.name) for c in project.__table__.columns}
    pdf_path = generate_audit_memo(project_data, risk_data)
    
    return FileResponse(
        pdf_path, 
        media_type="application/pdf", 
        filename=f"Audit_Memo_{project_id}.pdf"
    )
