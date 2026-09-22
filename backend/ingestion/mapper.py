def map_csv_to_project_dict(row: dict, run_id: str):
    def safe_float(val):
        try: return float(val) if val else None
        except: return None
    def safe_int(val):
        try: return int(float(val)) if val else None
        except: return None

    return {
        "project_id": row.get("Project_ID"),
        "mp_name": row.get("MP_Name"),
        "state": row.get("State"),
        "constituency": row.get("Constituency"),
        "work_type": row.get("Work_Type"),
        "vendor": row.get("Vendor"),
        "allocated_ceiling": safe_float(row.get("Allocated_Ceiling")),
        "sanctioned_amount": safe_float(row.get("Sanctioned_Amount")),
        "bill_amount": safe_float(row.get("Bill_Amount")),
        "uc_amount": safe_float(row.get("UC_Amount")),
        "cumulative_sanctioned": safe_float(row.get("Cumulative_Sanctioned")),
        "days_to_completion": safe_int(row.get("Days_to_Completion")),
        
        "is_overrun": safe_int(row.get("Is_Overrun")),
        "is_duplicate": safe_int(row.get("Is_Duplicate")),
        "is_delayed": safe_int(row.get("Is_Delayed")),
        "has_doc_mismatch": safe_int(row.get("Has_Doc_Mismatch")),
        "duplicate_group_id": row.get("Duplicate_Group_ID"),
        "ceiling_breach": safe_int(row.get("Ceiling_Breach")),
        "vendor_is_suspect": safe_int(row.get("Vendor_Is_Suspect")),
        
        "model_risk_prob": safe_float(row.get("Model_Risk_Prob")),
        "risk_score": safe_float(row.get("Risk_Score")),
        "risk_level": row.get("Risk_Level"),
        
        "doc_amount_gap_pct": safe_float(row.get("Doc_Amount_Gap_Pct")),
        "amount_ratio": safe_float(row.get("Amount_Ratio")),
        
        "data_source": "projects.csv",
        "run_id": run_id
    }
