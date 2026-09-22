# AGENT KAUTILYA — JURY PRESENTATION & DEFENSE GUIDE
## SIH 2026 | Problem Statement 26102 | Team CODE CARTEL

---

### Part 1: How We Addressed the Jury's Feedback

#### 1. Jury's Concern: *"The data was synthetic/integrated in the prototype. How does this system handle real data?"*
> **Your Answer**:
> *"Respected Jury, in our initial prototype, the project data was generated to demonstrate forensic capability on top of the real 540 MP ceilings. In response to your feedback, we have completely decoupled our architecture and engineered an **Enterprise Data Ingestion & Quality Engine** (`backend/ingestion/`).*
> 
> *Our system now treats data in four distinct stages:*
> 1. ***Raw Ingestion***: *Accepts real CSV or Excel exports from MoSPI, e-SAKSHI, or State portals.*
> 2. ***Data Quality & Validation Engine***: *Validates mandatory fields, checks for negative expenditures, detects unlinked sanctions, and generates an immutable **Data Quality Report** with exact warning counts.*
> 3. ***Schema Normalization***: *Maps heterogeneous government schemas into our transactional SQLite database, capturing data provenance, source record IDs, and timestamps.*
> 4. ***Model & Rule Decoupling***: *Our ML models and statutory rules now run strictly on stored relational tables without retraining on server startup.*
> 
> *As real MoSPI data becomes accessible via API or CSV dump, the system ingests it with zero architectural refactoring.*

---

#### 2. Jury's Concern: *"Don't run everything inside Streamlit. Build a separate, standalone backend."*
> **Your Answer**:
> *"We have built our own dedicated **FastAPI REST Backend Service** operating on Port 8000, completely separated from the Streamlit frontend on Port 8501.*
> 
> *Key Technical Highlights of Our Backend:*
> - ***FastAPI & SQLite Core***: *A lightweight, lightning-fast asynchronous REST API backed by SQLAlchemy.*
> - ***Enterprise Security***: *Standard OAuth2 with JSON Web Tokens (JWT). We eliminated all plaintext password storage, replacing it with cryptographic **bcrypt** one-way hashes across all 545 accounts.*
> - ***Constituency-Level Data Isolation (RBAC)***: *An MP logging into our system cannot access sanctions from other constituencies. The backend API enforces permission boundaries at the database query level (returning 403 Forbidden on unauthorized requests).*
> - ***Streamlit Decoupled***: *Streamlit now acts exclusively as an API consumer via our `KautilyaAPIClient` adapter. If the backend is offline, the UI alerts the user and degrades gracefully.*

---

### Part 2: 3-Minute Live Demo Flow

#### Step 1: Open the Swagger Interactive API Documentation
- **URL**: `http://127.0.0.1:8000/docs`
- **What to say**:
  > *"Here is the standalone Agent Kautilya REST Backend. You can see our structured API routes for Authentication, Projects, Ingestion, Audits, Vendors, and Reports. All sensitive endpoints are secured by OAuth2 Bearer tokens."*
- **Action**: Show `/api/data/quality/{run_id}` and `/api/vendors`.

#### Step 2: Show the Data Quality Audit Report
- **Endpoint**: `GET /api/data/quality/{run_id}`
- **What to say**:
  > *"When data is ingested, the system automatically checks for formatting errors, missing fields, and expenditure discrepancies. Notice that during our ingestion of 3,340 sanctions, the validation engine successfully flagged 1,849 warnings where expenditure exceeded sanctioned budgets before any ML was even run."*

#### Step 3: Open the Streamlit User Interface
- **URL**: `http://localhost:8501`
- **What to say**:
  > *"Notice the green badge in our navigation sidebar: `🟢 REST BACKEND ACTIVE (FastAPI Engine • SQLite • JWT Auth)`. The frontend is actively receiving tokenized data from our backend."*
- **Action**: Show login as **Ministry / CAG Auditor** (`auditor@mospi.gov.in` / `SIH2026Kautilya`).

#### Step 4: Demonstrate Real-Time Backend Inference & PDF Generation
- **Page**: **Project Directory** -> Select a High-Risk Project -> **Autonomous Audit** -> **CAG Case Dossier**.
- **Action**: Click *"Download CAG-Oriented Audit Memo"*.
- **What to say**:
  > *"When an auditor requests an audit memo, the backend dynamically calculates the risk score via our hybrid ML+Rules engine, generates the official CAG memorandum on the server using FPDF2, and streams the binary PDF to the user."*

#### Step 5: Show the Automated Parity & Verification Suite
- **Terminal Command**: `python parity_check.py`
- **What to say**:
  > *"To ensure zero regression or data loss during this migration, we built an automated parity test suite. As you can see, all 3,340 records, total sanctioned values, risk level distributions, and ML metrics match our baseline with 100% precision."*

---

### Part 3: Quick Reference Cheat Sheet

| Role | Username | Password | Access Level |
| :--- | :--- | :--- | :--- |
| **Ministry / CAG Auditor** | `auditor@mospi.gov.in` | `SIH2026Kautilya` | Full National Forensic Oversight |
| **District Collector** | `collector@nic.in` | `MPLADS-DA-2026` | District Sanctions & Inspections |
| **Member of Parliament** | `MP001` | `CF766A` | Scoped strictly to Hingoli Constituency |
| **Public Citizen** | *(No credentials)* | *(Guest Access)* | Public Civic Works (Risk Scores Masked) |

---

### Part 4: Commands to Launch

```powershell
# Option A: One-Click Startup (starts both Backend & Streamlit)
.\run.bat

# Option B: Python Orchestrator
python launch.py

# Option C: Run Parity Verification Suite
python parity_check.py
```
