# AutoApply v1 - LinkedIn Job Intelligence Database

A single-user job application automation tool that scrapes LinkedIn jobs, scores them for fit, and generates tailored resumes/cover letters for high-fit opportunities.

## 🎯 Purpose

AutoApply helps me (Shray) systematically search and apply to ML Engineer, AI Engineer, and Data Scientist roles in NCR + remote locations. It uses a two-stage approach: cheap fit scoring first, then expensive LLM-powered content generation only for promising jobs.

## 🛠 Tech Stack

- **Python 3.8+** - Core automation
- **Selenium/Playwright** - LinkedIn job scraping  
- **sentence-transformers** - Semantic similarity for fit scoring
- **Gemini 2.5 Flash** - Resume/cover letter generation
- **SQLite** - Job metadata and tracking
- **ReportLab** - PDF generation

## 🚀 Quick Start

### 1. Setup Environment
```bash
# Clone and setup
git clone <repo>
cd AutoApply
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Create .env file
cp .env.example .env

# Add your API key
echo "GOOGLE_API_KEY=your_gemini_api_key" >> .env
echo "LINKEDIN_EMAIL=your_email" >> .env  
echo "LINKEDIN_PASSWORD=your_password" >> .env
```

### 3. Update Profile
Edit `profile/profile.json` with your:
- Personal details (name, contact info)
- Work experience and achievements
- Skills and projects
- Job preferences and company tiers

### 4. Run AutoApply
```bash
# Development mode (free, limited jobs)
export MOCK_MODE=true
export DEV_MAX_JOBS=30
python job_finder.py

# Production mode (real API calls)
export MOCK_MODE=false
python job_finder.py
```

## 📊 How It Works

### Stage 1: Job Discovery & Scoring
- Scrapes LinkedIn jobs for target roles/locations
- Computes **fit_score** (0-100) using:
  - Semantic skills matching (35%)
  - Keyword overlap (15%) 
  - Title similarity (25%)
  - Salary estimation (15%)
  - Location preference (10%)
- Stores all jobs in SQLite with deduplication

### Stage 2: Content Generation (High-Fit Only)
- Jobs with `fit_score >= 70` trigger LLM calls
- Generates ATS-optimized resume tailored to JD
- Creates personalized cover letter
- Stores document paths and **ats_score** in database

### Queue Classification
- **Dream** (87+): Top-tier companies or perfect fit
- **Auto-Apply** (70-86): Strong fit, auto-generate docs  
- **Maybe** (45-69): Decent fit, metadata only
- **Skip** (<45): Poor fit, ignore

## 🗂 Database Schema

### Applications Table
```sql
app_id INTEGER PRIMARY KEY
job_title TEXT
company TEXT  
platform TEXT -- 'LinkedIn'
job_external_id TEXT UNIQUE -- deduplication key
jd_text TEXT
match_score REAL -- fit_score from job_scorer
ats_score REAL -- ATS evaluation of generated resume
resume_path TEXT
cover_letter_path TEXT
easy_apply INTEGER -- 0/1 for LinkedIn Easy Apply
status TEXT DEFAULT 'Applied'
salary_range TEXT
applied_date TEXT
-- ... other metadata fields
```

### API Spend Table
Tracks daily Gemini usage with spend limits and pause/resume controls.

## ⚙️ Configuration

### Key Settings (`config.py`)
```python
# Scoring thresholds
DREAM_JOB_THRESHOLD = 87
AUTO_APPLY_THRESHOLD = 70  
MAYBE_THRESHOLD = 45

# Development limits
DEV_MAX_JOBS_PER_RUN = 30
MOCK_MODE = True  # Free dev mode

# Cost control  
MAX_API_SPEND_INR = 20.0
HEADLESS_MODE = True  # Browser automation

# Job targets
TARGET_ROLES = ["ML Engineer", "AI Engineer", "Data Scientist"]
MIN_SALARY_LPA = 12
TARGET_SALARY_LPA = 20
```

## 🧪 Development Mode

MOCK_MODE enables free development:
- Generates dummy resumes/cover letters marked "MOCK"
- No real Gemini API calls
- Processes limited jobs (30 by default)
- Runs in headless browser mode

## 📈 Output Files

- `outputs/resumes/` - Generated tailored resumes
- `outputs/cover_letters/` - Generated cover letters  
- `outputs/easy_apply_jobs.xlsx` - Job export with scores
- `database/autoapply.db` - Complete job database

## 🔍 Features

### ✅ Implemented (v1)
- LinkedIn job scraping (NCR + remote)
- Multi-signal fit scoring without LLM
- Two-stage gating (fit score → LLM generation)
- ATS-aware resume tailoring
- Job deduplication via LinkedIn job IDs
- Cost control with spend limits
- Headless browser automation
- Mock mode for development

### 🚧 Future Work
- Naukri/Indeed platform support
- Auto-fill application forms
- Interview tracking dashboard
- A/B testing for resume versions
- Multi-user support

## 🐛 Troubleshooting

### Common Issues
- **LinkedIn login fails**: Check credentials in .env, manual verification may be needed
- **No jobs found**: Verify target roles/locations, check LinkedIn search limits
- **API spend limit reached**: Use `approve_resume()` in spend_watchdog.py or wait for daily reset
- **Chrome profile issues**: Delete `chrome_profile/` folder and re-run

### Debug Mode
```bash
# Run with visible browser for debugging
export HEADLESS_MODE=false
python job_finder.py
```

## 📄 License

Personal project for my job search. Not intended for commercial use.

---

**DEV_NOTES**: This v1 was completed overnight with focus on:

### Database Schema Upgrades
- Added `job_external_id` with UNIQUE constraint for deduplication
- Added `ats_score` column separate from `match_score` 
- Added `easy_apply` boolean field
- Implemented safe migration logic in `database/db.py`

### Two-Stage Scoring Implementation  
- Stage 1: Compute fit_score (non-LLM) for ALL jobs
- Stage 2: Generate LLM content only for jobs with fit_score >= 70
- Implemented in `process_job()` function with proper gating logic

### Job Deduplication & Limits
- Extract LinkedIn job IDs via `extract_job_external_id()` function
- Check duplicates before database insertion
- Added `DEV_MAX_JOBS_PER_RUN` (30) for development
- Progress logging: "Processing job i/MAX_JOBS: title @ company"

### Mock Mode for Development
- Default `MOCK_MODE=True` for free development testing
- Generates dummy resumes/cover letters clearly marked as "MOCK"
- ATS score set to 85.0 in mock mode
- No real Gemini API calls

### Headless Automation
- Default `HEADLESS_MODE=True` for production runs
- Robust Chrome options for stable headless operation
- Can be disabled for debugging with `HEADLESS_MODE=false`

### Repository Cleanup
- Moved `naukri_sync.py` to `archive/` folder
- Clean folder structure ready for portfolio showcase
- Comprehensive README with setup instructions

### Key Files Modified
- `database/db.py` - Schema upgrades and helper functions
- `job_finder.py` - Two-stage gating, job limits, progress tracking
- `config.py` - Development limits and headless mode
- `resume_tailor.py` - MOCK_MODE implementation
- `cover_letter.py` - MOCK_MODE implementation

### Testing
- All database operations tested and working
- Job scoring functional (78/100 test score)
- MOCK_MODE resume generation working
- ATS score persistence verified

The system is now ready for production use with proper cost controls, job deduplication, and efficient two-stage processing.
