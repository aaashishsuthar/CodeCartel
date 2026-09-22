"""
Agent Kautilya — Real-Time Anomaly & Fraud Interceptor Service
Evaluates newly ingested government works against the Calibrated SVM and Statutory Rule Engine,
detects duplicate proposals, rate inflations, and ceiling breaches,
updates relational risk tables, and automatically initiates audit investigation runs for high-risk sanctions.
"""

import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from sqlalchemy.orm import Session

from ..models.project import ProjectModel
from ..models.risk_score import RiskScoreRecord
from ..models.audit import AuditRun, Evidence
from .risk_fusion import calculate_risk
from ..rules.engine import apply_rules
from ..ml.predictor import predictor

logger = logging.getLogger("agent_kautilya.interceptor")


class LiveAnomalyInterceptor:
    """
    Real-Time Forensic Interceptor for automated fraud and anomaly surveillance.
    """

    @classmethod
    def intercept_project(
        cls,
        project: ProjectModel,
        db: Session,
        auto_audit_high_risk: bool = True
    ) -> Dict[str, Any]:
        """
        Evaluates a single project record through the full hybrid ML + Rule intelligence pipeline.
        Synchronizes risk_scores, flags anomalies, and creates audit investigations when needed.
        """
        # 1. Hybrid ML + Rules Risk Calculation
        risk_data = calculate_risk(project)
        ml_prob = risk_data["ml_probability"]
        rule_signal = risk_data["rule_signal"]
        composite_score = risk_data["risk_score"]
        risk_level = risk_data["risk_level"]
        triggered_rules = list(risk_data["rules"].get("triggered_rules", []))

        # 2. Rate Inflation & Benchmark Evaluation
        amount_ratio = getattr(project, "amount_ratio", 1.0) or 1.0
        if amount_ratio > 1.8 and "Cost Ratio Outlier" not in triggered_rules:
            triggered_rules.append("Cost Ratio Outlier")
            rule_signal = max(rule_signal, min(0.85, 0.30 + (amount_ratio - 1.8) * 0.4))
            composite_score = round(max(composite_score, rule_signal), 3)
            risk_level = "High" if composite_score >= 0.66 else ("Medium" if composite_score >= 0.33 else "Low")

        # 3. Duplicate Work Detection
        # Check if identical/similar description exists in same district
        desc = (project.description or "").strip()
        dist = project.district or project.constituency
        is_dup = getattr(project, "is_duplicate", 0) or 0

        if desc and len(desc) > 15 and dist:
            dup_candidates = db.query(ProjectModel).filter(
                ProjectModel.project_id != project.project_id,
                ProjectModel.district == dist,
                ProjectModel.description.ilike(desc)
            ).first()
            if dup_candidates and not is_dup:
                is_dup = 1
                if "Duplicate Sanction" not in triggered_rules:
                    triggered_rules.append("Duplicate Sanction")
                rule_signal = max(rule_signal, 0.75)
                composite_score = round(max(composite_score, rule_signal), 3)
                risk_level = "High" if composite_score >= 0.66 else "Medium"

        # 4. Update ProjectModel
        project.model_risk_prob = ml_prob
        project.risk_score = composite_score
        project.risk_level = risk_level
        project.is_duplicate = is_dup
        if ml_prob > 0.50:
            project.is_overrun = 1

        # 5. Synchronize risk_scores Table
        rs_rec = db.query(RiskScoreRecord).filter(RiskScoreRecord.project_id == project.project_id).first()
        rule_str = ", ".join(triggered_rules) if triggered_rules else "Nominal"

        if not rs_rec:
            rs_rec = RiskScoreRecord(
                project_id=project.project_id,
                ml_probability=ml_prob,
                rule_signal=rule_signal,
                composite_risk=composite_score,
                risk_level=risk_level,
                rate_inflation_flag=1 if amount_ratio > 1.8 else 0,
                duplicate_flag=is_dup,
                triggered_rules=rule_str,
                calculated_at=datetime.utcnow()
            )
            db.add(rs_rec)
        else:
            rs_rec.ml_probability = ml_prob
            rs_rec.rule_signal = rule_signal
            rs_rec.composite_risk = composite_score
            rs_rec.risk_level = risk_level
            rs_rec.rate_inflation_flag = 1 if amount_ratio > 1.8 else 0
            rs_rec.duplicate_flag = is_dup
            rs_rec.triggered_rules = rule_str
            rs_rec.calculated_at = datetime.utcnow()

        # 6. Automatic Audit Investigation for High-Risk Sanctions
        audit_run_id = None
        evidence_id = None
        if risk_level == "High" and auto_audit_high_risk:
            # Check if active audit run exists
            existing_audit = db.query(AuditRun).filter(AuditRun.project_id == project.project_id).first()
            if not existing_audit:
                audit_run_id = f"AUDIT-AUTO-{uuid.uuid4().hex[:6].upper()}"
                new_audit = AuditRun(
                    audit_id=audit_run_id,
                    project_id=project.project_id,
                    run_date=datetime.utcnow(),
                    ml_probability=ml_prob,
                    rule_signal=rule_signal,
                    final_risk_score=composite_score,
                    risk_level=risk_level,
                    triggered_rules=triggered_rules
                )
                db.add(new_audit)

                evidence_id = f"EVID-AUTO-{uuid.uuid4().hex[:6].upper()}"
                new_evidence = Evidence(
                    evidence_id=evidence_id,
                    project_id=project.project_id,
                    audit_id=audit_run_id,
                    evidence_type="REALTIME_INTERCEPT",
                    description=f"Autonomous Interceptor flagged sanction {project.project_id} with risk score {composite_score} ({risk_level}). Anomalies: {rule_str}",
                    source="Agent Kautilya Real-Time Anomaly Interceptor",
                    created_at=datetime.utcnow()
                )
                db.add(new_evidence)

        return {
            "project_id": project.project_id,
            "mp_name": project.mp_name,
            "district": dist,
            "sanctioned_amount": project.sanctioned_amount,
            "ml_probability": ml_prob,
            "rule_signal": rule_signal,
            "composite_risk_score": composite_score,
            "risk_level": risk_level,
            "triggered_rules": triggered_rules,
            "audit_initiated": audit_run_id is not None,
            "audit_id": audit_run_id,
            "evidence_id": evidence_id
        }

    @classmethod
    def intercept_batch(
        cls,
        db: Session,
        filter_source: Optional[str] = "EmpoweredIndian API",
        limit: int = 500,
        auto_audit: bool = True
    ) -> Dict[str, Any]:
        """
        Scans and intercepts projects matching filter_source or all newly ingested works.
        """
        query = db.query(ProjectModel)
        if filter_source:
            query = query.filter(ProjectModel.data_source == filter_source)

        projects = query.limit(limit).all()

        high_count = 0
        med_count = 0
        low_count = 0
        audits_count = 0
        evidence_count = 0
        verdicts = []

        for p in projects:
            res = cls.intercept_project(p, db, auto_audit_high_risk=auto_audit)
            verdicts.append(res)
            if res["risk_level"] == "High":
                high_count += 1
            elif res["risk_level"] == "Medium":
                med_count += 1
            else:
                low_count += 1

            if res["audit_initiated"]:
                audits_count += 1
                evidence_count += 1

        db.commit()

        return {
            "total_evaluated": len(projects),
            "high_risk_flagged": high_count,
            "medium_risk_flagged": med_count,
            "low_risk_flagged": low_count,
            "audits_initiated": audits_count,
            "evidence_markers_created": evidence_count,
            "sample_verdicts": verdicts[:5],
            "timestamp": datetime.utcnow().isoformat()
        }

    @classmethod
    def simulate_proposal(
        cls,
        work_type: str,
        sanctioned_amount: float,
        days_to_completion: int = 180,
        vendor: str = "Standard Executing Agency",
        allocated_ceiling: float = 50000000.0,
        cumulative_sanctioned: float = 0.0,
        description: Optional[str] = None,
        district: Optional[str] = None
    ) -> Dict[str, Any]:
        class MockProject:
            def __init__(self):
                self.sanctioned_amount = sanctioned_amount
                self.days_to_completion = days_to_completion
                self.work_type = work_type
                self.vendor = vendor
                self.allocated_ceiling = allocated_ceiling
                self.cumulative_sanctioned = cumulative_sanctioned + sanctioned_amount
                self.bill_amount = sanctioned_amount
                self.uc_amount = sanctioned_amount
                self.is_duplicate = 0
                self.has_doc_mismatch = 0
                self.description = description
                self.district = district
                self.constituency = district

        mock = MockProject()
        risk_data = calculate_risk(mock)

        from ..ingestion.connectors.empowered_indian import BENCHMARK_COSTS
        benchmark = BENCHMARK_COSTS.get(work_type, 2_000_000)
        ratio = round(sanctioned_amount / benchmark, 2) if benchmark > 0 else 1.0

        rules = list(risk_data["rules"].get("triggered_rules", []))
        if ratio > 1.8:
            rules.append("Cost Ratio Outlier")

        from ..rules.compliance import check_mospi_prohibited_work, evaluate_execution_horizon
        prohibited_check = check_mospi_prohibited_work(description or "", work_type)
        horizon_check = evaluate_execution_horizon(days_to_completion)

        is_prohibited = prohibited_check["is_prohibited"]
        is_horizon_breach = horizon_check["horizon_breach"]
        if is_horizon_breach:
            rules.append(f"Statutory Horizon Breach (>540 Days): {days_to_completion} days proposed")

        if is_prohibited:
            rules.append(f"Prohibited Work: {prohibited_check['category']}")
            risk_score = 1.0
            risk_level = "High"
            verdict = f"STATUTORY REJECT — {prohibited_check['reason']}"
        elif is_horizon_breach:
            risk_score = max(risk_data["risk_score"], 0.85)
            risk_level = "High"
            verdict = f"STATUTORY REJECT — Proposed execution timeline ({days_to_completion} days) breaches MoSPI Para 4.6 18-month statutory horizon."
        else:
            risk_score = risk_data["risk_score"]
            risk_level = risk_data["risk_level"]
            verdict = "REJECT / AUDIT REQUIRED" if risk_level == "High" else (
                "CONDITIONAL APPROVAL" if risk_level == "Medium" else "CLEAR TO SANCTION"
            )

        return {
            "work_type": work_type,
            "sanctioned_amount": sanctioned_amount,
            "cost_benchmark": benchmark,
            "cost_ratio": ratio,
            "ml_overrun_probability": risk_data["ml_probability"],
            "rule_signal": risk_data["rule_signal"],
            "composite_risk_score": risk_score,
            "risk_level": risk_level,
            "triggered_rules": rules,
            "is_prohibited": is_prohibited,
            "prohibited_details": prohibited_check if is_prohibited else None,
            "is_horizon_breach": is_horizon_breach,
            "horizon_details": horizon_check,
            "verdict": verdict,
        }

    @classmethod
    def get_recent_anomalies(cls, limit: int = 50, db: Optional[Session] = None) -> List[Dict[str, Any]]:
        from ..database import SessionLocal
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        try:
            from sqlalchemy import desc
            high_projects = db.query(ProjectModel).filter(
                ProjectModel.data_source == "EmpoweredIndian API",
                ProjectModel.risk_level == "High"
            ).order_by(desc(ProjectModel.risk_score)).limit(limit).all()

            items = []
            for p in high_projects:
                rs = db.query(RiskScoreRecord).filter(RiskScoreRecord.project_id == p.project_id).first()
                audit = db.query(AuditRun).filter(AuditRun.project_id == p.project_id).first()
                items.append({
                    "project_id": p.project_id,
                    "mp_name": p.mp_name,
                    "district": p.district,
                    "work_type": p.work_type,
                    "sanctioned_amount": p.sanctioned_amount,
                    "risk_score": rs.composite_risk if rs else p.risk_score,
                    "risk_level": rs.risk_level if rs else p.risk_level,
                    "audit_id": audit.audit_id if audit else None,
                    "audit_status": audit.status if audit else "NOT_INITIATED",
                    "flagged_at": rs.calculated_at.isoformat() if rs and rs.calculated_at else (p.created_at.isoformat() if getattr(p, "created_at", None) else datetime.utcnow().isoformat())
                })
            return items
        finally:
            if should_close:
                db.close()


live_interceptor = LiveAnomalyInterceptor()

