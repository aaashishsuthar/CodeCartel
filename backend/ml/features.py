import pandas as pd

def extract_features(project, feature_cols, work_types):
    if not isinstance(project, dict):
        p_dict = {
            "Sanctioned_Amount": getattr(project, "sanctioned_amount", 0.0) or 0.0,
            "Days_to_Completion": getattr(project, "days_to_completion", 180) or 180,
            "Work_Type": getattr(project, "work_type", "")
        }
    else:
        p_dict = project

    data = {
        "Sanctioned_Amount": p_dict.get("Sanctioned_Amount", 0.0),
        "Days_to_Completion": p_dict.get("Days_to_Completion", 180)
    }
    
    wt = p_dict.get("Work_Type", "")
    for w in work_types:
        data[f"WT_{w}"] = 1 if wt == w else 0
        
    df = pd.DataFrame([data])
    for col in feature_cols:
        if col not in df.columns:
            df[col] = 0
            
    return df[feature_cols]
