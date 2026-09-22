from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from ..database import Base

class UtilizationCertificate(Base):
    __tablename__ = "utilization_certificates"
    
    id = Column(Integer, primary_key=True, index=True)
    uc_id = Column(String, unique=True, index=True, nullable=False)
    project_id = Column(String, index=True, nullable=False)
    bill_amount = Column(Float, nullable=False)
    uc_amount = Column(Float, nullable=False)
    gap_amount = Column(Float, default=0.0)
    gap_pct = Column(Float, default=0.0)
    has_mismatch = Column(Integer, default=0)
    submission_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
