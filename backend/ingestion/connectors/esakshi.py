"""
Agent Kautilya — Official MoSPI eSAKSHI Portal Harvester & State Telemetry Connector
Connects directly to the official Government of India Ministry of Statistics and Programme Implementation (MoSPI)
MPLADS eSAKSHI portal REST endpoints (https://mplads.mospi.gov.in/rest/PreLoginDashboardData/).
Implements snapshot caching, official State ID resolution, and state-level forensic telemetry aggregation.
"""

import os
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

import requests
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from ...models.allocation import MPAllocation
from ...models.project import ProjectModel
from ...models.scrape_log import ScrapeLog

logger = logging.getLogger("agent_kautilya.connectors.esakshi")

CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data_cache",
    "esakshi_snapshots"
)


class EsakshiConnector:
    """
    Client for the official MoSPI eSAKSHI Portal REST API.
    """
    BASE_URL = "https://mplads.mospi.gov.in"
    STATE_DATA_ENDPOINT = "/rest/PreLoginDashboardData/getStateData"
    GRAPH_DATA_ENDPOINT = "/rest/PreLoginDashboardData/getgraphdata"
    CONSTITUENCY_DATA_ENDPOINT = "/rest/PreLoginDashboardData/getConstituencyData"

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "https://mplads.mospi.gov.in",
        "Referer": "https://mplads.mospi.gov.in/digigov/dashboard.html",
    }
    TIMEOUT = 25

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        os.makedirs(CACHE_DIR, exist_ok=True)

    # -------------------------------------------------------------------------
    # Snapshot Caching Helpers
    # -------------------------------------------------------------------------

    def _save_snapshot(self, name: str, data: Any) -> str:
        """
        Saves timestamped raw JSON payload for forensic audit trail.
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.json"
        filepath = os.path.join(CACHE_DIR, filename)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({
                    "snapshot_name": name,
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": self.base_url,
                    "data": data
                }, f, indent=2)
            return filepath
        except Exception as e:
            logger.warning(f"Failed to write snapshot to {filepath}: {e}")
            return ""

    def get_latest_snapshot(self, name: str = "state_data") -> Optional[Dict[str, Any]]:
        """
        Loads the most recently saved snapshot from cache.
        """
        if not os.path.exists(CACHE_DIR):
            return None
        files = [f for f in os.listdir(CACHE_DIR) if f.startswith(name) and f.endswith(".json")]
        if not files:
            return None
        files.sort(reverse=True)
        latest_path = os.path.join(CACHE_DIR, files[0])
        try:
            with open(latest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading snapshot {latest_path}: {e}")
            return None

    # -------------------------------------------------------------------------
    # Live MoSPI REST Endpoints
    # -------------------------------------------------------------------------

    def fetch_official_states(self, combo: str = "0,0,0,2,7") -> List[Dict[str, Any]]:
        """
        Pulls official State / UT list and MoSPI State IDs from getStateData.
        combo parameter: state,constituency,mp,house,tenure
        (default: '0,0,0,2,7' -> All, All, All, Lok Sabha, 18th Lok Sabha)
        """
        url = f"{self.base_url}{self.STATE_DATA_ENDPOINT}"
        payload = {"combo": combo}
        try:
            resp = requests.post(url, headers=self.DEFAULT_HEADERS, json=payload, timeout=self.TIMEOUT)
            resp.raise_for_status()
            states = resp.json()
            if isinstance(states, list) and len(states) > 0:
                self._save_snapshot("state_data", states)
                return states
            return []
        except Exception as e:
            logger.error(f"Failed to fetch official state list from MoSPI {url}: {e}")
            # Fallback to cached snapshot if offline
            cached = self.get_latest_snapshot("state_data")
            if cached and "data" in cached:
                logger.info("Using cached MoSPI state snapshot fallback.")
                return cached["data"]
            return []

    # -------------------------------------------------------------------------
    # State-Level Forensic Telemetry Aggregation
    # -------------------------------------------------------------------------

    def aggregate_state_telemetry(self, db: Session, official_states: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Correlates official MoSPI State IDs with internal database allocations,
        project counts, expenditure ratios, and anomaly signals.
        """
        results = []

        # Create quick lookup mapping of normalized state names to State IDs
        state_id_map = {
            s["STATE_NAME"].strip().lower(): s.get("STATE_ID")
            for s in official_states if "STATE_NAME" in s
        }

        # Query aggregated MP metrics by state
        mp_stats = db.query(
            MPAllocation.state,
            func.count(MPAllocation.id).label("total_mps"),
            func.sum(MPAllocation.allocated_amount).label("total_allocated"),
            func.sum(MPAllocation.total_expenditure).label("total_expenditure"),
            func.avg(MPAllocation.utilization_pct).label("avg_utilization"),
            func.sum(MPAllocation.completed_works).label("total_completed_works")
        ).group_by(MPAllocation.state).all()

        # Query project counts and risk by state
        proj_stats = db.query(
            ProjectModel.state,
            func.count(ProjectModel.id).label("total_projects"),
            func.sum(case((ProjectModel.risk_level == "High", 1), else_=0)).label("high_risk_projects"),
            func.sum(case((ProjectModel.is_overrun == 1, 1), else_=0)).label("overrun_count"),
            func.sum(case((ProjectModel.is_duplicate == 1, 1), else_=0)).label("duplicate_count"),
            func.avg(ProjectModel.risk_score).label("avg_risk_score")
        ).group_by(ProjectModel.state).all()

        proj_map = {
            (p.state or "").strip().lower(): p
            for p in proj_stats if p.state
        }

        for s in mp_stats:
            state_name = s.state or "Unknown"
            norm_name = state_name.strip().lower()
            state_id = state_id_map.get(norm_name)
            p_data = proj_map.get(norm_name)

            tot_alloc = float(s.total_allocated or 0.0)
            tot_exp = float(s.total_expenditure or 0.0)
            avg_util = float(s.avg_utilization or 0.0)

            tot_proj = int(p_data.total_projects) if p_data else 0
            high_risk = int(p_data.high_risk_projects) if p_data else 0
            overruns = int(p_data.overrun_count) if p_data else 0
            duplicates = int(p_data.duplicate_count) if p_data else 0
            avg_risk = round(float(p_data.avg_risk_score or 0.0), 3) if p_data else 0.0

            results.append({
                "state_id": state_id,
                "state_name": state_name,
                "total_mps": s.total_mps,
                "total_allocated": tot_alloc,
                "total_expenditure": tot_exp,
                "avg_utilization_pct": round(avg_util, 2),
                "total_completed_works": s.total_completed_works or 0,
                "total_projects_tracked": tot_proj,
                "high_risk_projects": high_risk,
                "overrun_flags": overruns,
                "duplicate_flags": duplicates,
                "avg_risk_score": avg_risk,
                "official_mospi_verified": state_id is not None
            })

        # Sort by total allocated descending
        results.sort(key=lambda x: x["total_allocated"], reverse=True)
        return results

    # -------------------------------------------------------------------------
    # Master Sync Pipeline
    # -------------------------------------------------------------------------

    def sync_and_audit(self, db: Session) -> Dict[str, Any]:
        """
        Executes an official eSAKSHI audit and synchronization run:
          1. Queries MoSPI getStateData.
          2. Generates state-level forensic telemetry.
          3. Archives raw snapshot for audit proof.
          4. Logs session in scrape_logs.
        """
        scrape_id = f"SCRAPE-MOSPI-{uuid.uuid4().hex[:8].upper()}"
        log_entry = ScrapeLog(
            scrape_id=scrape_id,
            source_name="eSAKSHI (MoSPI)",
            endpoint_url=f"{self.base_url}{self.STATE_DATA_ENDPOINT}",
            status="RUNNING",
            records_fetched=0,
            records_inserted=0,
            created_at=datetime.utcnow()
        )
        db.add(log_entry)
        db.commit()

        try:
            # 1. Fetch official states
            official_states = self.fetch_official_states()
            n_states = len(official_states)

            # 2. Compute state forensic rollups
            telemetry = self.aggregate_state_telemetry(db, official_states)

            # 3. Update ScrapeLog
            log_entry.status = "SUCCESS" if n_states > 0 else "PARTIAL"
            log_entry.records_fetched = n_states
            log_entry.records_inserted = len(telemetry)
            log_entry.snapshot_date = datetime.utcnow()
            db.commit()

            return {
                "success": True,
                "scrape_id": scrape_id,
                "source": "MoSPI eSAKSHI Portal",
                "official_states_count": n_states,
                "states_analyzed": len(telemetry),
                "timestamp": datetime.utcnow().isoformat(),
                "telemetry_sample": telemetry[:5],
            }

        except Exception as e:
            logger.exception(f"eSAKSHI sync failed: {e}")
            log_entry.status = "FAILED"
            log_entry.error_message = str(e)
            db.commit()
            return {
                "success": False,
                "scrape_id": scrape_id,
                "error": str(e)
            }
