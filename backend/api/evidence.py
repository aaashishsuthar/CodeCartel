from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.audit import Evidence
from ..models.project import ProjectModel
from ..models.user import User
from ..security import get_current_user, validate_project_access

router = APIRouter()

@router.get("/project/{project_id}")
def get_project_evidence(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(ProjectModel).filter(ProjectModel.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    validate_project_access(project, current_user)
    return db.query(Evidence).filter(Evidence.project_id == project_id).all()
