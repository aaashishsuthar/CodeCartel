import os
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from datetime import datetime
from ..database import Base
import enum

class IngestionStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, unique=True, index=True)
    source_name = Column(String)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    status = Column(String, default=IngestionStatus.PENDING)
    
    total_records = Column(Integer, default=0)
    valid_records = Column(Integer, default=0)
    invalid_records = Column(Integer, default=0)
    duplicate_records = Column(Integer, default=0)
    missing_value_count = Column(Integer, default=0)
    
    validation_errors = Column(JSON, default=dict)
    warnings = Column(JSON, default=dict)
