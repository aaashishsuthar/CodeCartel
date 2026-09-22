from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from ..database import Base

class ScrapeLog(Base):
    __tablename__ = "scrape_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    scrape_id = Column(String, unique=True, index=True, nullable=False)
    source_name = Column(String, index=True, nullable=False) # e.g. eSAKSHI, EmpoweredIndian, data.gov.in
    endpoint_url = Column(String, nullable=True)
    status = Column(String, default="SUCCESS") # SUCCESS, PARTIAL, FAILED
    records_fetched = Column(Integer, default=0)
    records_inserted = Column(Integer, default=0)
    error_message = Column(String, nullable=True)
    snapshot_date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
