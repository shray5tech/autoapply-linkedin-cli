from resume_tailor import tailor_resume
from config import MOCK_MODE

print(f"MOCK_MODE is: {MOCK_MODE}")

# Test with dummy data
result = tailor_resume(
    jd_text="Test job description for ML Engineer role",
    company_name="Test Company",
    job_title="ML Engineer"
)

print("Result:", result)
print("PDF path:", result.get("pdf_path"))
print("ATS score:", result.get("ats_score"))
