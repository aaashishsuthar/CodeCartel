from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from datetime import datetime
from ..database import Base

class AuditRun(Base):
    __tablename__ = "audit_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(String, unique=True, index=True)
    project_id = Column(String, index=True)
    run_date = Column(DateTime, default=datetime.utcnow)
    
    # Snapshot of scores during audit
    ml_probability = Column(Float)
    rule_signal = Column(Float)
    final_risk_score = Column(Float)
    risk_level = Column(String)
    
    triggered_rules = Column(JSON, default=list)
    
class Evidence(Base):
    __tablename__ = "evidence"
    
    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(String, unique=True, index=True)
    project_id = Column(String, index=True)
    audit_id = Column(String, nullable=True)
    evidence_type = Column(String) # e.g., 'document_mismatch', 'synthetic_demo'
    description = Column(String)
    source = Column(String)
    file_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
