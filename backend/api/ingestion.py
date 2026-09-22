from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import os

from ..database import get_db
from ..ingestion.csv_ingestor import ingest_csv
from ..models.ingestion import IngestionRun
from ..models.user import User
from ..security import require_roles

router = APIRouter()
BASE_DIR = r"c:/Users/Dream Different/OneDrive/Documents/vscode/New folder"

@router.post("/data/upload")
def upload_demo_data(
    current_user: User = Depends(require_roles("CAG")),
    db: Session = Depends(get_db)
):
    """
    Ingests and validates raw project datasets.
    Restricted to CAG / Central Authority.
    """
    csv_path = os.path.join(BASE_DIR, "projects.csv")
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="projects.csv not found")
    
    run = ingest_csv(csv_path, db)
    return {"status": "success", "run_id": run.run_id, "triggered_by": current_user.username}

@router.get("/data/ingestion-runs/{run_id}")
def get_run(
    run_id: str,
    current_user: User = Depends(require_roles("CAG")),
    db: Session = Depends(get_db)
):
    run = db.query(IngestionRun).filter(IngestionRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run

@router.get("/data/quality/{run_id}")
def get_quality(
    run_id: str,
    current_user: User = Depends(require_roles("CAG")),
    db: Session = Depends(get_db)
):
    run = db.query(IngestionRun).filter(IngestionRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return {
        "run_id": run.run_id,
        "total_records": run.total_records,
        "valid_records": run.valid_records,
        "invalid_records": run.invalid_records,
        "duplicate_records": run.duplicate_records,
        "missing_value_count": run.missing_value_count,
        "validation_errors": run.validation_errors,
        "warnings": run.warnings
    }
