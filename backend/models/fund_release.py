from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from ..database import Base

class FundRelease(Base):
    __tablename__ = "fund_releases"
    
    id = Column(Integer, primary_key=True, index=True)
    tranche_id = Column(String, unique=True, index=True, nullable=False)
    project_id = Column(String, index=True, nullable=False)
    installment_no = Column(Integer, default=1)
    release_date = Column(DateTime, nullable=True)
    disbursed_amount = Column(Float, nullable=False)
    implementing_agency = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
