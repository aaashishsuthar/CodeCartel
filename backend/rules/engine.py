import joblib
import os

BASE_DIR = r"c:/Users/Dream Different/OneDrive/Documents/vscode/New folder"
MODEL_PATH = os.path.join(BASE_DIR, "models", "artifacts", "model.pkl")

def get_suspect_vendors():
    if os.path.exists(MODEL_PATH):
        artifacts = joblib.load(MODEL_PATH)
        return artifacts.get("suspect_vendors", [])
    return []

def apply_rules(project):
    """
    Applies deterministic rules to the project data.
    """
    sanc = getattr(project, "sanctioned_amount", 0.0) or 0.0
    ceil = getattr(project, "allocated_ceiling", float('inf')) or float('inf')
    bill = getattr(project, "bill_amount", 0.0) or 0.0
    uc = getattr(project, "uc_amount", 0.0) or 0.0
    cum = getattr(project, "cumulative_sanctioned", 0.0) or 0.0
    vendor = getattr(project, "vendor", "") or ""
    
    ceiling_breach = 1 if cum > ceil else 0
    is_duplicate = getattr(project, "is_duplicate", 0) or 0
    has_doc_mismatch = getattr(project, "has_doc_mismatch", 0) or 0
    
    doc_amount_gap_pct = 0.0
    if bill > 0:
        doc_amount_gap_pct = abs(uc - bill) / bill * 100
        
    doc_gap_over_tolerance = max(0, doc_amount_gap_pct - 2.0)
    doc_mismatch_severity = has_doc_mismatch * min(0.85, 0.50 + (doc_gap_over_tolerance / 100.0))
    
    suspect_vendors = get_suspect_vendors()
    vendor_is_suspect = 1 if vendor in suspect_vendors else 0
    
    rule_signal = min(1.0, max(0.0, 
        0.80 * ceiling_breach +
        0.75 * is_duplicate +
        doc_mismatch_severity +
        0.40 * vendor_is_suspect
    ))
    
    return {
        "ceiling_breach": ceiling_breach,
        "is_duplicate": is_duplicate,
        "doc_mismatch_severity": doc_mismatch_severity,
        "vendor_is_suspect": vendor_is_suspect,
        "rule_signal": rule_signal,
        "triggered_rules": [
            k for k, v in [
                ("Ceiling Breach", ceiling_breach), 
                ("Duplicate", is_duplicate), 
                ("Document Mismatch", has_doc_mismatch), 
                ("Suspect Vendor", vendor_is_suspect)
            ] if v > 0
        ]
    }
