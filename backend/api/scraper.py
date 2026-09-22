"""
Agent Kautilya — Background Scraper & Automated Scheduler REST API Router
Exposes endpoints to monitor the background harvesting daemon, trigger instant live sync,
reconfigure sync frequency, and review automated scrape logs.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..database import get_db
from ..models.scrape_log import ScrapeLog
from ..services.scheduler import scheduler_daemon

router = APIRouter()


class SchedulerConfigPayload(BaseModel):
    interval_minutes: int = Field(default=60, ge=1, le=10080, description="Sync frequency in minutes (1 to 10080)")


class ScraperTelemetryResponse(BaseModel):
    daemon_active: bool
    interval_minutes: int
    next_scheduled_run: Optional[str] = None
    last_run_time: Optional[str] = None
    last_run_status: str
    total_runs_completed: int
    last_run_summary: Optional[Dict[str, Any]] = None


class ScrapeLogDetail(BaseModel):
    scrape_id: str
    source_name: str
    endpoint_url: Optional[str] = None
    status: str
    records_fetched: int
    records_inserted: int
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


@router.get("/status", response_model=ScraperTelemetryResponse)
def get_scraper_status():
    """
    Returns live telemetry on the automated background harvesting daemon:
      - Active state
      - Configured interval
      - Next scheduled run timestamp
      - Last run result and breakdown
      - Total completed runs
    """
    return scheduler_daemon.get_telemetry()


@router.post("/trigger", status_code=status.HTTP_202_ACCEPTED)
def trigger_immediate_harvest():
    """
    Triggers an instant on-demand harvest cycle in a non-blocking background thread:
      1. Pulls live MP summaries and completed works from Empowered Indian API.
      2. Syncs official state data from MoSPI eSAKSHI.
      3. Sanitizes and LGD geo-codes newly inserted records.
      4. Records session in scrape_logs.
    """
    res = scheduler_daemon.trigger_async()
    return res


@router.post("/configure")
def configure_scheduler(payload: SchedulerConfigPayload):
    """
    Updates the periodic harvest interval (in minutes).
    """
    scheduler_daemon.set_interval(payload.interval_minutes)
    return {
        "success": True,
        "message": f"Harvest interval updated to every {payload.interval_minutes} minutes.",
        "interval_minutes": payload.interval_minutes
    }


@router.post("/start")
def start_scheduler():
    """
    Starts the background scheduler daemon if stopped.
    """
    if not scheduler_daemon.is_running:
        scheduler_daemon.start()
        return {"status": "SUCCESS", "message": "Scheduler daemon started."}
    return {"status": "ALREADY_RUNNING", "message": "Scheduler daemon is already active."}


@router.post("/stop")
def stop_scheduler():
    """
    Stops the background scheduler daemon.
    """
    if scheduler_daemon.is_running:
        scheduler_daemon.stop()
        return {"status": "SUCCESS", "message": "Scheduler daemon stopped."}
    return {"status": "ALREADY_STOPPED", "message": "Scheduler daemon is not running."}


@router.get("/logs", response_model=List[ScrapeLogDetail])
def get_scraper_logs(
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Returns full chronological audit log of all automated and manual scraping runs.
    """
    logs = db.query(ScrapeLog).order_by(desc(ScrapeLog.created_at)).limit(limit).all()
    return logs
