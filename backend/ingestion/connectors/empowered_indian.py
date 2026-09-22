"""
Agent Kautilya — Live Works API Harvester (Empowered Indian Connector)
Connects directly to the public REST endpoints of Empowered Indian (api.empoweredindian.in),
ingests real-time MP expenditure/allocation summaries and itemized completed works,
normalizes the records into the 7-table relational schema, and records telemetry into scrape_logs.
"""

import re
import uuid
import logging
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

import requests
from sqlalchemy.orm import Session

from ...models.allocation import MPAllocation
from ...models.project import ProjectModel
from ...models.vendor import Vendor
from ...models.fund_release import FundRelease
from ...models.certificate import UtilizationCertificate
from ...models.risk_score import RiskScoreRecord
from ...models.scrape_log import ScrapeLog

logger = logging.getLogger("agent_kautilya.connectors.empowered_indian")

WORK_TYPE_KEYWORDS = [
    (r"\b(road|cc road|naali|drain|pathway|pavement|interlocking|bridge|foot bridge|link road)\b", "Road Construction"),
    (r"\b(water|drinking water|tubewell|handpump|pipeline|storage tank|boring|borewell)\b", "Drinking Water Supply"),
    (r"\b(school|classroom|smart class|iti|lab|computer lab|library|education|college|polytechnic)\b", "School Building"),
    (r"\b(hall|community|multipurpose|bhavan|panchayat|auditorium|sabha|shed)\b", "Community Hall"),
    (r"\b(health|hospital|clinic|dispensary|sub-centre|ambulance|medical|ayush|phc|chc)\b", "Health Sub-Centre"),
    (r"\b(solar|street light|lighting|high mast|led light|light)\b", "Solar Street Lighting"),
    (r"\b(sports|stadium|ground|gym|play ground|track|sports complex)\b", "Sports Infrastructure"),
]

BENCHMARK_COSTS = {
    "Road Construction": 3_500_000,
    "Drinking Water Supply": 2_200_000,
    "School Building": 5_000_000,
    "Community Hall": 2_800_000,
    "Health Sub-Centre": 4_200_000,
    "Solar Street Lighting": 1_500_000,
    "Sports Infrastructure": 3_000_000,
    "Public Works / Civic Amenity": 2_000_000,
}


class EmpoweredIndianConnector:
    """
    Client and Normalizer for the EmpoweredIndian Open MPLADS REST API.
    """
    BASE_URL = "https://api.empoweredindian.in"
    MP_SUMMARY_ENDPOINT = "/api/summary/mps"
    WORKS_COMPLETED_ENDPOINT = "/api/works/completed"
    DEFAULT_HEADERS = {
        "User-Agent": "Agent-Kautilya-Harvester/1.0 (Autonomous Forensic Intelligence Suite; SIH26102)",
        "Accept": "application/json",
    }
    TIMEOUT = 25

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or self.BASE_URL).rstrip("/")

    # -------------------------------------------------------------------------
    # REST API Fetchers
    # -------------------------------------------------------------------------

    def fetch_mp_summaries(self, page: int = 1, limit: int = 800) -> Dict[str, Any]:
        """
        Fetch MP allocations and cumulative expenditure summaries.
        Returns full response dict with 'success', 'data', 'pagination'.
        """
        url = f"{self.base_url}{self.MP_SUMMARY_ENDPOINT}?page={page}&limit={limit}"
        try:
            resp = requests.get(url, headers=self.DEFAULT_HEADERS, timeout=self.TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            return data
        except Exception as e:
            logger.error(f"Failed to fetch MP summaries from {url}: {e}")
            return {"success": False, "error": str(e), "data": []}

    def fetch_completed_works(self, constituency: str, page: int = 1, limit: int = 100) -> Dict[str, Any]:
        """
        Fetch itemized completed works for a specific constituency.
        Extracts list of works from response.
        """
        encoded_const = urllib.parse.quote(constituency.strip())
        url = f"{self.base_url}{self.WORKS_COMPLETED_ENDPOINT}?constituency={encoded_const}&page={page}&limit={limit}"
        try:
            resp = requests.get(url, headers=self.DEFAULT_HEADERS, timeout=self.TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            works = []
            if isinstance(data, dict):
                inner_data = data.get("data")
                if isinstance(inner_data, dict):
                    works = inner_data.get("completedWorks", [])
                elif isinstance(inner_data, list):
                    works = inner_data
            elif isinstance(data, list):
                works = data

            return {
                "success": True,
                "constituency": constituency,
                "data": works,
                "raw": data if isinstance(data, dict) else {},
            }
        except Exception as e:
            logger.error(f"Failed to fetch works for {constituency} from {url}: {e}")
            return {"success": False, "constituency": constituency, "error": str(e), "data": []}

    # -------------------------------------------------------------------------
    # Normalization Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def map_category(description: Optional[str], original_category: Optional[str]) -> str:
        """
        Derives standard Work_Type from project description and original category.
        """
        text = f"{description or ''} {original_category or ''}".lower()
        for pattern, std_type in WORK_TYPE_KEYWORDS:
            if re.search(pattern, text, re.IGNORECASE):
                return std_type
        if original_category and original_category not in ["Normal/Others", "Unknown", None]:
            return original_category.strip()
        return "Public Works / Civic Amenity"

    @staticmethod
    def extract_agency(location_str: Optional[str]) -> str:
        """
        Extracts implementing agency or executing body from location string.
        e.g. 'GAUTAM BUDDHA NAGAR(DISTRICT MAGISTRATE GAUTAMBUDHNAGAR)' -> 'DISTRICT MAGISTRATE GAUTAMBUDHNAGAR'
        """
        if not location_str:
            return "District Implementing Agency"
        match = re.search(r"\((.*?)\)", location_str)
        if match:
            agency = match.group(1).strip()
            if agency:
                return agency[:80]
        cleaned = location_str.split(",")[0].strip()
        return cleaned[:80] if cleaned else "District Implementing Agency"

    @staticmethod
    def parse_iso_date(date_str: Optional[str]) -> Optional[datetime]:
        """
        Safely parse ISO datetime string.
        """
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            try:
                return datetime.strptime(date_str[:10], "%Y-%m-%d")
            except Exception:
                return None

    # -------------------------------------------------------------------------
    # Relational Database Synchronization
    # -------------------------------------------------------------------------

    def sync_mp_allocations(self, db: Session, mp_records: List[Dict[str, Any]]) -> Tuple[int, int]:
        """
        Upserts MP allocations into mp_allocations table.
        Returns (updated_count, inserted_count).
        """
        updated = 0
        inserted = 0

        for r in mp_records:
            mp_name = (r.get("mpName") or "").strip()
            constituency = (r.get("constituency") or "").strip()
            state = (r.get("state") or "").strip()
            if not mp_name and not constituency:
                continue

            # Check existing record by constituency or MP name
            existing = None
            if constituency:
                existing = db.query(MPAllocation).filter(
                    MPAllocation.constituency.ilike(constituency)
                ).first()
            if not existing and mp_name:
                existing = db.query(MPAllocation).filter(
                    MPAllocation.mp_name.ilike(mp_name)
                ).first()

            alloc_amt = float(r.get("allocatedAmount") or 50000000.0)
            expenditure = float(r.get("totalExpenditure") or 0.0)
            recommended = float(r.get("totalRecommendedAmount") or 0.0)
            util_pct = float(r.get("expenditurePercentage") or r.get("utilizationPercentage") or 0.0)
            comp_works = int(r.get("completedWorksCount") or 0)
            rec_works = int(r.get("recommendedWorksCount") or 0)

            if existing:
                existing.allocated_amount = alloc_amt
                existing.total_expenditure = expenditure
                existing.total_recommended = recommended
                existing.utilization_pct = round(util_pct, 2)
                existing.completed_works = comp_works
                existing.recommended_works = rec_works
                existing.data_source = "EmpoweredIndian API"
                existing.updated_at = datetime.utcnow()
                updated += 1
            else:
                new_alloc = MPAllocation(
                    mp_id=str(r.get("id") or f"MP-{uuid.uuid4().hex[:6]}"),
                    mp_name=mp_name or "Unknown MP",
                    house=r.get("house") or "Lok Sabha",
                    state=state or "National",
                    constituency=constituency,
                    allocated_amount=alloc_amt,
                    total_expenditure=expenditure,
                    total_recommended=recommended,
                    utilization_pct=round(util_pct, 2),
                    completed_works=comp_works,
                    recommended_works=rec_works,
                    data_source="EmpoweredIndian API",
                    updated_at=datetime.utcnow()
                )
                db.add(new_alloc)
                inserted += 1

        db.commit()
        return updated, inserted

    def sync_completed_works(
        self,
        db: Session,
        constituency: str,
        works: List[Dict[str, Any]],
        run_id: str
    ) -> Tuple[int, int]:
        """
        Upserts live completed works into projects table and synchronizes:
          - fund_releases (tranche disbursal records)
          - utilization_certificates (UC records)
          - risk_scores (initial risk evaluation)
          - vendors (executing agencies)
        Returns (fetched_count, inserted_or_updated_count).
        """
        processed = 0

        # Look up MP allocation ceiling for context
        mp_alloc = db.query(MPAllocation).filter(
            MPAllocation.constituency.ilike(constituency)
        ).first()
        ceiling_amt = mp_alloc.allocated_amount if mp_alloc else 50000000.0
        mp_official_name = mp_alloc.mp_name if mp_alloc else None

        vendor_cache: Dict[str, Vendor] = {}
        for w in works:
            raw_id = w.get("work_id") or w.get("_id")
            if not raw_id:
                continue

            pid = f"EI-{raw_id}"
            cost = float(w.get("cost") or 0.0)
            desc = w.get("work_description") or ""
            work_type = self.map_category(desc, w.get("category"))
            agency = self.extract_agency(w.get("location"))
            state = w.get("state") or (mp_alloc.state if mp_alloc else "National")
            district = w.get("district") or constituency
            mp_name = (w.get("mp_details") or {}).get("name") or mp_official_name or "Hon. MP"
            comp_date = self.parse_iso_date(w.get("completion_date"))

            # Calculate amount ratio vs benchmark
            benchmark = BENCHMARK_COSTS.get(work_type, 2_000_000)
            amount_ratio = round(cost / benchmark, 2) if benchmark > 0 else 1.0

            # Calculate initial baseline risk score
            risk_prob = 0.12
            is_overrun = 0
            if amount_ratio > 1.8:
                risk_prob = min(0.85, 0.25 + (amount_ratio - 1.8) * 0.3)
                is_overrun = 1 if amount_ratio > 2.2 else 0

            risk_score = round(risk_prob, 3)
            risk_level = "High" if risk_score >= 0.66 else ("Medium" if risk_score >= 0.33 else "Low")

            # Check if project already exists
            project = db.query(ProjectModel).filter(
                (ProjectModel.project_id == pid) | (ProjectModel.source_record_id == str(raw_id))
            ).first()

            if not project:
                project = ProjectModel(
                    project_id=pid,
                    mp_name=mp_name,
                    state=state,
                    constituency=constituency,
                    district=district,
                    work_type=work_type,
                    description=desc,
                    vendor=agency,
                    allocated_ceiling=ceiling_amt,
                    sanctioned_amount=cost,
                    bill_amount=cost,
                    uc_amount=cost,
                    cumulative_sanctioned=cost,
                    expenditure=cost,
                    days_to_completion=180,
                    completion_date=comp_date,
                    status="Completed",
                    is_overrun=is_overrun,
                    is_duplicate=0,
                    is_delayed=0,
                    has_doc_mismatch=0,
                    ceiling_breach=0,
                    vendor_is_suspect=0,
                    model_risk_prob=risk_prob,
                    risk_score=risk_score,
                    risk_level=risk_level,
                    doc_amount_gap_pct=0.0,
                    amount_ratio=amount_ratio,
                    data_source="EmpoweredIndian API",
                    source_record_id=str(raw_id),
                    ingested_at=datetime.utcnow(),
                    run_id=run_id
                )
                db.add(project)
            else:
                project.sanctioned_amount = cost
                project.bill_amount = cost
                project.uc_amount = cost
                project.description = desc
                project.work_type = work_type
                project.vendor = agency
                project.amount_ratio = amount_ratio
                project.completion_date = comp_date
                project.ingested_at = datetime.utcnow()

            # Ensure Vendor record exists (using in-memory cache to prevent unique constraint collisions)
            vendor_rec = vendor_cache.get(agency)
            if not vendor_rec:
                vendor_rec = db.query(Vendor).filter(Vendor.vendor_name == agency).first()
                if vendor_rec:
                    vendor_cache[agency] = vendor_rec

            if not vendor_rec:
                vendor_rec = Vendor(
                    vendor_name=agency,
                    total_works=1,
                    districts_count=1,
                    states_count=1,
                    total_value=cost,
                    vci_score=0.15,
                    is_suspect=0,
                    high_risk_count=1 if risk_level == "High" else 0,
                    updated_at=datetime.utcnow()
                )
                db.add(vendor_rec)
                vendor_cache[agency] = vendor_rec
            else:
                vendor_rec.total_works = (vendor_rec.total_works or 0) + 1
                vendor_rec.total_value = (vendor_rec.total_value or 0.0) + cost
                if risk_level == "High":
                    vendor_rec.high_risk_count = (vendor_rec.high_risk_count or 0) + 1

            # Ensure FundRelease record exists
            tranche_id = f"TR-EI-{raw_id}"
            fr = db.query(FundRelease).filter(FundRelease.tranche_id == tranche_id).first()
            if not fr:
                fr = FundRelease(
                    tranche_id=tranche_id,
                    project_id=pid,
                    installment_no=1,
                    release_date=comp_date or datetime.utcnow(),
                    disbursed_amount=cost,
                    implementing_agency=agency,
                    created_at=datetime.utcnow()
                )
                db.add(fr)

            # Ensure UtilizationCertificate record exists
            uc_id = f"UC-EI-{raw_id}"
            uc = db.query(UtilizationCertificate).filter(UtilizationCertificate.uc_id == uc_id).first()
            if not uc:
                uc = UtilizationCertificate(
                    uc_id=uc_id,
                    project_id=pid,
                    bill_amount=cost,
                    uc_amount=cost,
                    gap_amount=0.0,
                    gap_pct=0.0,
                    has_mismatch=0,
                    submission_date=comp_date or datetime.utcnow(),
                    created_at=datetime.utcnow()
                )
                db.add(uc)

            # Ensure RiskScoreRecord exists
            rs = db.query(RiskScoreRecord).filter(RiskScoreRecord.project_id == pid).first()
            if not rs:
                rs = RiskScoreRecord(
                    project_id=pid,
                    ml_probability=risk_prob,
                    rule_signal=0.10,
                    composite_risk=risk_score,
                    risk_level=risk_level,
                    rate_inflation_flag=1 if amount_ratio > 1.8 else 0,
                    triggered_rules="Cost Ratio Outlier" if amount_ratio > 1.8 else "Nominal",
                    calculated_at=datetime.utcnow()
                )
                db.add(rs)

            db.flush()
            processed += 1

        db.commit()
        return len(works), processed

    # -------------------------------------------------------------------------
    # Master Harvesting Pipeline
    # -------------------------------------------------------------------------

    def harvest_batch(
        self,
        db: Session,
        sync_mps: bool = True,
        constituencies: Optional[List[str]] = None,
        max_constituencies: int = 5
    ) -> Dict[str, Any]:
        """
        Executes end-to-end live data harvesting session:
          1. Fetches live MP summaries and updates mp_allocations.
          2. Selects target constituencies.
          3. Fetches live completed works and updates projects + relational tables.
          4. Logs session in scrape_logs.
        """
        run_id = f"RUN-EI-{uuid.uuid4().hex[:8].upper()}"
        scrape_id = f"SCRAPE-EI-{uuid.uuid4().hex[:8].upper()}"

        # Initialize ScrapeLog entry
        log_entry = ScrapeLog(
            scrape_id=scrape_id,
            source_name="EmpoweredIndian",
            endpoint_url=f"{self.base_url}{self.MP_SUMMARY_ENDPOINT}",
            status="RUNNING",
            records_fetched=0,
            records_inserted=0,
            created_at=datetime.utcnow()
        )
        db.add(log_entry)
        db.commit()

        total_fetched = 0
        total_inserted = 0
        errors = []

        try:
            # Step 1: MP Allocation Summaries
            mp_count_updated = 0
            mp_count_inserted = 0
            if sync_mps:
                logger.info("Harvesting live MP allocation summaries from Empowered Indian...")
                mp_resp = self.fetch_mp_summaries(page=1, limit=800)
                if mp_resp.get("success", False) or mp_resp.get("data"):
                    mp_data = mp_resp.get("data", [])
                    total_fetched += len(mp_data)
                    mp_count_updated, mp_count_inserted = self.sync_mp_allocations(db, mp_data)
                    total_inserted += (mp_count_updated + mp_count_inserted)
                else:
                    errors.append(f"MP Summary fetch warning: {mp_resp.get('error')}")

            # Step 2: Target Constituencies for Itemized Works
            target_constituencies = []
            if constituencies:
                target_constituencies = constituencies
            else:
                # Pick top constituencies with active completed works from mp_allocations
                top_allocs = db.query(MPAllocation.constituency).filter(
                    MPAllocation.completed_works > 0,
                    MPAllocation.constituency.isnot(None)
                ).limit(max_constituencies).all()
                target_constituencies = [a[0] for a in top_allocs if a[0]]

            # Fallback default constituencies if none found
            if not target_constituencies:
                target_constituencies = ["SHILLONG", "GAUTAM BUDDHA NAGAR", "VARANASI"][:max_constituencies]

            # Step 3: Fetch and synchronize works per constituency
            works_fetched = 0
            works_synced = 0
            constituency_results = {}

            for const in target_constituencies:
                logger.info(f"Harvesting completed works for constituency: {const}")
                works_resp = self.fetch_completed_works(const, page=1, limit=100)
                if works_resp.get("success", False) and works_resp.get("data"):
                    raw_works = works_resp.get("data", [])
                    n_fetched = len(raw_works)
                    works_fetched += n_fetched
                    total_fetched += n_fetched

                    n_synced, n_proc = self.sync_completed_works(db, const, raw_works, run_id)
                    works_synced += n_proc
                    total_inserted += n_proc
                    constituency_results[const] = {
                        "status": "SUCCESS",
                        "fetched": n_fetched,
                        "synced": n_proc
                    }
                else:
                    constituency_results[const] = {
                        "status": "EMPTY_OR_ERROR",
                        "error": works_resp.get("error", "No data returned")
                    }

            # Finalize ScrapeLog
            log_entry.status = "SUCCESS" if not errors else "PARTIAL"
            log_entry.records_fetched = total_fetched
            log_entry.records_inserted = total_inserted
            log_entry.error_message = "; ".join(errors) if errors else None
            db.commit()

            return {
                "success": True,
                "scrape_id": scrape_id,
                "run_id": run_id,
                "source": "EmpoweredIndian API",
                "mp_summaries": {
                    "updated": mp_count_updated,
                    "inserted": mp_count_inserted,
                },
                "itemized_works": {
                    "constituencies_processed": len(target_constituencies),
                    "total_works_fetched": works_fetched,
                    "total_works_synced": works_synced,
                    "details": constituency_results,
                },
                "total_records_fetched": total_fetched,
                "total_records_inserted": total_inserted,
                "status": log_entry.status,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.exception(f"Fatal error during harvesting session {scrape_id}: {e}")
            log_entry.status = "FAILED"
            log_entry.error_message = str(e)
            db.commit()
            return {
                "success": False,
                "scrape_id": scrape_id,
                "error": str(e),
                "records_fetched": total_fetched,
                "records_inserted": total_inserted,
            }
