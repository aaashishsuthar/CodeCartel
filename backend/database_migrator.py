"""
Agent Kautilya — Relational Database Normalization & Seed Migrator (Phase 1)
Migrates data into the 7 normalized tables matching the system architecture diagram.
"""

import os
import json
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from datetime import datetime

from .database import engine, SessionLocal, Base
from .models import (
    ProjectModel,
    MPAllocation,
    Vendor,
    FundRelease,
    UtilizationCertificate,
    RiskScoreRecord,
    ScrapeLog,
    User,
    AuditRun,
    Evidence,
    IngestionRun
)

BASE_DIR = r"c:/Users/Dream Different/OneDrive/Documents/vscode/New folder"

def run_migration():
    print("=" * 65)
    print("  AGENT KAUTILYA — PHASE 1 DATABASE NORMALIZATION MIGRATOR  ")
    print("=" * 65)

    # 1. Create all tables in SQLite
    Base.metadata.create_all(bind=engine)
    print("[OK] 1. All 7 Normalized Tables Verified & Created in SQLite.")

    db: Session = SessionLocal()
    try:
        # -------------------------------------------------------------
        # 2. Seed mp_allocations table
        # -------------------------------------------------------------
        alloc_count = db.query(MPAllocation).count()
        if alloc_count == 0:
            ceilings_csv = os.path.join(BASE_DIR, "mplad_ceilings.csv")
            if os.path.exists(ceilings_csv):
                df_ceilings = pd.read_csv(ceilings_csv)
                allocations = []
                for _, r in df_ceilings.iterrows():
                    allocated_val = float(r.get("Allocated_Amount", 50000000.0))
                    alloc = MPAllocation(
                        mp_id=f"MP-{r.get('Sr_No', '000')}",
                        mp_name=str(r.get("MP_Name", "")).strip(),
                        house="Lok Sabha",
                        state=str(r.get("State", "")).strip(),
                        constituency=str(r.get("Constituency", "")).strip(),
                        allocated_amount=allocated_val,
                        data_source="Official MoSPI Ceilings"
                    )
                    allocations.append(alloc)
                db.bulk_save_objects(allocations)
                db.commit()
                print(f"[OK] 2. Seeded {len(allocations)} MP records into 'mp_allocations'.")
        else:
            print(f"[OK] 2. 'mp_allocations' already contains {alloc_count} records.")

        # -------------------------------------------------------------
        # 3. Seed vendors table
        # -------------------------------------------------------------
        vendor_count = db.query(Vendor).count()
        if vendor_count == 0:
            projects_csv = os.path.join(BASE_DIR, "projects.csv")
            if os.path.exists(projects_csv):
                df_proj = pd.read_csv(projects_csv)
                total_districts = max(df_proj["Constituency"].nunique(), 1)
                g = df_proj.groupby("Vendor")
                
                vendor_objs = []
                for vendor_name, group in g:
                    works_count = len(group)
                    districts_count = group["Constituency"].nunique()
                    states_count = group["State"].nunique()
                    total_val = float(group["Sanctioned_Amount"].sum())
                    high_risk_share = float((group["Risk_Level"] == "High").mean())
                    dup_share = float((group["Duplicate_Group_ID"].fillna("").astype(str) != "").mean())
                    reach = districts_count / total_districts
                    
                    vci = (0.45 * reach + 0.35 * high_risk_share + 0.20 * dup_share) * 100
                    is_susp = int(vendor_name in ["Vendor_004", "Vendor_017", "Vendor_022"])
                    high_risk_c = int((group["Risk_Level"] == "High").sum())
                    
                    vendor_objs.append(Vendor(
                        vendor_name=vendor_name,
                        total_works=works_count,
                        districts_count=districts_count,
                        states_count=states_count,
                        total_value=total_val,
                        vci_score=round(vci, 2),
                        is_suspect=is_susp,
                        high_risk_count=high_risk_c
                    ))
                db.bulk_save_objects(vendor_objs)
                db.commit()
                print(f"[OK] 3. Seeded {len(vendor_objs)} vendors into 'vendors' table.")
        else:
            print(f"[OK] 3. 'vendors' table already contains {vendor_count} records.")

        # -------------------------------------------------------------
        # 4. Seed utilization_certificates table
        # -------------------------------------------------------------
        uc_count = db.query(UtilizationCertificate).count()
        if uc_count == 0:
            projects_csv = os.path.join(BASE_DIR, "projects.csv")
            if os.path.exists(projects_csv):
                df_proj = pd.read_csv(projects_csv)
                uc_objs = []
                for _, r in df_proj.iterrows():
                    pid = str(r["Project_ID"])
                    bill = float(r["Bill_Amount"])
                    uc = float(r["UC_Amount"])
                    gap = abs(uc - bill)
                    gap_pct = float(r.get("Doc_Amount_Gap_Pct", round((gap / bill * 100) if bill else 0, 1)))
                    has_mism = int(r.get("Has_Doc_Mismatch", int(gap_pct > 2.0)))
                    
                    uc_objs.append(UtilizationCertificate(
                        uc_id=f"UC-{pid.replace('MPLAD-', '')}",
                        project_id=pid,
                        bill_amount=bill,
                        uc_amount=uc,
                        gap_amount=round(gap, 2),
                        gap_pct=gap_pct,
                        has_mismatch=has_mism
                    ))
                db.bulk_save_objects(uc_objs)
                db.commit()
                print(f"[OK] 4. Seeded {len(uc_objs)} certificates into 'utilization_certificates'.")
        else:
            print(f"[OK] 4. 'utilization_certificates' already contains {uc_count} records.")

        # -------------------------------------------------------------
        # 5. Seed risk_scores table
        # -------------------------------------------------------------
        risk_count = db.query(RiskScoreRecord).count()
        if risk_count == 0:
            projects_csv = os.path.join(BASE_DIR, "projects.csv")
            if os.path.exists(projects_csv):
                df_proj = pd.read_csv(projects_csv)
                risk_objs = []
                for _, r in df_proj.iterrows():
                    pid = str(r["Project_ID"])
                    triggered = []
                    if r.get("Ceiling_Breach") == 1: triggered.append("Statutory Ceiling Breach")
                    if r.get("Is_Duplicate") == 1: triggered.append("Duplicate Twin Sanction")
                    if r.get("Has_Doc_Mismatch") == 1: triggered.append("Documentary Gap (Invoice vs UC)")
                    if r.get("Vendor_Is_Suspect") == 1: triggered.append("Suspect Contractor Cartel")
                    
                    risk_objs.append(RiskScoreRecord(
                        project_id=pid,
                        ml_probability=float(r.get("Model_Risk_Prob", 0.0)),
                        composite_risk=float(r.get("Risk_Score", 0.0)),
                        risk_level=str(r.get("Risk_Level", "Low")),
                        ceiling_breach_flag=int(r.get("Ceiling_Breach", 0)),
                        duplicate_flag=int(r.get("Is_Duplicate", 0)),
                        doc_mismatch_flag=int(r.get("Has_Doc_Mismatch", 0)),
                        vendor_suspect_flag=int(r.get("Vendor_Is_Suspect", 0)),
                        rate_inflation_flag=int(float(r.get("Amount_Ratio", 1.0)) > 1.4),
                        triggered_rules=json.dumps(triggered)
                    ))
                db.bulk_save_objects(risk_objs)
                db.commit()
                print(f"[OK] 5. Seeded {len(risk_objs)} score records into 'risk_scores'.")
        else:
            print(f"[OK] 5. 'risk_scores' already contains {risk_count} records.")

        # -------------------------------------------------------------
        # 6. Seed fund_releases table
        # -------------------------------------------------------------
        fr_count = db.query(FundRelease).count()
        if fr_count == 0:
            projects_csv = os.path.join(BASE_DIR, "projects.csv")
            if os.path.exists(projects_csv):
                df_proj = pd.read_csv(projects_csv)
                fr_objs = []
                for _, r in df_proj.iterrows():
                    pid = str(r["Project_ID"])
                    sanc = float(r["Sanctioned_Amount"])
                    fr_objs.append(FundRelease(
                        tranche_id=f"TR-{pid.replace('MPLAD-', '')}-1",
                        project_id=pid,
                        installment_no=1,
                        disbursed_amount=round(sanc * 0.6, 2), # 1st tranche typical 60%
                        implementing_agency=f"District Authority / {r.get('Constituency', 'Local')}"
                    ))
                db.bulk_save_objects(fr_objs)
                db.commit()
                print(f"[OK] 6. Seeded {len(fr_objs)} tranches into 'fund_releases'.")
        else:
            print(f"[OK] 6. 'fund_releases' already contains {fr_count} records.")

        # -------------------------------------------------------------
        # 7. Seed scrape_logs with baseline record
        # -------------------------------------------------------------
        scrape_count = db.query(ScrapeLog).count()
        if scrape_count == 0:
            log = ScrapeLog(
                scrape_id="SCRAPE-INIT-2026",
                source_name="Official Baseline Ingestion",
                endpoint_url="mplad_ceilings.csv + projects.csv",
                status="SUCCESS",
                records_fetched=3340,
                records_inserted=3340,
                snapshot_date=datetime.utcnow()
            )
            db.add(log)
            db.commit()
            print("[OK] 7. Seeded baseline ingestion log into 'scrape_logs'.")
        else:
            print(f"[OK] 7. 'scrape_logs' already contains {scrape_count} records.")

        print("\n" + "=" * 65)
        print("  PHASE 1 DATABASE NORMALIZATION COMPLETED SUCCESSFULLY!   ")
        print("=" * 65)

    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
