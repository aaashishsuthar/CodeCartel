from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from ..database import Base

class Vendor(Base):
    __tablename__ = "vendors"
    
    id = Column(Integer, primary_key=True, index=True)
    vendor_name = Column(String, unique=True, index=True, nullable=False)
    total_works = Column(Integer, default=0)
    districts_count = Column(Integer, default=1)
    states_count = Column(Integer, default=1)
    total_value = Column(Float, default=0.0)
    vci_score = Column(Float, default=0.0)
    is_suspect = Column(Integer, default=0)
    high_risk_count = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow)


class AuthorityNotice(Base):
    __tablename__ = "authority_notices"

    id = Column(Integer, primary_key=True, index=True)
    notice_id = Column(String, unique=True, index=True, nullable=False)
    vendor_name = Column(String, index=True, nullable=False)
    authority_tier = Column(String, nullable=False)
    authority_email = Column(String, nullable=False)
    statutory_grounds = Column(String, nullable=False)
    urgency = Column(String, default="IMMEDIATE")
    recommended_action = Column(String, nullable=False)
    status = Column(String, default="DISPATCHED")
    action_taken = Column(String, nullable=True)
    action_taken_by = Column(String, nullable=True)
    action_taken_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
