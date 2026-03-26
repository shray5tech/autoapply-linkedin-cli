import os
import json
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import GEMINI_API_KEY, PROFILE_PATH, COVER_LETTERS_DIR, MOCK_MODE
from spend_watchdog import check_spend_limit, log_api_call
from google import genai
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from reportlab.lib import colors

client = genai.Client(api_key=GEMINI_API_KEY)

def load_profile():
    with open(PROFILE_PATH, "r") as f:
        return json.load(f)

def generate_cover_letter(jd_text, company_name, job_title, jd_analysis):
    if not MOCK_MODE and not check_spend_limit():
        raise Exception("Daily API spend limit reached.")
    
    if MOCK_MODE:
        print("  🧪 MOCK_MODE - Generating dummy cover letter")
        cover_text = (
            f"MOCK COVER LETTER for {company_name} - {job_title}\n\n"
            "This is a dummy cover letter generated in MOCK_MODE for testing AutoApply."
        )
        
        # Generate PDF with dummy content
        profile = load_profile()
        pdf_path = generate_pdf(cover_text, profile, company_name, job_title)
        
        return cover_text

    # Original Gemini logic (only runs when not MOCK_MODE)
    profile = load_profile()
    p = profile["personal"]
    exp = profile["experience"][0]
    projects = profile["projects"]

    # Tone based on company type
    tone_map = {
        "startup": "conversational, enthusiastic, direct",
        "mid-size": "professional yet personable",
        "enterprise": "formal, structured, achievement-focused",
        "bank": "formal, compliance-aware, metrics-driven",
        "GCC": "formal, structured, global-mindset"
    }
    tone = tone_map.get(jd_analysis.get("company_type", "enterprise"), "professional")

    prompt = f"""Write a professional cover letter for a job application.

Candidate: {p["name"]}
Applying for: {job_title} at {company_name}
Tone: {tone}

Candidate background:
- {exp["duration"]} at {exp["company"]} as {exp["title"]}
- Key achievement: Improved VIBE scores from 78% to 81%, reduced call handling time from 370s to 350s using ML
- Built SupportAI: RAG-based chatbot using Gemini, LangChain, ChromaDB
- Built Churn Prediction model: 84.7% ROC-AUC, $259K business impact, Flask API deployed
- Skills: {", ".join(profile["skills"][:12])}

Job Description:
{jd_text}

JD Keywords to reference naturally: {", ".join(jd_analysis.get("keywords", [])[:6])}

RULES:
- Exactly 4 paragraphs
- Under 300 words total
- Paragraph 1: Why THIS specific company and role (reference something specific from the JD)
- Paragraph 2: Most relevant experience for this role (quantified)
- Paragraph 3: Most relevant project (SupportAI or Churn — pick the most relevant to this JD)
- Paragraph 4: Call to action (confident, not desperate)
- Never use generic phrases like "I am writing to apply" or "I believe I am a great fit"
- No placeholders, no brackets, write the full letter ready to send
- Do NOT include date, address headers, or "Dear Hiring Manager" — start directly with paragraph 1

Return ONLY the 4 paragraphs, nothing else."""

    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    tokens = response.usage_metadata.total_token_count if response.usage_metadata else 0
    cost = (tokens / 1000) * 0.008
    log_api_call(tokens, cost)

    return response.text.strip()

def generate_pdf(cover_letter_text, profile, company_name, job_title):
    os.makedirs(COVER_LETTERS_DIR, exist_ok=True)
    safe_company = company_name.replace(" ", "_").replace("/", "_")
    safe_role = job_title.replace(" ", "_").replace("/", "_")
    filename = f"CoverLetter_Shray_Bisht_{safe_company}_{safe_role}.pdf"
    filepath = os.path.join(COVER_LETTERS_DIR, filename)

    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            rightMargin=25*mm, leftMargin=25*mm,
                            topMargin=25*mm, bottomMargin=25*mm)
    story = []

    # Styles
    header_style = ParagraphStyle('header', fontSize=13, fontName='Helvetica-Bold',
                                  spaceAfter=6, leading=18,
                                  textColor=colors.HexColor('#1a1a2e'))
    contact_style = ParagraphStyle('contact', fontSize=9, fontName='Helvetica',
                                   spaceAfter=20, leading=14,
                                   textColor=colors.HexColor('#555555'))
    body_style = ParagraphStyle('body', fontSize=10, fontName='Helvetica',
                                spaceAfter=12, leading=16, alignment=TA_JUSTIFY,
                                textColor=colors.HexColor('#222222'))
    sign_style = ParagraphStyle('sign', fontSize=10, fontName='Helvetica-Bold',
                                spaceBefore=16, textColor=colors.HexColor('#1a1a2e'))

    p = profile["personal"]

    # Header
    story.append(Paragraph(p["name"], header_style))
    story.append(Paragraph(
        f'{p["phone"]}  |  {p["email"]}  |  '
        f'<a href="{p["linkedin"]}"><u>LinkedIn</u></a>  |  '
        f'<a href="{p["github"]}"><u>GitHub</u></a>',
        contact_style))

    # Body — split into paragraphs
    paragraphs = [p.strip() for p in cover_letter_text.split('\n\n') if p.strip()]
    for para in paragraphs:
        story.append(Paragraph(para, body_style))

    # Closing
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph("Sincerely,", body_style))
    story.append(Paragraph(p["name"], sign_style))

    doc.build(story)
    print(f"✅ Cover letter PDF saved: {filepath}")
    return filepath

def create_cover_letter(jd_text, company_name, job_title, jd_analysis):
    print(f"✍️ Writing cover letter for {job_title} at {company_name}...")
    profile = load_profile()

    cover_letter_text = generate_cover_letter(jd_text, company_name, job_title, jd_analysis)
    word_count = len(cover_letter_text.split())
    print(f"📝 Cover letter generated — {word_count} words")

    pdf_path = generate_pdf(cover_letter_text, profile, company_name, job_title)

    return {
        "pdf_path": pdf_path,
        "text": cover_letter_text,
        "word_count": word_count
    }

if __name__ == "__main__":
    test_jd = """
    We are looking for a Machine Learning Engineer to join our AI team.
    You will build and deploy ML models, work with large datasets, and develop 
    data pipelines. Required skills: Python, scikit-learn, XGBoost, SQL, 
    feature engineering, model evaluation, and experience with NLP.
    Experience with LLMs, LangChain, or RAG pipelines is a strong plus.
    3+ years of experience required.
    """
    test_jd_analysis = {
        "keywords": ["Python", "scikit-learn", "XGBoost", "SQL", "NLP", "LangChain"],
        "role_type": "ML Engineer",
        "company_type": "enterprise",
        "seniority": "Mid",
        "responsibilities": ["Build ML models", "Develop data pipelines", "Work with large datasets"]
    }
    result = create_cover_letter(test_jd, "TestCompany", "ML Engineer", test_jd_analysis)
    print(f"\n📄 Saved to: {result['pdf_path']}")
    print(f"📝 Word count: {result['word_count']}")
    
