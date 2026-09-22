from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class ProjectBase(BaseModel):
    project_id: str
    mp_name: Optional[str] = None
    state: Optional[str] = None
    constituency: Optional[str] = None
    district: Optional[str] = None
    lgd_district_code: Optional[int] = None
    lgd_state_code: Optional[int] = None
    work_type: Optional[str] = None
    description: Optional[str] = None
    vendor: Optional[str] = None
    sanctioned_amount: Optional[float] = 0.0
    risk_score: Optional[float] = 0.0
    risk_level: Optional[str] = "Low"

class ProjectResponse(ProjectBase):
    id: int
    
    class Config:
        from_attributes = True

class ProjectDetailResponse(ProjectResponse):
    allocated_ceiling: Optional[float] = None
    bill_amount: Optional[float] = None
    uc_amount: Optional[float] = None
    cumulative_sanctioned: Optional[float] = None
    expenditure: Optional[float] = None
    days_to_completion: Optional[int] = None
    is_overrun: Optional[int] = 0
    is_duplicate: Optional[int] = 0
    is_delayed: Optional[int] = 0
    has_doc_mismatch: Optional[int] = 0
    duplicate_group_id: Optional[str] = None
    ceiling_breach: Optional[int] = 0
    vendor_is_suspect: Optional[int] = 0
    model_risk_prob: Optional[float] = None
    doc_amount_gap_pct: Optional[float] = None
    amount_ratio: Optional[float] = None
    data_source: Optional[str] = None
    ingested_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ProjectFilterParams(BaseModel):
    skip: int = Field(default=0, ge=0, description="Number of records to skip")
    limit: int = Field(default=100, ge=1, le=10000, description="Max number of records (1-10000)")
    risk_level: Optional[Literal["Low", "Medium", "High"]] = Field(default=None, description="Filter by risk tier")
    state: Optional[str] = Field(default=None, max_length=100, description="Filter by State")
    work_type: Optional[str] = Field(default=None, max_length=100, description="Filter by Work Type")
    mp_name: Optional[str] = Field(default=None, max_length=150, description="Filter by MP Name")
    vendor: Optional[str] = Field(default=None, max_length=100, description="Filter by Vendor")
