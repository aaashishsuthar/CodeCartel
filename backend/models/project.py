from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from ..database import Base

class ProjectModel(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String, unique=True, index=True, nullable=True)
    mp_name = Column(String, index=True, nullable=True)
    state = Column(String, index=True, nullable=True)
    constituency = Column(String, nullable=True)
    district = Column(String, nullable=True)
    lgd_district_code = Column(Integer, nullable=True)
    lgd_state_code = Column(Integer, nullable=True)
    
    work_type = Column(String, nullable=True)
    description = Column(String, nullable=True)
    vendor = Column(String, nullable=True)
    
    allocated_ceiling = Column(Float, nullable=True)
    sanctioned_amount = Column(Float, nullable=True)
    bill_amount = Column(Float, nullable=True)
    uc_amount = Column(Float, nullable=True)
    cumulative_sanctioned = Column(Float, nullable=True)
    expenditure = Column(Float, nullable=True)
    
    days_to_completion = Column(Integer, nullable=True)
    start_date = Column(DateTime, nullable=True)
    completion_date = Column(DateTime, nullable=True)
    status = Column(String, nullable=True)
    
    is_overrun = Column(Integer, nullable=True)
    is_duplicate = Column(Integer, nullable=True)
    is_delayed = Column(Integer, nullable=True)
    has_doc_mismatch = Column(Integer, nullable=True)
    duplicate_group_id = Column(String, nullable=True)
    ceiling_breach = Column(Integer, nullable=True)
    vendor_is_suspect = Column(Integer, nullable=True)
    
    model_risk_prob = Column(Float, nullable=True)
    risk_score = Column(Float, nullable=True)
    risk_level = Column(String, nullable=True)
    
    doc_amount_gap_pct = Column(Float, nullable=True)
    amount_ratio = Column(Float, nullable=True)
    
    data_source = Column(String, nullable=True)
    source_record_id = Column(String, nullable=True)
    ingested_at = Column(DateTime, default=datetime.utcnow)
    run_id = Column(String, nullable=True)
