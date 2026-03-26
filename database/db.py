import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "autoapply.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    """Initialize database with safe schema migrations"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create applications table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            app_id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_title TEXT,
            company TEXT,
            platform TEXT,
            job_external_id TEXT,
            jd_text TEXT,
            match_score REAL,
            ats_score REAL,
            easy_apply INTEGER,
            resume_path TEXT,
            cover_letter_path TEXT,
            apply_link TEXT,
            status TEXT,
            salary_range TEXT,
            applied_date TEXT,
            location TEXT,
            posted_date TEXT,
            apply_by_date TEXT,
            expected_salary TEXT,
            remote INTEGER
        )
    ''')
    
    # Create api_spend table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_spend (
            spend_id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            tokens_used INTEGER,
            cost_inr REAL,
            model TEXT
        )
    ''')
    
    # Safe migration: add new columns if they don't exist
    new_columns = [
        ('apply_by_date', 'TEXT'),
        ('expected_salary', 'TEXT'), 
        ('remote', 'INTEGER')
    ]
    
    cursor.execute("PRAGMA table_info(applications)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    
    for column_name, column_type in new_columns:
        if column_name not in existing_columns:
            print(f"  🔄 Adding column: {column_name}")
            cursor.execute(f"ALTER TABLE applications ADD COLUMN {column_name} {column_type}")
    
    # Create unique index on job_external_id if not exists
    cursor.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_job_external_id 
        ON applications(job_external_id)
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully")

def insert_job(job_data):
    """Insert a new job record with deduplication"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check for duplicate by job_external_id
    if job_data.get('job_external_id'):
        cursor.execute("SELECT app_id FROM applications WHERE job_external_id = ?", 
                    (job_data['job_external_id'],))
        if cursor.fetchone():
            conn.close()
            return None  # Duplicate found
    
    cursor.execute('''
        INSERT INTO applications (
            job_title, company, platform, jd_text, match_score, 
            job_external_id, easy_apply, salary_range, status,
            apply_by_date, expected_salary, remote
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        job_data.get('job_title'),
        job_data.get('company'),
        job_data.get('platform', 'LinkedIn'),
        job_data.get('jd_text', ''),
        job_data.get('match_score'),
        job_data.get('job_external_id'),
        job_data.get('easy_apply', 0),
        job_data.get('salary_range'),
        job_data.get('status', 'Discovered'),
        job_data.get('apply_by_date'),
        job_data.get('expected_salary'),
        job_data.get('remote', 0)
    ))
    
    app_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return app_id

def update_job_with_documents(app_id, resume_path=None, cover_letter_path=None, ats_score=None):
    """Update existing job record with generated documents and ATS score"""
    conn = get_connection()
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if resume_path:
        updates.append("resume_path = ?")
        params.append(resume_path)
    
    if cover_letter_path:
        updates.append("cover_letter_path = ?")
        params.append(cover_letter_path)
    
    if ats_score is not None:
        updates.append("ats_score = ?")
        params.append(ats_score)
    
    if updates:
        query = f"UPDATE applications SET {', '.join(updates)} WHERE app_id = ?"
        params.append(app_id)
        cursor.execute(query, params)
        conn.commit()
    
    conn.close()

if __name__ == "__main__":
    init_db()
