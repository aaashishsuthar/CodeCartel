# Agent Kautilya — Autonomous Forensic Intelligence Suite for MPLAD Scheme

> **Smart India Hackathon (SIH 2026)**  
> **Problem Statement ID**: SIH26102 (Ministry of Statistics and Programme Implementation - MoSPI)  
> **Team Name**: Code Cartel  

---

## 🏛️ Project Overview
**Agent Kautilya** is an AI-powered vigilance, anomaly detection, and forensic audit platform for the Members of Parliament Local Area Development Scheme (MPLADS). It transforms raw project and financial records across 543 Lok Sabha and 77 Rajya Sabha constituencies into actionable, real-time audit intelligence.

### Key Capabilities
- **Four Administrative Governance Tiers**: Dedicated consoles for Ministry/Central CAG Auditors, State Nodal Authorities (SNA), District Authorities / Collectors, and Members of Parliament (LS/RS).
- **Physical vs. Financial Progress Divergence**: Autonomous detection of "Ghost Assets" where funds are prematurely disbursed (>70%) despite lagging physical milestones (<=35%).
- **MoSPI 2023 Statutory Compliance**: Automated Annexure-II negative list scanner and Para 2.5 mandatory SC (15%) & ST (7.5%) quota deficit tracking.
- **Early Warning Delay Radar**: Statutory 18-month (540 calendar day) execution horizon monitoring (MoSPI Para 4.6) and fiscal year-end fund lapse risk forecasting.
- **Real-Time Pre-Sanction Interceptor**: Gateway blocking non-compliant or high-risk proposals before administrative sanction.
- **Automated Evidence & CAG Audit Memos**: One-click generation of court-admissible PDF audit memos.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10 to 3.13 installed
- Git (optional)

### 2. Installation
Open your terminal inside this project folder and run:
```powershell
pip install -r requirements.txt
```

### 3. (Optional) Refresh Real Government Data & Cryptographic Provenance
To re-fetch the live parliamentary datasets from Open City, MoSPI eSAKSHI, and Empowered Indian:
```powershell
python fetch_live_data.py
```
This generates `data/provenance.json` (SHA-256 audit hashes) and `data/clean/mp_risk_clean.csv` (1,675 real MP risk indicators).

### 4. Launch Agent Kautilya
Run the unified launcher:
```powershell
python launch.py
```
This will:
1. Verify initial datasets and ML models (`projects.csv`, `models/artifacts/model.pkl`).
2. Start the FastAPI backend engine on `http://127.0.0.1:8000`.
3. Launch the Streamlit dashboard on `http://localhost:8501`.
4. Automatically open Agent Kautilya in your default browser.

---

## 🔐 Portal Demo Credentials

| Role | Username / Identifier | Password | Access Level |
| :--- | :--- | :--- | :--- |
| **Ministry / CAG Auditors** | `auditor@mospi.gov.in` | `SIH2026Kautilya` | Full unmasked forensic surveillance, national radar & CAG memo export |
| **State Nodal Authorities (SNA)** | `sna@state.gov.in` | `MPLADS-SNA-2026` | State-level slicing, inter-district leaderboard & delay alerts |
| **District Authorities / Collectors** | Any District (e.g. *Varanasi*) | *Auto-selected* | Execution console, milestone sign-off & inspection queue |
| **Members of Parliament** | MP Constituency Selection (e.g. *MP001*) | `DEMO2026` | Constituency view, statutory quotas & proposal recommendation |

---

## 🧪 Verification & Regression Test Suites
Agent Kautilya includes comprehensive automated test suites covering all modules:

```powershell
# Run primary verification suites (Steps 1–5):
python run_tests.py

# Run all 13 verification and deep phase suites:
python run_tests.py --all

# Run individual test suites directly:
python tests/test_step1_sna.py           # State Nodal Authority role & dashboard
python tests/test_step2_ghost_asset.py   # Physical vs financial divergence engine
python tests/test_step3_compliance.py    # MoSPI Annexure-II & SC/ST quotas
python tests/test_step4_early_warning.py # 18-month delay radar & lapse forecasting
python tests/parity_check.py             # 100% mathematical & ML benchmark parity
```

---

## 📁 Repository Structure
```
├── app.py                     # Streamlit multi-tier frontend application
├── launch.py                  # Direct unified launcher (FastAPI + Streamlit)
├── data_gen.py                # Synthetic dataset & ML model trainer
├── run_tests.py               # Unified verification test suite runner
├── backend/                   # FastAPI backend services, rules & API routes
│   ├── api/                   # REST endpoints (projects, audits, interceptor, etc.)
│   ├── rules/                 # MoSPI compliance & delay horizon rule engines
│   ├── ingestion/             # MoSPI eSAKSHI & EmpoweredIndian harvesters
│   ├── ml/                    # Feature extractors & model predictors
│   └── models/                # SQLAlchemy relational database models
├── client/                    # Python API client SDK for Agent Kautilya
├── models/artifacts/          # Trained Calibrated SVM model artifacts
├── presentation/              # Official SIH 2026 presentation deck & jury guide
│   ├── Agent_Kautilya_SIH2026_Perfect_Presentation.pptx
│   └── JURY_PRESENTATION_GUIDE.md
├── tests/                     # Automated test suites (Steps 1–4, Parity, Phases 1–8)
├── projects.csv               # Ground-truth project-level baseline dataset
├── mplad_ceilings.csv         # Real parliamentary allocation ceilings
├── mp_credentials.csv         # 540 Lok Sabha & Rajya Sabha credentials
├── kautilya.db                # SQLite normalized database
├── portal_credentials.json    # Portal access credentials
└── requirements.txt           # Python package dependencies
```

---
*Developed with pride by **Team Code Cartel** for **Smart India Hackathon 2026**.*
