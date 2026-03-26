import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Development Mode
MOCK_MODE: bool = os.getenv("MOCK_MODE", "true").lower() == "true"  # True = no real Gemini calls

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILE_PATH = os.path.join(BASE_DIR, "profile", "profile.json")
DB_PATH = os.path.join(BASE_DIR, "database", "autoapply.db")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
RESUMES_DIR = os.path.join(OUTPUTS_DIR, "resumes")
COVER_LETTERS_DIR = os.path.join(OUTPUTS_DIR, "cover_letters")
SCREENSHOTS_DIR = os.path.join(OUTPUTS_DIR, "screenshots")
MANUAL_APPLY_DIR = os.path.join(OUTPUTS_DIR, "manual_apply")
DREAM_MANUAL_DIR = os.path.join(MANUAL_APPLY_DIR, "dream")
SALARY_MANUAL_DIR = os.path.join(MANUAL_APPLY_DIR, "salary_confirmed")

# Application limits
MAX_APPLICATIONS_PER_DAY = 50
MAX_API_SPEND_INR = 20.0
DEV_MAX_JOBS_PER_RUN = int(os.getenv("DEV_MAX_JOBS", "30"))  # Default 30 for dev
MISSION_JOB_BATCH_SIZE = int(os.getenv("MISSION_JOB_BATCH_SIZE", "20"))  # Jobs per mission
GENERATE_DOCUMENTS_DEFAULT = True  # Default to generating documents
HEADLESS_MODE = os.getenv("HEADLESS_MODE", "true").lower() == "true"  # Default headless for v1

# Scoring thresholds
DREAM_JOB_THRESHOLD = 87
AUTO_APPLY_THRESHOLD = 70
MAYBE_THRESHOLD = 45
ATS_SCORE_TARGET = 80
ATS_REWRITE_TRIGGER = 70

# Timing
FOLLOW_UP_DAYS = 7
FOLLOW_UP_ESCALATION_DAYS = 14
JOB_MAX_AGE_DAYS = 14
MIN_DELAY_BETWEEN_APPS = 30  # seconds
MAX_DELAY_BETWEEN_APPS = 90  # seconds

# Job targets
TARGET_ROLES = ["ML Engineer", "AI Engineer", "Data Scientist"]
MIN_SALARY_LPA = 12
TARGET_SALARY_LPA = 20

# NCR searches — WFO + Remote jobs in NCR region
NCR_SEARCH_LOCATIONS = [
    "Noida, Uttar Pradesh, India",
    "Delhi, India",
    "Gurugram, Haryana, India",
]

# Remote searches — trust LinkedIn's remote tag, no location filter applied
REMOTE_SEARCH_LOCATIONS = [
    "Remote",
    "Worldwide",
]

# NCR cities — acceptable for WFO
NCR_CITIES = [
    "noida", "delhi", "gurugram", "gurgaon", "ncr",
    "new delhi", "faridabad", "greater noida", "ghaziabad"
]

# Non-NCR cities — WFO here always skipped
NON_NCR_CITIES = [
    "bengaluru", "bangalore", "mumbai", "pune", "hyderabad",
    "chennai", "kolkata", "ahmedabad", "jaipur", "kochi",
    "chandigarh", "indore", "nagpur", "coimbatore", "surat",
    "bhubaneswar", "trivandrum", "mysuru", "mysore", "vadodara"
]

# Dream companies — generate manual package even without Easy Apply
DREAM_COMPANIES = [
    "google", "microsoft", "amazon", "meta", "apple", "netflix",
    "flipkart", "swiggy", "zomato", "razorpay", "phonepe", "groww",
    "meesho", "cred", "zepto", "myntra", "nykaa",
    "american express", "amex", "deloitte", "mckinsey", "bcg", "bain",
    "goldman sachs", "jpmorgan", "jp morgan", "morgan stanley",
    "adobe", "salesforce", "uber", "linkedin", "atlassian",
    "freshworks", "sprinklr", "browserstack", "moengage", "clevertap",
    "ibm", "sap", "oracle", "visa", "mastercard"
]
