import sqlite3
conn = sqlite3.connect("database/autoapply.db")
deleted = conn.execute("DELETE FROM applications WHERE status='Discovered'")
conn.commit()
conn.close()
print(f"✅ DB cleared — {deleted.rowcount} rows deleted")
