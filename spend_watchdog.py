import sqlite3
import os
from datetime import date
from plyer import notification
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH, MAX_API_SPEND_INR

def get_today():
    return str(date.today())

def init_today(cursor):
    cursor.execute("""
        INSERT OR IGNORE INTO api_spend (date, calls_made, tokens_used, spend_inr, status)
        VALUES (?, 0, 0, 0.0, 'active')
    """, (get_today(),))

def get_today_spend():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    init_today(cursor)
    conn.commit()
    cursor.execute("SELECT spend_inr, status FROM api_spend WHERE date = ?", (get_today(),))
    row = cursor.fetchone()
    conn.close()
    return row[0], row[1]  # spend_inr, status

def log_api_call(tokens_used, spend_inr):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    init_today(cursor)
    cursor.execute("""
        UPDATE api_spend
        SET calls_made = calls_made + 1,
            tokens_used = tokens_used + ?,
            spend_inr = spend_inr + ?
        WHERE date = ?
    """, (tokens_used, spend_inr, get_today()))
    conn.commit()
    conn.close()

def check_spend_limit():
    spend, status = get_today_spend()
    if status == 'paused':
        print(f"⛔ Daily limit reached. Spend today: ₹{spend:.2f}. Waiting for approval.")
        return False
    if spend >= MAX_API_SPEND_INR:
        pause_spending()
        return False
    return True

def pause_spending():
    spend, _ = get_today_spend()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE api_spend SET status = 'paused' WHERE date = ?", (get_today(),))
    conn.commit()
    conn.close()
    notification.notify(
        title="⛔ AutoApply — API Limit Reached",
        message=f"Daily spend hit ₹{spend:.2f}. All agents paused. Open dashboard to approve.",
        timeout=10
    )
    print(f"⛔ PAUSED — Daily API spend hit ₹{spend:.2f}. Approve in dashboard to continue.")

def approve_resume():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE api_spend SET status = 'approved' WHERE date = ?", (get_today(),))
    conn.commit()
    conn.close()
    print("✅ Spending approved. Agents can resume.")

if __name__ == "__main__":
    print(f"Today's spend: ₹{get_today_spend()[0]:.2f}")
    print(f"Limit check: {'✅ OK' if check_spend_limit() else '⛔ Paused'}")
