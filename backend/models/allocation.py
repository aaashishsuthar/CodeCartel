from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from ..database import Base

class MPAllocation(Base):
    __tablename__ = "mp_allocations"
    
    id = Column(Integer, primary_key=True, index=True)
    mp_id = Column(String, index=True, nullable=True)
    mp_name = Column(String, index=True, nullable=False)
    house = Column(String, default="Lok Sabha")
    state = Column(String, index=True, nullable=False)
    constituency = Column(String, index=True, nullable=True)
    
    allocated_amount = Column(Float, default=50000000.0) # Rs 5 Crore
    total_expenditure = Column(Float, default=0.0)
    total_recommended = Column(Float, default=0.0)
    utilization_pct = Column(Float, default=0.0)
    
    completed_works = Column(Integer, default=0)
    recommended_works = Column(Integer, default=0)
    
    data_source = Column(String, default="Official MoSPI Ceilings")
    updated_at = Column(DateTime, default=datetime.utcnow)
