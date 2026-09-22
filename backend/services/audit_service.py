from sqlalchemy.orm import Session
from ..models.project import ProjectModel
from ..models.audit import AuditRun, Evidence
from .risk_fusion import calculate_risk
import uuid
from datetime import datetime

def run_project_audit(project_id: str, db: Session):
    project = db.query(ProjectModel).filter(ProjectModel.project_id == project_id).first()
    if not project:
        return None
        
    risk_data = calculate_risk(project)
    audit_id = f"AUDIT-{datetime.utcnow().year}-{uuid.uuid4().hex[:6].upper()}"
    
    audit_run = AuditRun(
        audit_id=audit_id,
        project_id=project_id,
        ml_probability=risk_data["ml_probability"],
        rule_signal=risk_data["rule_signal"],
        final_risk_score=risk_data["risk_score"],
        risk_level=risk_data["risk_level"],
        triggered_rules=risk_data["rules"]["triggered_rules"]
    )
    db.add(audit_run)
    
    # Generate mock synthetic evidence if high risk
    if risk_data["risk_score"] > 0.66:
        ev = Evidence(
            evidence_id=f"EV-{uuid.uuid4().hex[:8].upper()}",
            project_id=project_id,
            audit_id=audit_id,
            evidence_type="synthetic_demo",
            description="High risk anomaly detected by Agent Kautilya. System generated evidence marker.",
            source="Agent Kautilya Fusion Engine"
        )
        db.add(ev)
        
    db.commit()
    return audit_run
