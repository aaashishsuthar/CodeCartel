# Agent Kautilya — Autonomous Forensic Intelligence Suite for MPLADS

> **Tekathon 5.0** — Chandigarh University's internal qualifier for **Smart India Hackathon 2026**
> **Problem Statement**: SIH26102 (Ministry of Statistics & Programme Implementation — MoSPI)
> **Team**: Code Cartel

Built by six students who'd never entered a hackathon before, Agent Kautilya went from a fraud-detection notebook to a full multi-tier audit platform in under a week of building through the night — and took our team straight to the Grand Finale.

---

## What This Is

**Agent Kautilya** is an AI-powered vigilance, anomaly-detection, and forensic-audit platform for the Members of Parliament Local Area Development Scheme (MPLADS). It turns raw project and financial records from constituencies across India into real-time, actionable audit intelligence — before public money is lost, not after.

### Key Capabilities
- **Four Governance Tiers** — dedicated consoles for Ministry/CAG Auditors, State Nodal Authorities (SNA), District Authorities/Collectors, and Members of Parliament.
- **Ghost Asset Detection** — autonomously flags projects where funds are prematurely disbursed (>70%) despite lagging physical progress (≤35%).
- **MoSPI 2023 Statutory Compliance** — automated Annexure-II negative-list scanner and Para 2.5 SC (15%) / ST (7.5%) quota-deficit tracking.
- **Early Warning Delay Radar** — monitors the statutory 18-month (540-day) execution horizon (Para 4.6) and forecasts fiscal year-end fund-lapse risk.
- **Pre-Sanction Interceptor** — blocks non-compliant or high-risk proposals in real time, before administrative sanction is granted.
- **One-Click Audit Memos** — generates court-admissible PDF evidence reports.

### Tech Stack
- **Frontend**: Streamlit (multi-tier dashboard, `streamlit-agraph` for the vendor network graph)
- **Backend**: FastAPI (REST API, rule engines, ingestion pipelines)
- **ML**: Scikit-learn (class-weighted SVM, calibrated) for risk fusion
- **Data**: SQLAlchemy + SQLite, `pandas` / `numpy` for processing
- **Reporting**: `fpdf2` (PDF audit memos), `python-pptx` (deck generation)
- **Scheduling**: APScheduler for the autonomous monitoring agent

---

## Quick Start

### 1. Prerequisites
- Python 3.10 – 3.13
- Git (optional, for cloning)

### 2. Clone & Install
```bash
git clone https://github.com/aaashishsuthar/CodeCartel.git
cd CodeCartel
pip install -r requirements.txt
```

### 3. (Optional) Refresh Live Government Data
Re-fetches live parliamentary datasets from Open City, MoSPI eSAKSHI, and Empowered Indian, with SHA-256 provenance hashing:
```bash
python fetch_live_data.py
```
This regenerates `data/provenance.json` and `data/clean/mp_risk_clean.csv` (1,675 real MP risk indicators).

### 4. Launch
```bash
python launch.py
```
This single command will:
1. Verify/generate the initial datasets and ML model (`projects.csv`, `models/artifacts/model.pkl`).
2. Start the FastAPI backend at `http://127.0.0.1:8000`.
3. Launch the Streamlit dashboard at `http://localhost:8501`.
4. Open Agent Kautilya in your default browser automatically.

---

## New Here? How to See the Project in Action

If you're landed here from LinkedIn and want a walkthrough rather than a code read — here's the fastest path:

1. **Run the Quick Start steps above** (takes ~2 minutes; `launch.py` does the rest for you).
2. Once the browser opens on `localhost:8501`, you'll land on a **role selector** — pick any of the four tiers below.
3. Log in using one of the demo credentials in the table below.
4. Explore — each tier has a different lens on the same underlying data: national/state oversight (Auditor, SNA), on-ground execution (District), or an individual MP's own constituency view.
5. No time to run it locally? The `presentation/` folder has the full pitch deck (`Agent_Kautilya_SIH2026_Perfect_Presentation.pptx`) and jury guide, which walk through every screen without needing to install anything.

### Demo Credentials

| Role | Login | Passkey | What You'll See |
| :--- | :--- | :--- | :--- |
| **Ministry / CAG Auditors** | `auditor@mospi.gov.in` | `SIH2026Kautilya` | Full unmasked national forensic surveillance, risk radar & CAG memo export |
| **State Nodal Authorities (SNA)** | `sna@state.gov.in` | `MPLADS-SNA-2026` | State-level drilldown, inter-district leaderboard & delay alerts |
| **District Authorities / Collectors** | Select any district (e.g. *Varanasi*) | `MPLADS-DA-2026` | Execution console, milestone sign-off & inspection queue |
| **Members of Parliament** | `MP001` (or any of the 543 MP usernames) | `CF766A` *(unique per MP)* | Constituency view, statutory quotas & proposal recommendations |

> **Note on MP logins**: every one of the 543 MPs has a real, unique auto-generated password (not a shared demo code) — `MP001` / `CF766A` above is just one working example. The login screen has a built-in **"Browse the MP credentials directory"** search if you want to look up a specific MP or state.

---

## Repository Structure
```
├── app.py                     # Streamlit multi-tier frontend application
├── launch.py                  # Unified launcher (FastAPI + Streamlit)
├── data_gen.py                # Synthetic dataset & ML model trainer
├── fetch_live_data.py         # Live government data harvester + provenance hashing
├── run_tests.py               # Unified verification test suite runner
├── backend/                   # FastAPI backend
│   ├── api/                   # REST endpoints (projects, audits, interceptor, etc.)
│   ├── rules/                 # MoSPI compliance & delay horizon rule engines
│   ├── ingestion/             # MoSPI eSAKSHI & Empowered Indian harvesters
│   ├── ml/                    # Feature extractors & model predictors
│   ├── models/                # SQLAlchemy relational database models
│   └── services/              # Audit, auth, autonomous agent, reporting services
├── client/                    # Python API client SDK for Agent Kautilya
├── models/artifacts/          # Trained calibrated SVM model artifacts
├── presentation/               # Official SIH 2026 presentation deck & jury guide
│   ├── Agent_Kautilya_SIH2026_Perfect_Presentation.pptx
│   └── JURY_PRESENTATION_GUIDE.md
├── tests/                     # Automated test suites (Steps 1–6, Parity, Phases 1–8)
├── projects.csv               # Ground-truth project-level baseline dataset
├── mplad_ceilings.csv         # Real parliamentary allocation ceilings
├── mp_credentials.csv         # 543 MP demo credentials (unique per MP)
├── kautilya.db                # SQLite normalized database
├── portal_credentials.json    # Portal access credentials
└── requirements.txt           # Python package dependencies
```

---

## Verification & Regression Test Suites
```bash
# Run the 6 primary verification suites (Steps 1–6):
python run_tests.py

# Run all 14 suites — primary + deep phase tests:
python run_tests.py --all

# Or run any suite individually:
python tests/test_step1_sna.py                    # State Nodal Authority role & dashboard
python tests/test_step2_ghost_asset.py             # Physical vs financial divergence engine
python tests/test_step3_compliance.py               # MoSPI Annexure-II & SC/ST quotas
python tests/test_step4_early_warning.py            # 18-month delay radar & lapse forecasting
python tests/parity_check.py                        # Mathematical & ML benchmark parity
python tests/test_autonomous_and_escalation.py      # Autonomous vigilance & authority escalation
```

---

## Team Code Cartel
Built for Tekathon 5.0 (SIH 2026 internal qualifier, Chandigarh University) — our first hackathon, and our first Grand Finale.

*Developed with pride by Team Code Cartel.*
