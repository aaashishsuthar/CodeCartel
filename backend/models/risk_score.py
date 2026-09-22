from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from ..database import Base

class RiskScoreRecord(Base):
    __tablename__ = "risk_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String, index=True, nullable=False)
    ml_probability = Column(Float, nullable=True)
    rule_signal = Column(Float, nullable=True)
    composite_risk = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False)
    ceiling_breach_flag = Column(Integer, default=0)
    duplicate_flag = Column(Integer, default=0)
    doc_mismatch_flag = Column(Integer, default=0)
    vendor_suspect_flag = Column(Integer, default=0)
    rate_inflation_flag = Column(Integer, default=0)
    triggered_rules = Column(String, nullable=True)
    calculated_at = Column(DateTime, default=datetime.utcnow)
