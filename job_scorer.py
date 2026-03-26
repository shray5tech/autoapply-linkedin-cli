import os
import json
import sys
import re
import time
import requests
from bs4 import BeautifulSoup

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (DREAM_JOB_THRESHOLD, AUTO_APPLY_THRESHOLD,
                    MAYBE_THRESHOLD, MIN_SALARY_LPA, JOB_MAX_AGE_DAYS, PROFILE_PATH)
from sentence_transformers import SentenceTransformer, util
from datetime import datetime, date

model = SentenceTransformer('all-MiniLM-L6-v2')

TITLE_ALIASES = [
    "machine learning", "ml engineer", "ai engineer", "data scientist",
    "applied scientist", "research scientist", "nlp engineer", "mlops",
    "ml ops", "computer vision engineer", "deep learning engineer",
    "data science", "artificial intelligence", "ai/ml", "ai ml",
    "quantitative analyst", "decision scientist", "analytics engineer",
    "data analyst", "business intelligence", "bi engineer", "llm engineer",
    "generative ai", "gen ai", "prompt engineer", "ai researcher",
    "product analyst", "ai product analyst", "growth analyst",
    "business analyst", "product data scientist", "ai product manager",
    "analytics manager", "product manager ai"
]

GLASSDOOR_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def load_profile():
    with open(PROFILE_PATH, "r") as f:
        return json.load(f)


def parse_salary(salary_str):
    if not salary_str:
        return None, None
    try:
        salary_str = (salary_str.lower()
                      .replace("lpa", "").replace("lakh", "")
                      .replace("₹", "").replace(",", "").strip())
        if "-" in salary_str:
            parts = salary_str.split("-")
            return float(parts[0].strip()), float(parts[1].strip())
        return float(salary_str.strip()), float(salary_str.strip())
    except:
        return None, None


def fetch_salary_glassdoor(company, job_title):
    """
    Try to fetch salary from Glassdoor for a given company + role.
    Returns (min_lpa, max_lpa) or (None, None) if not found.
    """
    try:
        query = f"{company} {job_title} salary India site:glassdoor.co.in"
        url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
        resp = requests.get(url, headers=GLASSDOOR_HEADERS, timeout=8)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Look for salary pattern in Google snippet: "₹X - ₹Y" or "X LPA - Y LPA"
        text = soup.get_text()
        patterns = [
            r'₹\s*(\d+(?:\.\d+)?)\s*[–\-]\s*₹\s*(\d+(?:\.\d+)?)\s*(?:L|lakh|LPA)',
            r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*(?:LPA|lpa|L PA)',
            r'(\d+(?:\.\d+)?)\s*(?:LPA|lpa)\s*[-–]\s*(\d+(?:\.\d+)?)\s*(?:LPA|lpa)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                low = float(match.group(1))
                high = float(match.group(2))
                # Sanity check — reasonable Indian salary range
                if 3 <= low <= 200 and 3 <= high <= 200:
                    return low, high

    except Exception:
        pass
    return None, None


def get_company_tier(company_name, profile):
    """
    Returns salary assumption based on company tier:
    tier1 → 80 (known high payer, missing salary is fine)
    tier2 → 45 (known low payer)
    unknown → 55 (neutral)
    """
    company_lower = company_name.lower()
    tiers = profile.get("company_tiers", {})

    tier1 = [c.lower() for c in tiers.get("tier1_high_pay", [])]
    tier2 = [c.lower() for c in tiers.get("tier2_mid_pay", [])]
    tier3_keywords = [k.lower() for k in tiers.get("tier3_low_pay_keywords", [])]

    if any(t in company_lower for t in tier1):
        return "tier1", 80
    elif any(t in company_lower for t in tier2):
        return "tier2", 45
    elif any(k in company_lower for k in tier3_keywords):
        return "tier3", 30
    else:
        return "unknown", 55


def score_location(job_location):
    job_location = job_location.lower()
    tier1 = ["noida", "delhi", "gurugram", "gurgaon", "ncr", "new delhi"]
    tier2 = ["bengaluru", "bangalore", "hyderabad", "pune", "mumbai", "chennai", "kolkata"]
    tier3 = ["remote"]
    tier4 = ["united states", "usa", "canada", "germany", "netherlands",
             "singapore", "united kingdom", "uk", "australia",
             "new zealand", "sweden", "denmark", "ireland", "dubai", "uae"]
    tier5 = ["india"]

    if any(loc in job_location for loc in tier1):
        return 100, "Ideal location (NCR)"
    elif any(loc in job_location for loc in tier3):
        return 85, "Remote"
    elif any(loc in job_location for loc in tier2):
        return 75, "Relocatable city"
    elif any(loc in job_location for loc in tier4):
        return 70, "Visa sponsorship country"
    elif any(loc in job_location for loc in tier5):
        return 50, "India (other city)"
    else:
        return 20, "Unknown/undesired location"


def score_title(job_title, profile):
    if not job_title:
        return 30
    job_title_lower = job_title.lower()

    alias_score = 0
    if any(alias in job_title_lower for alias in TITLE_ALIASES):
        alias_score = 90
    elif "data" in job_title_lower and "engineer" in job_title_lower:
        alias_score = 60
    elif "data" in job_title_lower or "analyst" in job_title_lower:
        alias_score = 55
    elif "product" in job_title_lower and "manager" in job_title_lower:
        alias_score = 50
    elif "software engineer" in job_title_lower or "developer" in job_title_lower:
        alias_score = 25

    target_roles_text = " ".join(profile["job_targets"]["roles"])
    title_emb = model.encode(job_title, convert_to_tensor=True)
    roles_emb = model.encode(target_roles_text, convert_to_tensor=True)
    semantic_similarity = float(util.cos_sim(title_emb, roles_emb)[0][0])
    semantic_score = min(100, semantic_similarity * 160)

    return max(alias_score, semantic_score)


def build_skills_prose(profile):
    skills = profile.get("skills", [])
    exp = profile.get("experience", [{}])
    duration = exp[0].get("duration", "4 years") if exp else "4 years"

    prose = f"""
    Experienced data scientist and machine learning engineer with {duration} of industry experience.
    Proficient in building and deploying end-to-end machine learning pipelines using Python,
    including XGBoost, Random Forest, Logistic Regression, and neural networks.
    Strong SQL expertise for large-scale data extraction, transformation, and analysis.
    Hands-on NLP experience including sentiment analysis, text classification, and LLMs.
    Built production RAG pipelines using LangChain, ChromaDB, and Gemini API.
    Experienced in feature engineering, model evaluation, A/B testing, and hypothesis testing.
    Delivered customer analytics and business insights to senior stakeholders at American Express.
    Built AI automation systems, REST APIs with Flask, and interactive dashboards with Streamlit.
    Familiar with product analytics, growth metrics, funnel analysis, and business intelligence.
    Skilled with Power BI, Tableau, DAX, Excel, Git, Docker, and cloud basics (AWS, Azure, GCP).
    Additional tools and technologies: {", ".join(skills[:30])}.
    """
    return prose.strip()


def keyword_overlap_score(skills_list, jd_text):
    """
    Smarter keyword overlap — matches any word from multi-word skills.
    e.g. "RAG Pipelines" matches if "rag" OR "pipelines" in JD.
    """
    if not jd_text:
        return 50
    jd_lower = jd_text.lower()
    matches = 0
    for skill in skills_list:
        skill_lower = skill.lower()
        skill_words = [w for w in skill_lower.split() if len(w) > 3]
        if skill_words and any(word in jd_lower for word in skill_words):
            matches += 1
        elif skill_lower in jd_lower:
            matches += 1
    overlap = matches / max(len(skills_list), 1)
    return min(100, overlap * 200)  # 50% skill match = 100


def score_job(job):
    profile = load_profile()
    score = 0
    reasons = []

    # --- Hard filters ---
    sal_min, sal_max = parse_salary(job.get("salary_range", ""))
    min_salary = profile["job_targets"].get("min_salary_lpa", MIN_SALARY_LPA)

    if sal_max is not None and sal_max < min_salary:
        return {"score": 0, "queue": "skip",
                "reason": f"Salary {sal_max}LPA below minimum {min_salary}LPA"}

    if job.get("posted_date"):
        try:
            posted = datetime.strptime(job["posted_date"], "%Y-%m-%d").date()
            age_days = (date.today() - posted).days
            if age_days > JOB_MAX_AGE_DAYS:
                return {"score": 0, "queue": "skip",
                        "reason": f"Job posted {age_days} days ago — too old"}
        except:
            pass

    blacklist = [c.lower() for c in profile["job_targets"].get("blacklisted_companies", [])]
    if job.get("company", "").lower() in blacklist:
        return {"score": 0, "queue": "skip", "reason": "Company is blacklisted"}

    jd_text = job.get("jd_text", "")

    # --- Skills match — semantic prose (35% weight) ---
    skills_prose = build_skills_prose(profile)
    if jd_text:
        prose_emb = model.encode(skills_prose, convert_to_tensor=True)
        jd_emb = model.encode(jd_text, convert_to_tensor=True)
        similarity = float(util.cos_sim(prose_emb, jd_emb)[0][0])
        semantic_score = min(100, similarity * 150)
    else:
        semantic_score = 50
    score += semantic_score * 0.35
    reasons.append(f"Semantic match: {semantic_score:.0f}%")

    # --- Keyword overlap (15% weight) ---
    skills_list = profile.get("skills", [])
    kw_score = keyword_overlap_score(skills_list, jd_text)
    score += kw_score * 0.15
    reasons.append(f"Keyword overlap: {kw_score:.0f}%")

    # --- Title match — hybrid (25% weight) ---
    title_score = score_title(job.get("title", ""), profile)
    score += title_score * 0.25
    reasons.append(f"Title match: {title_score:.0f}%")

    # --- Salary match (15% weight) ---
    company_name = job.get("company", "")
    target_salary = profile["job_targets"]["target_salary_lpa"]

    if sal_min is not None:
        # Salary explicitly listed
        if sal_min >= target_salary:
            sal_score = 100
        elif sal_min >= min_salary:
            sal_score = 70
        else:
            sal_score = 30
        sal_source = "listed"
    else:
        # Try Glassdoor first
        gd_min, gd_max = fetch_salary_glassdoor(company_name, job.get("title", ""))
        if gd_min is not None:
            if gd_min >= target_salary:
                sal_score = 100
            elif gd_min >= min_salary:
                sal_score = 70
            else:
                sal_score = 40
            sal_source = f"Glassdoor ~{gd_min}-{gd_max}LPA"
        else:
            # Fall back to company tier
            tier, tier_score = get_company_tier(company_name, profile)
            sal_score = tier_score
            sal_source = f"estimated ({tier})"

    score += sal_score * 0.15
    reasons.append(f"Salary match: {sal_score}% ({sal_source})")

    # --- Location match (10% weight) ---
    loc_score, loc_reason = score_location(job.get("location", ""))
    score += loc_score * 0.10
    reasons.append(f"Location: {loc_score}% ({loc_reason})")

    final_score = round(score)

    if final_score >= DREAM_JOB_THRESHOLD:
        queue = "dream"
    elif final_score >= AUTO_APPLY_THRESHOLD:
        queue = "auto_apply"
    elif final_score >= MAYBE_THRESHOLD:
        queue = "maybe"
    else:
        queue = "skip"

    return {"score": final_score, "queue": queue, "reasons": reasons}


if __name__ == "__main__":
    tests = [
        {
            "title": "Machine Learning Engineer",
            "company": "Flipkart",
            "jd_text": "Python, scikit-learn, XGBoost, SQL, feature engineering, NLP, LangChain, RAG pipelines, recommendation systems.",
            "salary_range": "18-28 LPA",
            "location": "Bangalore / Remote",
            "posted_date": "2026-03-10",
        },
        {
            "title": "Applied Scientist",
            "company": "Amazon",
            "jd_text": "Deep learning, NLP, Python, PyTorch, model deployment, A/B testing, large scale ML systems.",
            "salary_range": "",
            "location": "Hyderabad, India",
            "posted_date": "2026-03-09",
        },
        {
            "title": "Data Scientist",
            "company": "EXL",
            "jd_text": "Python, SQL, machine learning, data analysis, statistical modeling, business insights.",
            "salary_range": "12-18 LPA",
            "location": "Noida",
            "posted_date": "2026-03-08",
        },
        {
            "title": "Java Backend Developer",
            "company": "TCS",
            "jd_text": "Java, Spring Boot, REST APIs, microservices, SQL, Docker.",
            "salary_range": "10-15 LPA",
            "location": "Chennai",
            "posted_date": "2026-03-07",
        },
        {
            "title": "Decision Scientist",
            "company": "American Express",
            "jd_text": "Python, statistical modeling, SQL, predictive analytics, customer segmentation.",
            "salary_range": "",
            "location": "Gurugram",
            "posted_date": "2026-03-10",
        },
        {
            "title": "Product Analyst",
            "company": "Swiggy",
            "jd_text": "SQL, Python, product metrics, funnel analysis, A/B testing, dashboards, business insights, growth analytics.",
            "salary_range": "",
            "location": "Bengaluru",
            "posted_date": "2026-03-10",
        }
    ]

    for job in tests:
        result = score_job(job)
        print(f"\n{job['title']} @ {job['company']}")
        print(f"  Score: {result['score']}/100 — {result['queue'].upper()}")
        for r in result['reasons']:
            print(f"  → {r}")
