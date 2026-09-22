"""
Agent Kautilya — Official MoSPI eSAKSHI REST API Router
Exposes endpoints to query official Government of India state identifiers,
trigger live MoSPI sync, inspect state-level forensic telemetry, and view audit snapshots.
"""

import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..ingestion.connectors.esakshi import EsakshiConnector, CACHE_DIR

router = APIRouter()


class OfficialStateResponse(BaseModel):
    STATE_NAME: str
    STATE_ID: int


class StateTelemetryResponse(BaseModel):
    state_id: Optional[int] = None
    state_name: str
    total_mps: int
    total_allocated: float
    total_expenditure: float
    avg_utilization_pct: float
    total_completed_works: int
    total_projects_tracked: int
    high_risk_projects: int
    overrun_flags: int
    duplicate_flags: int
    avg_risk_score: float
    official_mospi_verified: bool


class SnapshotMeta(BaseModel):
    filename: str
    size_bytes: int
    created_at: str


@router.get("/states", response_model=List[OfficialStateResponse])
def get_official_states():
    """
    Returns official list of 36 States and Union Territories with official MoSPI State IDs.
    Fetched directly from https://mplads.mospi.gov.in/rest/PreLoginDashboardData/getStateData.
    """
    connector = EsakshiConnector()
    states = connector.fetch_official_states()
    if not states:
        raise HTTPException(status_code=502, detail="Failed to fetch state data from MoSPI eSAKSHI")
    return states


@router.post("/sync")
def sync_mospi_esakshi(db: Session = Depends(get_db)):
    """
    Triggers live synchronization and state-level audit with official MoSPI portal.
    Saves timestamped JSON snapshots to data_cache and records in scrape_logs.
    """
    connector = EsakshiConnector()
    result = connector.sync_and_audit(db)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=f"MoSPI sync failed: {result.get('error')}")
    return result


@router.get("/telemetry", response_model=List[StateTelemetryResponse])
def get_state_telemetry(
    state: Optional[str] = Query(None, description="Filter by State Name"),
    db: Session = Depends(get_db)
):
    """
    Returns state-level forensic telemetry correlating official MoSPI State IDs
    with internal MP allocations, total expenditure, project counts, and anomaly signals.
    """
    connector = EsakshiConnector()
    official_states = connector.fetch_official_states()
    telemetry = connector.aggregate_state_telemetry(db, official_states)

    if state:
        telemetry = [t for t in telemetry if state.lower() in t["state_name"].lower()]

    return telemetry


@router.get("/snapshots", response_model=List[SnapshotMeta])
def list_snapshots():
    """
    Lists archived raw JSON snapshots fetched from official MoSPI eSAKSHI endpoints.
    Provides verifiable forensic audit evidence.
    """
    if not os.path.exists(CACHE_DIR):
        return []

    snapshots = []
    for f in sorted(os.listdir(CACHE_DIR), reverse=True):
        if f.endswith(".json"):
            path = os.path.join(CACHE_DIR, f)
            stat = os.stat(path)
            from datetime import datetime
            snapshots.append(SnapshotMeta(
                filename=f,
                size_bytes=stat.st_size,
                created_at=datetime.fromtimestamp(stat.st_mtime).isoformat()
            ))
    return snapshots
