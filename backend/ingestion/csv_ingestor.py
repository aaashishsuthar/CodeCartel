import csv
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from ..models.ingestion import IngestionRun, IngestionStatus
from ..models.project import ProjectModel
from .validators import validate_project_record
from .mapper import map_csv_to_project_dict
from collections import defaultdict

def ingest_csv(file_path: str, db: Session, source_name: str = "CSV"):
    run_id = f"RUN-{uuid.uuid4().hex[:8].upper()}"
    run = IngestionRun(
        run_id=run_id,
        source_name=source_name,
        status=IngestionStatus.RUNNING
    )
    db.add(run)
    db.commit()
    
    total = valid = invalid = duplicates = missing = 0
    error_counts = defaultdict(int)
    warning_counts = defaultdict(int)
    seen_ids = set()
    projects_to_insert = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                total += 1
                empty_fields = sum(1 for k, v in row.items() if not v or str(v).strip() == "")
                missing += empty_fields
                
                is_valid, errors, warnings = validate_project_record(row)
                
                pid = row.get("Project_ID")
                if pid in seen_ids:
                    duplicates += 1
                    is_valid = False
                    errors.append("Duplicate projects")
                elif pid:
                    seen_ids.add(pid)
                
                for e in errors: error_counts[e] += 1
                for w in warnings: warning_counts[w] += 1
                
                if is_valid:
                    valid += 1
                    projects_to_insert.append(ProjectModel(**map_csv_to_project_dict(row, run_id)))
                else:
                    invalid += 1

        if projects_to_insert:
            db.query(ProjectModel).delete()
            db.bulk_save_objects(projects_to_insert)
            
        run.total_records = total
        run.valid_records = valid
        run.invalid_records = invalid
        run.duplicate_records = duplicates
        run.missing_value_count = missing
        run.validation_errors = dict(error_counts)
        run.warnings = dict(warning_counts)
        run.status = IngestionStatus.COMPLETED
        run.end_time = datetime.utcnow()
        db.commit()
        return run
    except Exception as e:
        run.status = IngestionStatus.FAILED
        run.end_time = datetime.utcnow()
        run.validation_errors = {"system_error": str(e)}
        db.commit()
        raise e
