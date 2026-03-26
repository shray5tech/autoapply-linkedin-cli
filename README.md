# AutoApply v1 – LinkedIn Job Intelligence Database

A single-user job application automation tool that scrapes LinkedIn jobs, scores them for fit, and optionally generates ATS‑aware resumes and cover letters for high‑fit opportunities.

## 🎯 Purpose

AutoApply helps me (Shray) systematically search and apply to ML Engineer, AI Engineer, and Data Scientist roles in NCR + remote locations.  
It uses a two‑stage approach: cheap fit scoring first, then expensive LLM‑powered content generation only for promising jobs.

## 🛠 Tech Stack

- Python 3.8+ – Core automation  
- Selenium/Playwright – LinkedIn job scraping  
- sentence‑transformers – Semantic similarity for fit scoring  
- Gemini 2.5 Flash – Resume/cover letter generation  
- SQLite – Job metadata and tracking  
- ReportLab – PDF generation  

***

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Clone and setup
git clone <repo>
cd autoapply-linkedin-cli
python -m venv venv
# Linux/macOS
source venv/bin/activate
# Windows
# venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Create .env file (or copy example if present)
cp .env.example .env  # if .env.example exists

# Add your keys and credentials (edit .env)
GOOGLE_API_KEY=your_gemini_api_key
LINKEDIN_EMAIL=your_email
LINKEDIN_PASSWORD=your_password
```

### 3. Update Profile

Edit `profile/profile.json` with your:

- Personal details (name, contact info)  
- Work experience and achievements  
- Skills and projects  
- Job preferences and company tiers  

### 4. Run AutoApply (Missions)

Each run is a **mission** that processes up to *N* new LinkedIn jobs (default 20, overridable with `DEV_MAX_JOBS`).

**Development – scraping only (fast, no documents):**

```bash
# PowerShell style
$env:MOCK_MODE="true"
$env:GENERATE_DOCUMENTS="false"
$env:DEV_MAX_JOBS="5"
python job_finder.py
```

**Development – mock resumes & cover letters (no API cost):**

```bash
$env:MOCK_MODE="true"
$env:GENERATE_DOCUMENTS="true"
$env:DEV_MAX_JOBS="5"
python job_finder.py
```

**Production – real resumes & cover letters (with spend caps):**

```bash
$env:MOCK_MODE="false"
$env:GENERATE_DOCUMENTS="true"
python job_finder.py
```

***

## 📊 How It Works

### Stage 1: Job Discovery & Scoring

- Scrapes LinkedIn jobs for target roles/locations.  
- Extracts:
  - Job title, company, location, salary text.  
  - Easy Apply flag, remote flag.  
  - Job description, apply link, job ID (for dedup).  
- Computes `fit_score` (0–100) using:
  - Semantic skills matching (35%)  
  - Keyword overlap (15%)  
  - Title similarity (25%)  
  - Salary estimation vs target (15%)  
  - Location preference (10%)  
- Stores all jobs in SQLite with deduplication via `job_external_id`.

### Stage 2: Content Generation (High‑Fit Only, Optional)

- Jobs with `fit_score >= 70` are considered **high‑fit**.  
- If `GENERATE_DOCUMENTS=true`:
  - Generates an ATS‑optimized resume tailored to the JD.  
  - Creates a personalized cover letter.  
  - Computes and stores an `ats_score` (0–100) for the resume vs JD.  
- If `GENERATE_DOCUMENTS=false`:
  - Only metadata + `match_score` are stored.  
  - No resume, cover letter, or ats_score is generated (fields stay NULL/NA).

### Queue Classification

(implicit from `fit_score` thresholds)

- **Dream** (87+): Top‑tier companies or perfect fit.  
- **Auto‑Apply** (70–86): Strong fit, auto‑generate docs when enabled.  
- **Maybe** (45–69): Decent fit, metadata only.  
- **Skip** (<45): Poor fit, ignore.

***

## 🗂 Database Schema

### Applications Table (core fields)

```text
app_id           INTEGER PRIMARY KEY
job_title        TEXT
company          TEXT
platform         TEXT           -- 'LinkedIn'
job_external_id  TEXT UNIQUE    -- deduplication key
jd_text          TEXT

match_score      REAL           -- fit_score from job_scorer
ats_score        REAL           -- ATS evaluation of generated resume (NULL if no docs)

resume_path      TEXT           -- path to generated resume (NULL if no docs)
cover_letter_path TEXT          -- path to generated cover letter (NULL if no docs)

easy_apply       INTEGER        -- 0/1 for LinkedIn Easy Apply
remote           INTEGER        -- 0/1 for remote roles
apply_by_date    TEXT           -- application deadline (if available)
expected_salary  TEXT           -- salary pulled from LinkedIn text

apply_link       TEXT
status           TEXT DEFAULT 'Applied'
salary_range     TEXT
applied_date     TEXT
-- ... other metadata fields (follow_up_date, notes, etc.)
```

### API Spend Table

Tracks daily Gemini usage with spend limits and pause/resume controls.

***

## ⚙️ Configuration

### Key Settings (`config.py`)

```python
# Scoring thresholds
DREAM_JOB_THRESHOLD = 87
AUTO_APPLY_THRESHOLD = 70
MAYBE_THRESHOLD      = 45

# Development limits
DEV_MAX_JOBS_PER_RUN   = 30
MISSION_JOB_BATCH_SIZE = 20
MOCK_MODE              = True   # Free dev mode

# Document generation toggle (can be overridden via env)
GENERATE_DOCUMENTS_DEFAULT = True

# Cost control
MAX_API_SPEND_INR = 20.0
HEADLESS_MODE     = True  # Browser automation

# Job targets
TARGET_ROLES       = ["ML Engineer", "AI Engineer", "Data Scientist"]
MIN_SALARY_LPA     = 12
TARGET_SALARY_LPA  = 20
```

***

## 🧪 Development Mode

`MOCK_MODE` enables free development:

- Generates dummy resumes/cover letters clearly marked **"MOCK"**.  
- Sets a fixed, realistic `ats_score` (e.g., 85.0) for testing.  
- No real Gemini API calls.  
- Respects mission/job limits and runs in headless browser mode (unless overridden).

Use `GENERATE_DOCUMENTS=false` to test **only scraping + scoring** without touching document logic.

***

## 📈 Output & Files

- `outputs/resumes/` – Generated tailored resumes (PDF).  
- `outputs/cover_letters/` – Generated cover letters (PDF).  
- `database/autoapply.db` – Complete job database (applications + api_spend).  
- `profile/profile.json` – Your structured resume/profile data.  
- `archive/` – Naukri prototype and legacy/dev scripts (not used in v1 runtime).

***

## 🔍 Features

### ✅ Implemented (v1)

- LinkedIn job scraping (NCR + remote).  
- Multi‑signal fit scoring without LLM.  
- Mission‑based runs (up to N new jobs per mission).  
- Two‑stage gating (fit_score → optional LLM generation).  
- ATS‑aware resume tailoring (single‑pass, logged ats_score).  
- Job deduplication via LinkedIn job IDs.  
- Cost control with spend limits and `spend_watchdog`.  
- Headless browser automation (debuggable with HEADLESS_MODE=false).  
- Mock mode for development (no API cost).  
- Optional document generation via `GENERATE_DOCUMENTS` flag.  
- Extra metadata for future UI: `remote`, `easy_apply`, `apply_by_date`, `expected_salary`.

### 🚧 Future Work

- Naukri/Indeed platform support.  
- Auto‑fill application forms (Easy Apply and custom).  
- Interview tracking dashboard.  
- A/B testing for resume versions.  
- Web UI (filters, job count, document toggle, table view).  
- Multi‑user support.

***

## 🐛 Troubleshooting

### Common Issues

- **LinkedIn login fails:**  
  Check credentials in `.env`, and verify you can log in manually in the same browser profile.

- **No jobs found:**  
  Verify `TARGET_ROLES` and location filters, and check LinkedIn’s own search results.

- **API spend limit reached:**  
  Use functions in `spend_watchdog.py` to approve more spend or wait for daily reset.

- **Chrome profile issues:**  
  Delete `chrome_profile/` folder and rerun to reinitialize.

### Debug Mode

```bash
# Run with visible browser for debugging
$env:HEADLESS_MODE="false"
python job_finder.py
```

***

## 📄 License

Personal project for my job search. Not intended for commercial use.

***

## DEV_NOTES

This v1 was completed quickly with focus on:

### Database Schema Upgrades

- Added `job_external_id` with UNIQUE constraint for deduplication.  
- Added `ats_score` column separate from `match_score`.  
- Added `easy_apply`, `remote`, `apply_by_date`, and `expected_salary` fields.  
- Implemented safe migration logic in `database/db.py`.

### Two‑Stage Scoring Implementation

- Stage 1: Compute `fit_score` (non‑LLM) for **all** jobs.  
- Stage 2: Generate LLM content only for jobs with `fit_score >= 70`.  
- Implemented in `process_job()` with proper gating logic.

### Job Deduplication & Limits

- Extract LinkedIn job IDs via `extract_job_external_id()` function.  
- Check duplicates before database insertion.  
- Added `DEV_MAX_JOBS_PER_RUN` (30) and mission batch size (20) for development.  
- Progress logging: “Processing job i/MAX_JOBS: title @ company”.

### Mock Mode for Development

- Default `MOCK_MODE=True` for free development testing.  
- Generates dummy resumes/cover letters clearly marked as "MOCK".  
- ATS score set to a fixed value (e.g., 85.0) in mock mode.  
- No real Gemini API calls.

### Headless Automation

- Default `HEADLESS_MODE=True` for production runs.  
- Stable Chrome options for headless operation.  
- Can be disabled for debugging with `HEADLESS_MODE=false`.

### Repository Cleanup

- Moved old Naukri code and dev helpers into `archive/`.  
- Clean folder structure ready for portfolio showcase.  
- `.gitignore` configured for env files, DBs, outputs, venv, and IDE configs.

### Testing

- Database operations tested and working.  
- Job scoring functional.  
- MOCK_MODE resume generation working.  
- ats_score persistence verified.  

The system is now ready for real‑world use with proper cost controls, job deduplication, and efficient two‑stage processing.

---
