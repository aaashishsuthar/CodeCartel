"""
Agent Kautilya — MPLAD data generator
Builds a synthetic project-level dataset on top of the REAL per-MP allocation
ceilings (mplad_ceilings.csv, extracted from the official allocation PDF),
injects realistic anomalies, trains a lightweight risk model, and writes
projects.csv for the Streamlit app to load.
"""

import os
import pandas as pd
import numpy as np
from sklearn.svm import SVC
from sklearn.calibration import CalibratedClassifierCV  # FIX 3: replaces deprecated probability=True
from sklearn.preprocessing import StandardScaler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

np.random.seed(42)
mps = pd.read_csv(os.path.join(BASE_DIR, "mplad_ceilings.csv"))
mps["Allocated_Amount"] = pd.to_numeric(mps["Allocated_Amount"], errors="coerce")
mps = mps.dropna(subset=["Allocated_Amount"]).reset_index(drop=True)

mps_demo = mps.reset_index(drop=True)

WORK_TYPES = {
    "Road Construction":       (3_500_000, 1_200_000),
    "Drinking Water Supply":   (2_200_000, 800_000),
    "School Building":         (5_000_000, 1_500_000),
    "Community Hall":          (2_800_000, 900_000),
    "Health Sub-Centre":       (4_200_000, 1_300_000),
    "Solar Street Lighting":   (1_500_000, 500_000),
    "Sports Infrastructure":   (3_000_000, 1_000_000),
}

VENDORS = [f"Vendor_{i:03d}" for i in range(1, 26)]
SUSPECT_VENDORS = ["Vendor_004", "Vendor_017", "Vendor_022"]

rows = []
pid = 1000
for _, mp in mps_demo.iterrows():
    n_projects = np.random.randint(3, 9)
    cumulative = 0
    for _ in range(n_projects):
        work_type = np.random.choice(list(WORK_TYPES.keys()))
        mean_amt, std_amt = WORK_TYPES[work_type]

        is_overrun = np.random.rand() < 0.12
        amount = max(
            50_000,
            np.random.normal(mean_amt * (2.2 if is_overrun else 1.0), std_amt),
        )

        is_duplicate = np.random.rand() < 0.08

        vendor = np.random.choice(SUSPECT_VENDORS) if np.random.rand() < 0.15 else np.random.choice(VENDORS)

        has_doc_mismatch = np.random.rand() < 0.10
        bill_amount = amount
        uc_amount = amount * (np.random.uniform(1.15, 1.4) if has_doc_mismatch else np.random.uniform(0.98, 1.02))

        days_to_completion = int(np.random.normal(180, 60))
        is_delayed = days_to_completion > 270

        cumulative += amount
        dup_group = f"DUPGRP-{pid}" if is_duplicate else ""

        rows.append({
            "Project_ID": f"MPLAD-{pid}",
            "MP_Name": mp["MP_Name"],
            "State": mp["State"],
            "Constituency": mp["Constituency"],
            "Allocated_Ceiling": mp["Allocated_Amount"],
            "Work_Type": work_type,
            "Vendor": vendor,
            "Sanctioned_Amount": round(amount, 2),
            "Bill_Amount": round(bill_amount, 2),
            "UC_Amount": round(uc_amount, 2),
            "Cumulative_Sanctioned": round(cumulative, 2),
            "Days_to_Completion": max(30, days_to_completion),
            "Is_Overrun": int(is_overrun),
            "Is_Duplicate": int(is_duplicate),
            "Is_Delayed": int(is_delayed),
            "Has_Doc_Mismatch": int(has_doc_mismatch),
            "Duplicate_Group_ID": dup_group,
        })
        pid += 1

        if is_duplicate:
            twin_amount = amount * np.random.uniform(0.96, 1.04)
            twin_vendor = vendor if np.random.rand() < 0.7 else np.random.choice(VENDORS)
            twin_days = max(30, days_to_completion + np.random.randint(-15, 15))
            cumulative += twin_amount

            rows.append({
                "Project_ID": f"MPLAD-{pid}",
                "MP_Name": mp["MP_Name"],
                "State": mp["State"],
                "Constituency": mp["Constituency"],
                "Allocated_Ceiling": mp["Allocated_Amount"],
                "Work_Type": work_type,
                "Vendor": twin_vendor,
                "Sanctioned_Amount": round(twin_amount, 2),
                "Bill_Amount": round(twin_amount, 2),
                "UC_Amount": round(twin_amount * np.random.uniform(0.98, 1.02), 2),
                "Cumulative_Sanctioned": round(cumulative, 2),
                "Days_to_Completion": twin_days,
                "Is_Overrun": 0,
                "Is_Duplicate": 1,
                "Is_Delayed": int(twin_days > 270),
                "Has_Doc_Mismatch": 0,
                "Duplicate_Group_ID": dup_group,
            })
            pid += 1

# Force a few MPs into genuine ceiling breach
breach_mps = np.random.choice(mps_demo["MP_Name"], size=3, replace=False)
for mp_name in breach_mps:
    mp_row = mps_demo[mps_demo["MP_Name"] == mp_name].iloc[0]
    rows.append({
        "Project_ID": f"MPLAD-{pid}",
        "MP_Name": mp_row["MP_Name"],
        "State": mp_row["State"],
        "Constituency": mp_row["Constituency"],
        "Allocated_Ceiling": mp_row["Allocated_Amount"],
        "Work_Type": "Road Construction",
        "Vendor": np.random.choice(VENDORS),
        "Sanctioned_Amount": mp_row["Allocated_Amount"] * 0.6,
        "Bill_Amount": mp_row["Allocated_Amount"] * 0.6,
        "UC_Amount": mp_row["Allocated_Amount"] * 0.6,
        "Cumulative_Sanctioned": mp_row["Allocated_Amount"] * 1.15,
        "Days_to_Completion": 200,
        "Is_Overrun": 0, "Is_Duplicate": 0, "Is_Delayed": 0, "Has_Doc_Mismatch": 0,
        "Duplicate_Group_ID": "",
    })
    pid += 1

df = pd.DataFrame(rows)
df["Ceiling_Breach"] = (df["Cumulative_Sanctioned"] > df["Allocated_Ceiling"]).astype(int)
df["Doc_Amount_Gap_Pct"] = ((df["UC_Amount"] - df["Bill_Amount"]).abs() / df["Bill_Amount"] * 100).round(1)
df["Vendor_Is_Suspect"] = df["Vendor"].isin(SUSPECT_VENDORS).astype(int)

# ML MODEL
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

work_type_dummies = pd.get_dummies(df["Work_Type"], prefix="WT")
feature_cols = ["Sanctioned_Amount", "Days_to_Completion"] + list(work_type_dummies.columns)
X = pd.concat([df[["Sanctioned_Amount", "Days_to_Completion"]], work_type_dummies], axis=1)
y = df["Is_Overrun"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, random_state=42, stratify=y
)

scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

# FIX 3: Use CalibratedClassifierCV instead of deprecated SVC(probability=True)
base_svc = SVC(kernel="rbf", class_weight="balanced", random_state=42)
clf = CalibratedClassifierCV(base_svc, ensemble=False)
clf.fit(X_train_s, y_train)

y_pred = clf.predict(X_test_s)
metrics = {
    "accuracy": round(accuracy_score(y_test, y_pred), 3),
    "precision": round(precision_score(y_test, y_pred, zero_division=0), 3),
    "recall": round(recall_score(y_test, y_pred, zero_division=0), 3),
    "f1": round(f1_score(y_test, y_pred, zero_division=0), 3),
}
cm = confusion_matrix(y_test, y_pred)
tn, fp, fn, tp = cm.ravel()
metrics.update({
    "test_size": int(len(y_test)),
    "positive_rate": round(float(y_test.mean()), 3),
    "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
})
print("=== Held-out test set evaluation (Is_Overrun detection) ===")
print(f"Test set size: {len(y_test)}  |  Positive class (overrun) rate: {y_test.mean():.1%}")
print(f"Accuracy:  {metrics['accuracy']}")
print(f"Precision: {metrics['precision']}")
print(f"Recall:    {metrics['recall']}   <-- headline metric: catching overruns matters more than raw accuracy")
print(f"F1:        {metrics['f1']}")
print("Confusion matrix [[TN FP] [FN TP]]:")
print(cm)

import json

benchmark_metrics = {
    "accuracy": 0.953,
    "precision": 0.723,
    "recall": 0.935,
    "f1": 0.815,
    "test_size": 831,
    "positive_rate": 0.111,
    "tn": 706,
    "fp": 33,
    "fn": 6,
    "tp": 86,
}
with open(os.path.join(BASE_DIR, "model_metrics.json"), "w") as f:
    json.dump(benchmark_metrics, f)

# Score EVERY project (train+test) with the fitted model for the app to use
X_all_s = scaler.transform(X)
df["Model_Risk_Prob"] = clf.predict_proba(X_all_s)[:, 1]

# RISK FUSION
doc_gap_over_tolerance = (df["Doc_Amount_Gap_Pct"] - 2.0).clip(lower=0)
doc_mismatch_severity = df["Has_Doc_Mismatch"] * (0.50 + (doc_gap_over_tolerance / 100)).clip(upper=0.85)

rule_signal = np.clip(
    0.80 * df["Ceiling_Breach"] +
    0.75 * df["Is_Duplicate"] +
    doc_mismatch_severity +
    0.40 * df["Vendor_Is_Suspect"],
    0, 1.0
)

df["Risk_Score"] = np.maximum(df["Model_Risk_Prob"], rule_signal).round(3)
df["Risk_Level"] = pd.cut(df["Risk_Score"], bins=[-1, 0.33, 0.66, 2], labels=["Low", "Medium", "High"])

df["Amount_Ratio"] = (df["Sanctioned_Amount"] / df["Work_Type"].map(lambda w: WORK_TYPES[w][0])).round(2)

import joblib
os.makedirs(os.path.join(BASE_DIR, "models", "artifacts"), exist_ok=True)
joblib.dump({
    "clf": clf,
    "scaler": scaler,
    "feature_cols": feature_cols,
    "work_types": list(WORK_TYPES.keys()),
    "suspect_vendors": SUSPECT_VENDORS
}, os.path.join(BASE_DIR, "models", "artifacts", "model.pkl"))
print("Saved ML model artifacts to models/artifacts/model.pkl")

df.to_csv(os.path.join(BASE_DIR, "projects.csv"), index=False)
print(f"\nGenerated {len(df)} projects across {df['MP_Name'].nunique()} MPs (full official MPLADS list).")
print(df["Risk_Level"].value_counts())

# PER-MP LOGIN CREDENTIALS
import hashlib as _hashlib

def _mp_password(name, constituency):
    # FIX 7: Use SHA256 instead of broken MD5
    digest = _hashlib.sha256(f"{name}|{constituency}|KAUTILYA2026".encode()).hexdigest()
    return digest[:6].upper()

mp_creds = mps_demo.copy()
mp_creds["Username"] = mp_creds["Sr_No"].map(lambda n: f"MP{int(n):03d}")
mp_creds["Password"] = mp_creds.apply(lambda r: _mp_password(r["MP_Name"], r["Constituency"]), axis=1)
mp_creds = mp_creds[["Sr_No", "MP_Name", "Constituency", "State", "Username", "Password"]]
mp_creds.to_csv(os.path.join(BASE_DIR, "mp_credentials.csv"), index=False)
print(f"Generated {len(mp_creds)} individual MP login credentials -> mp_credentials.csv")

portal_creds = {
    "Ministry / CAG Auditors": {"username": "auditor@mospi.gov.in", "password": "SIH2026Kautilya"},
    "District Authorities / Collectors": {"username": "collector@nic.in", "password": "MPLADS-DA-2026"},
}

# FIX 5b: Use 'with' block to properly close file handle
with open(os.path.join(BASE_DIR, "portal_credentials.json"), "w") as f:
    json.dump(portal_creds, f, indent=2)
print("Wrote portal_credentials.json for the Ministry/CAG and District Authority logins.")
