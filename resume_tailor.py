import os
import sys
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    GEMINI_API_KEY, PROFILE_PATH, RESUMES_DIR,
    COVER_LETTERS_DIR, DREAM_MANUAL_DIR, SALARY_MANUAL_DIR, MOCK_MODE
)
from spend_watchdog import check_spend_limit, log_api_call
from google import genai
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib import colors
from datetime import date

client = genai.Client(api_key=GEMINI_API_KEY)


# ─────────────────────────────────────────────
# CORE HELPERS
# ─────────────────────────────────────────────

def load_profile():
    with open(PROFILE_PATH, "r") as f:
        return json.load(f)


def call_gemini(prompt):
    if not check_spend_limit():
        raise Exception("Daily API spend limit reached.")
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    tokens = response.usage_metadata.total_token_count if response.usage_metadata else 0
    cost = (tokens / 1000) * 0.008
    log_api_call(tokens, cost)
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def analyze_jd(jd_text):
    prompt = f"""Analyze this job description and extract:
1. Top 10 required skills/keywords (most important first)
2. Seniority level (Junior/Mid/Senior)
3. Primary role type (ML Engineer / AI Engineer / Data Scientist / Other)
4. Top 3 responsibilities in the JD
5. Company type (startup / mid-size / enterprise / bank / GCC)

Job Description:
{jd_text}

Respond in this exact JSON format:
{{
  "keywords": ["skill1", "skill2", ...],
  "seniority": "Mid",
  "role_type": "ML Engineer",
  "responsibilities": ["resp1", "resp2", "resp3"],
  "company_type": "enterprise"
}}"""
    return json.loads(call_gemini(prompt))


def tailor_bullets(achievements, jd_analysis):
    keywords = ", ".join(jd_analysis["keywords"])
    responsibilities = "\n".join(jd_analysis["responsibilities"])
    prompt = f"""You are a professional resume writer. Create ATS-optimized resume bullets.

REQUIREMENTS:
- Use clear, ATS-friendly structure: Summary, Skills, Experience, Education, Projects
- Include as many genuine JD keywords and required skills as feasible, integrated naturally
- Keep formatting simple: no tables, no multi-column layouts, clear headings only
- Keep content truthful to the provided profile data
- Focus on achievements with quantifiable metrics

ATS OPTIMIZATION:
- Start each bullet with strong action verbs (Developed, Implemented, Built, etc.)
- Include relevant keywords from JD naturally throughout bullets
- Use standard section headers that ATS systems recognize
- Avoid graphics, tables, or complex formatting
- Keep each bullet concise (under 2 lines)

KEYWORDS TO INTEGRATE: {keywords}
COMPANY TYPE: {jd_analysis['company_type']}
ROLE TYPE: {jd_analysis['role_type']}

ORIGINAL ACHIEVEMENTS:
{json.dumps(achievements, indent=2)}

JD RESPONSIBILITIES:
{responsibilities}

Return ONLY rewritten bullets as a JSON array of strings."""
    return json.loads(call_gemini(prompt))


def calculate_ats_score(tailored_bullets, jd_keywords, jd_text):
    bullet_text = " ".join(tailored_bullets)
    prompt = f"""You are an ATS (Applicant Tracking System) evaluator.

Score how well these resume bullets match the job description keywords.

Resume bullets:
{bullet_text}

JD Keywords to match: {", ".join(jd_keywords)}

Job Description:
{jd_text}

Rules:
- Consider synonyms and related terms as matches
- Consider partial matches for compound skills
- Return ONLY: {{"score": 75, "matched": ["Python", "SQL"], "missing": ["Docker"]}}"""

    result = json.loads(call_gemini(prompt))
    return result.get("score", 0), result.get("matched", []), result.get("missing", [])


def select_resume_version(role_type):
    role_type = role_type.lower()
    if "data scientist" in role_type:
        return "data_scientist"
    elif "ai engineer" in role_type:
        return "ai_engineer"
    return "ml_engineer"


# ─────────────────────────────────────────────
# PDF GENERATOR
# ─────────────────────────────────────────────

def generate_pdf(profile, tailored_bullets, jd_analysis, company_name, job_title, output_dir=None):
    save_dir = output_dir if output_dir else RESUMES_DIR
    os.makedirs(save_dir, exist_ok=True)

    safe_company = company_name.replace(" ", "_").replace("/", "_")
    safe_role    = job_title.replace(" ", "_").replace("/", "_")
    filename     = f"Shray_Bisht_{safe_company}_{safe_role}.pdf"
    filepath     = os.path.join(save_dir, filename)

    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            rightMargin=20*mm, leftMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    story = []

    name_style      = ParagraphStyle('name', fontSize=16, fontName='Helvetica-Bold',
                                     alignment=TA_CENTER, spaceAfter=6, leading=20,
                                     textColor=colors.HexColor('#1a1a2e'))
    contact_style   = ParagraphStyle('contact', fontSize=9, fontName='Helvetica',
                                     alignment=TA_CENTER, spaceAfter=6, leading=14,
                                     textColor=colors.HexColor('#333333'))
    section_style   = ParagraphStyle('section', fontSize=10, fontName='Helvetica-Bold',
                                     spaceBefore=10, spaceAfter=2,
                                     textColor=colors.HexColor('#1a1a2e'))
    job_title_style = ParagraphStyle('jobtitle', fontSize=9.5, fontName='Helvetica-Bold',
                                     spaceBefore=6, spaceAfter=1)
    job_meta_style  = ParagraphStyle('jobmeta', fontSize=8.5, fontName='Helvetica',
                                     spaceAfter=4, textColor=colors.HexColor('#555555'))
    bullet_style    = ParagraphStyle('bullet', fontSize=9, fontName='Helvetica',
                                     spaceAfter=3, leftIndent=10, leading=13)
    normal_style    = ParagraphStyle('normal', fontSize=9, fontName='Helvetica',
                                     spaceAfter=3, leading=13)
    summary_style   = ParagraphStyle('summary', fontSize=9, fontName='Helvetica',
                                     spaceAfter=4, leading=14,
                                     textColor=colors.HexColor('#333333'))

    def section_header(title):
        story.append(Paragraph(title, section_style))
        story.append(HRFlowable(width="100%", thickness=0.7,
                                color=colors.HexColor('#1a1a2e'), spaceAfter=5))

    p = profile["personal"]
    story.append(Paragraph(p["name"], name_style))
    story.append(Paragraph(
        f'{p["phone"]}  |  {p["email"]}  |  {p["location"]}', contact_style))
    story.append(Paragraph(
        f'<a href="{p["linkedin"]}"><u>LinkedIn</u></a>'
        f'  |  <a href="{p["github"]}"><u>GitHub</u></a>', contact_style))
    story.append(HRFlowable(width="100%", thickness=1.2,
                            color=colors.HexColor('#1a1a2e'), spaceAfter=8))

    section_header("PROFESSIONAL SUMMARY")
    story.append(Paragraph(
        f'Results-driven <b>{jd_analysis["role_type"]}</b> with 4+ years of experience at American Express '
        f'in data analytics, ML model development, NLP, and sentiment analysis. '
        f'Proven track record of delivering measurable business impact. '
        f'Skilled in {", ".join(jd_analysis["keywords"][:6])}.',
        summary_style))

    section_header("EXPERIENCE")
    for exp in profile["experience"]:
        story.append(Paragraph(exp["title"], job_title_style))
        story.append(Paragraph(f'{exp["company"]}  |  {exp["duration"]}', job_meta_style))
        bullets = tailored_bullets if exp["company"] == "American Express" else exp["achievements"]
        for b in bullets:
            story.append(Paragraph(f'• {b}', bullet_style))

    section_header("PROJECTS")
    for proj in profile["projects"]:
        tech = ", ".join(proj["tech_stack"])
        story.append(Paragraph(proj["name"], job_title_style))
        story.append(Paragraph(f'Tech: {tech}', job_meta_style))
        story.append(Paragraph(proj["description"], bullet_style))
        if "highlights" in proj:
            story.append(Paragraph("• " + "  •  ".join(proj["highlights"]), bullet_style))

    section_header("SKILLS")
    story.append(Paragraph(", ".join(profile["skills"]), normal_style))

    section_header("EDUCATION")
    for edu in profile["education"]:
        story.append(Paragraph(
            f'<b>{edu["degree"]}</b>  |  {edu["institution"]}  |  {edu["year"]}',
            normal_style))

    section_header("CERTIFICATIONS")
    for cert in profile["certifications"]:
        story.append(Paragraph(f'• {cert}', bullet_style))

    doc.build(story)
    print(f"  ✅ Resume saved: {filepath}")
    return filepath


# ─────────────────────────────────────────────
# COVER LETTER GENERATOR
# ─────────────────────────────────────────────

def generate_cover_letter(jd_text, company_name, job_title, jd_analysis, output_dir=None):
    """
    Generates a tailored cover letter as .txt file.
    Saved to output_dir if provided, else COVER_LETTERS_DIR.
    Returns file path.
    """
    save_dir = output_dir if output_dir else COVER_LETTERS_DIR
    os.makedirs(save_dir, exist_ok=True)

    safe_company = company_name.replace(" ", "_").replace("/", "_")
    safe_role    = job_title.replace(" ", "_").replace("/", "_")
    filename     = f"CoverLetter_Shray_Bisht_{safe_company}_{safe_role}.txt"
    filepath     = os.path.join(save_dir, filename)

    prompt = f"""Write a professional cover letter for this job application.

Candidate: Shray Bisht
Applying for: {job_title} at {company_name}
Background: 4+ years at American Express in data analytics, ML model development, 
NLP pipelines, and sentiment analysis. Strong Python, SQL, XGBoost, scikit-learn skills.

JD Keywords to weave in: {', '.join(jd_analysis['keywords'][:8])}
Company type: {jd_analysis['company_type']}
Role type: {jd_analysis['role_type']}

RULES:
- 3 short paragraphs only
- Paragraph 1: Why this specific company and role excite you (be specific, not generic)
- Paragraph 2: 2-3 concrete achievements from Amex with actual numbers/impact
- Paragraph 3: Short confident closing with call to action
- Do NOT start with "I am writing to apply..."
- Do NOT use hollow phrases like "I am passionate about..."
- Sound like a confident professional, not a desperate applicant
- Plain text only, no markdown, no subject line, no "Dear Hiring Manager" header

Return ONLY the 3 paragraphs."""

    text = call_gemini(prompt)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"Cover Letter — {job_title} @ {company_name}\n")
        f.write(f"{'─' * 60}\n\n")
        f.write(text)
        f.write(f"\n\n{'─' * 60}\n")
        f.write(f"Generated: {date.today()}\n")

    print(f"  ✅ Cover letter saved: {filepath}")
    return filepath


# ─────────────────────────────────────────────
# MAIN TAILOR FUNCTION (Easy Apply jobs)
# ─────────────────────────────────────────────

def tailor_resume(jd_text, company_name, job_title, output_dir=None):
    print(f"  🔍 Tailoring resume: {job_title} @ {company_name}")
    
    if MOCK_MODE:
        print("  🧪 MOCK_MODE - Generating dummy resume")
        # Create dummy resume text
        resume_text = f"MOCK RESUME for {company_name} - {job_title}\n\nThis is a dummy resume for testing AutoApply."
        
        # Generate dummy JD analysis for consistency
        jd_analysis = {
            "keywords": ["Python", "SQL", "Machine Learning", "AI", "Data Science"],
            "seniority": "Mid",
            "role_type": "ML Engineer",
            "responsibilities": ["Build ML models", "Data analysis", "AI development"],
            "company_type": "enterprise"
        }
        
        # Create dummy tailored bullets
        tailored_bullets = [
            "MOCK: Applied ML models to solve business problems",
            "MOCK: Developed data pipelines using Python and SQL",
            "MOCK: Built AI solutions with 85% accuracy"
        ]
        
        # Set dummy ATS score
        ats_score = 85.0
        matched = jd_analysis["keywords"][:3]
        missing = jd_analysis["keywords"][3:]
        
        print(f"  📊 MOCK ATS Score: {ats_score}% | Matched: {matched} | Missing: {missing}")
        
        # Generate PDF with dummy content
        profile = load_profile()
        pdf_path = generate_pdf(
            profile, tailored_bullets, jd_analysis,
            company_name, job_title, output_dir=output_dir
        )
        
        return {
            "pdf_path":          pdf_path,
            "ats_score":         ats_score,
            "matched_keywords":  matched,
            "missing_keywords":  missing,
            "resume_version":    select_resume_version(jd_analysis["role_type"]),
            "jd_analysis":       jd_analysis
        }
    
    # Original Gemini logic (only runs when not MOCK_MODE)
    profile = load_profile()

    jd_analysis = analyze_jd(jd_text)
    print(f"  ✅ JD analyzed — Role: {jd_analysis['role_type']} | Keywords: {', '.join(jd_analysis['keywords'][:5])}")

    amex_achievements = profile["experience"][0]["achievements"]
    tailored_bullets  = tailor_bullets(amex_achievements, jd_analysis)

    # Single ATS scoring pass - no retry loop
    ats_score, matched, missing = calculate_ats_score(
        tailored_bullets, jd_analysis["keywords"], jd_text
    )
    print(f"  📊 ATS Score: {ats_score}% | Matched: {matched} | Missing: {missing}")

    pdf_path = generate_pdf(
        profile, tailored_bullets, jd_analysis,
        company_name, job_title, output_dir=output_dir
    )

    return {
        "pdf_path":          pdf_path,
        "ats_score":         ats_score,
        "matched_keywords":  matched,
        "missing_keywords":  missing,
        "resume_version":    select_resume_version(jd_analysis["role_type"]),
        "jd_analysis":       jd_analysis
    }


# ─────────────────────────────────────────────
# MANUAL PACKAGE GENERATOR
# ─────────────────────────────────────────────

def generate_manual_package(job: dict, queue_type: str):
    """
    Full manual application package for non-Easy Apply jobs.
    Returns (package_dir, resume_path, cover_letter_path)
    """
    base_dir = DREAM_MANUAL_DIR if queue_type == "dream" else SALARY_MANUAL_DIR

    safe_company = job["company"].replace(" ", "_").replace("/", "_")
    safe_title   = job["title"].replace(" ", "_").replace("/", "_")
    package_dir  = os.path.join(base_dir, f"{safe_company}_{safe_title}")
    os.makedirs(package_dir, exist_ok=True)

    resume_path = ""
    cl_path     = ""
    ats_score   = 0
    missing     = []
    jd_analysis = {}

    # 1. Tailored resume
    try:
        tailor_result = tailor_resume(
            jd_text=job.get("jd_text", ""),
            company_name=job["company"],
            job_title=job["title"],
            output_dir=package_dir
        )
        resume_path = tailor_result["pdf_path"]
        ats_score   = tailor_result["ats_score"]
        missing     = tailor_result["missing_keywords"]
        jd_analysis = tailor_result["jd_analysis"]
    except Exception as e:
        print(f"  ❌ Resume tailor failed: {e}")

    # 2. Cover letter
    try:
        cl_path = generate_cover_letter(
            jd_text=job.get("jd_text", ""),
            company_name=job["company"],
            job_title=job["title"],
            jd_analysis=jd_analysis if jd_analysis else {
                "keywords": [], "company_type": "enterprise", "role_type": "ML Engineer"
            },
            output_dir=package_dir
        )
    except Exception as e:
        print(f"  ❌ Cover letter failed: {e}")

    # 3. job_details.txt
    with open(os.path.join(package_dir, "job_details.txt"), "w", encoding="utf-8") as f:
        f.write(f"Job Title    : {job['title']}\n")
        f.write(f"Company      : {job['company']}\n")
        f.write(f"Location     : {job['location']}\n")
        f.write(f"Salary       : {job.get('salary_range', 'Not mentioned')}\n")
        f.write(f"Platform     : {job.get('platform', 'LinkedIn')}\n")
        f.write(f"Apply URL    : {job.get('url', 'N/A')}\n")
        f.write(f"Date Found   : {date.today()}\n")
        f.write(f"\n{'─'*60}\nJOB DESCRIPTION\n{'─'*60}\n")
        f.write(job.get("jd_text", "JD not available"))

    # 4. notes.txt
    reason = (
        "⭐ DREAM COMPANY — Easy Apply not available"
        if queue_type == "dream"
        else f"💰 SALARY CONFIRMED ≥ {job.get('salary_range', '')} — Easy Apply not available"
    )
    with open(os.path.join(package_dir, "notes.txt"), "w", encoding="utf-8") as f:
        f.write(f"WHY FLAGGED\n{'─'*40}\n{reason}\n\n")
        f.write(f"ATS SCORE    : {ats_score}%\n")
        f.write(f"MISSING KEYS : {', '.join(missing) if missing else 'None'}\n\n")
        f.write(f"MANUAL STEPS\n{'─'*40}\n")
        f.write(f"1. Open apply URL: {job.get('url', 'N/A')}\n")
        f.write(f"2. Create account / log in if needed\n")
        f.write(f"3. Upload: {os.path.basename(resume_path)}\n")
        f.write(f"4. Cover letter: {os.path.basename(cl_path)}\n")
        f.write(f"5. Submit and mark as applied\n")

    print(f"  📦 Manual package ready: {package_dir}")
    return package_dir, resume_path, cl_path


# ─────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    test_jd = """
    We are looking for a Machine Learning Engineer to join our AI team.
    Required skills: Python, scikit-learn, XGBoost, SQL, feature engineering,
    model evaluation, NLP. LLMs, LangChain, RAG pipelines is a strong plus.
    3+ years of experience required.
    """
    result = tailor_resume(test_jd, "TestCompany", "ML Engineer")
    print(f"\n🎯 Resume version : {result['resume_version']}")
    print(f"📊 Final ATS Score: {result['ats_score']}%")
    print(f"✅ Matched        : {result['matched_keywords']}")
    print(f"❌ Missing        : {result['missing_keywords']}")
    print(f"📄 Saved to       : {result['pdf_path']}")
