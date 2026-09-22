from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional, Literal

from ..database import get_db
from ..models.project import ProjectModel
from ..models.user import User
from ..schemas.project import ProjectDetailResponse
from ..security import get_current_user, get_optional_current_user, validate_project_access

router = APIRouter()

@router.get("/projects", response_model=List[ProjectDetailResponse])
def get_projects(
    skip: int = Query(default=0, ge=0, description="Offset for pagination"),
    limit: int = Query(default=100, ge=1, le=10000, description="Max items to retrieve (1-10000)"),
    risk_level: Optional[Literal["Low", "Medium", "High"]] = Query(default=None),
    state: Optional[str] = Query(default=None),
    work_type: Optional[str] = Query(default=None),
    mp_name: Optional[str] = Query(default=None),
    vendor: Optional[str] = Query(default=None),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(ProjectModel)

    # Scoping by Role:
    if current_user and current_user.role == "MP":
        # MP can strictly only see their own projects
        if current_user.name:
            query = query.filter(ProjectModel.mp_name == current_user.name)
        elif current_user.constituency:
            query = query.filter(ProjectModel.constituency == current_user.constituency)
    elif current_user and current_user.role == "COLLECTOR" and current_user.constituency:
        query = query.filter(ProjectModel.constituency == current_user.constituency)
    else:
        # Central CAG or public citizen - apply requested filter
        if mp_name:
            query = query.filter(ProjectModel.mp_name.ilike(f"%{mp_name}%"))

    # Apply general filters with validation
    if risk_level:
        query = query.filter(ProjectModel.risk_level == risk_level)
    if state:
        query = query.filter(ProjectModel.state.ilike(f"%{state}%"))
    if work_type:
        query = query.filter(ProjectModel.work_type.ilike(f"%{work_type}%"))
    if vendor:
        query = query.filter(ProjectModel.vendor == vendor)

    projects = query.offset(skip).limit(limit).all()
    return projects

@router.get("/projects/{project_id}", response_model=ProjectDetailResponse)
def get_project_by_id(
    project_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(ProjectModel).filter(ProjectModel.project_id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found."
        )

    # RBAC check if logged in
    if current_user:
        validate_project_access(project, current_user)

    return project
