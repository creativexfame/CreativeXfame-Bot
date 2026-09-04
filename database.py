import os
from datetime import datetime, timedelta

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Set the Supabase PostgreSQL connection string "
        "in your local .env and in Render Environment Variables."
    )

try:
    import psycopg2
except ImportError as e:
    raise RuntimeError(
        "psycopg2 is not installed. Run: pip install psycopg2-binary"
    ) from e

print("🗄️ DATABASE: Supabase PostgreSQL")

def connect():
    return psycopg2.connect(DATABASE_URL)

def setup_database():
    connection = connect()
    try:
        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id SERIAL PRIMARY KEY,
                discord_id TEXT NOT NULL,
                discord_username TEXT NOT NULL,
                platform TEXT NOT NULL,
                username TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id SERIAL PRIMARY KEY,
                discord_id TEXT NOT NULL,
                discord_username TEXT NOT NULL,
                whop_username TEXT NOT NULL,
                google_drive_link TEXT NOT NULL,
                total_views INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'Pending',
                created_at TEXT NOT NULL,
                week_start TEXT,
                payout TEXT,
                reviewed_at TEXT,
                reviewed_by TEXT,
                decline_reason TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS submission_accounts (
                id SERIAL PRIMARY KEY,
                submission_id INTEGER NOT NULL,
                account_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                username TEXT NOT NULL,
                views INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (submission_id) REFERENCES submissions(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        cursor.execute("""
            INSERT INTO settings (key, value)
            VALUES ('submissions_open', '1')
            ON CONFLICT (key) DO NOTHING
        """)

        connection.commit()
        print("✅ PostgreSQL database setup completed!")
    except Exception as error:
        connection.rollback()
        print("❌ Database setup error:", error)
        raise
    finally:
        connection.close()

def add_account(discord_id, discord_username, platform, username):
    connection = connect()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO accounts (
                discord_id, discord_username, platform, username, created_at
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (
            str(discord_id), str(discord_username), str(platform),
            str(username), datetime.now().isoformat()
        ))
        account_id = cursor.fetchone()[0]
        connection.commit()
        print("✅ ACCOUNT SAVED:", account_id, str(discord_id), str(platform), str(username))
        return account_id
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

def get_user_accounts(discord_id):
    connection = connect()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT id, platform, username, created_at
            FROM accounts
            WHERE discord_id = %s
            ORDER BY id ASC
        """, (str(discord_id),))
        accounts = cursor.fetchall()
        print("🔎 MATCHING ACCOUNTS:", accounts)
        return accounts
    finally:
        connection.close()

def get_all_accounts():
    connection = connect()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT id, discord_id, discord_username, platform, username, created_at
            FROM accounts
            ORDER BY id ASC
        """)
        return cursor.fetchall()
    finally:
        connection.close()

def delete_account(account_id, discord_id=None):
    connection = connect()
    cursor = connection.cursor()
    try:
        if discord_id is not None:
            cursor.execute(
                "DELETE FROM accounts WHERE id = %s AND discord_id = %s",
                (int(account_id), str(discord_id))
            )
        else:
            cursor.execute(
                "DELETE FROM accounts WHERE id = %s",
                (int(account_id),)
            )
        deleted = cursor.rowcount
        connection.commit()
        return deleted
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

def get_current_week_start():
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()

def create_submission(
    discord_id, discord_username, whop_username, google_drive_link, account_views
):
    connection = connect()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "SELECT value FROM settings WHERE key = 'submissions_open'"
        )
        result = cursor.fetchone()

        if result and result[0] != "1":
            raise PermissionError("Submissions are currently closed.")

        total_views = sum(int(account["views"]) for account in account_views)

        cursor.execute("""
            INSERT INTO submissions (
                discord_id, discord_username, whop_username,
                google_drive_link, total_views, status, created_at,
                week_start, payout, reviewed_at, reviewed_by, decline_reason
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            str(discord_id), str(discord_username), str(whop_username),
            str(google_drive_link), total_views, "Pending",
            datetime.now().isoformat(), get_current_week_start(),
            None, None, None, None
        ))
        submission_id = cursor.fetchone()[0]

        for account in account_views:
            cursor.execute("""
                INSERT INTO submission_accounts (
                    submission_id, account_id, platform, username, views
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                submission_id, account["account_id"], account["platform"],
                account["username"], int(account["views"])
            ))

        connection.commit()
        return submission_id
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

def get_submission(submission_id):
    connection = connect()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT id, discord_id, discord_username, whop_username,
                   google_drive_link, total_views, status, created_at,
                   week_start, payout, reviewed_at, reviewed_by, decline_reason
            FROM submissions WHERE id = %s
        """, (int(submission_id),))
        submission = cursor.fetchone()

        if not submission:
            return None

        cursor.execute("""
            SELECT account_id, platform, username, views
            FROM submission_accounts
            WHERE submission_id = %s
            ORDER BY id ASC
        """, (int(submission_id),))
        accounts = cursor.fetchall()

        return {
            "id": submission[0],
            "discord_id": submission[1],
            "discord_username": submission[2],
            "whop_username": submission[3],
            "google_drive_link": submission[4],
            "total_views": submission[5],
            "status": submission[6],
            "created_at": submission[7],
            "week_start": submission[8],
            "payout": submission[9],
            "reviewed_at": submission[10],
            "reviewed_by": submission[11],
            "decline_reason": submission[12],
            "accounts": accounts
        }
    finally:
        connection.close()

def get_pending_submissions():
    connection = connect()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT id, discord_id, discord_username, whop_username,
                   google_drive_link, total_views, status, created_at,
                   week_start, payout, reviewed_at, reviewed_by, decline_reason
            FROM submissions WHERE status = 'Pending' ORDER BY id ASC
        """)
        return cursor.fetchall()
    finally:
        connection.close()

def get_user_submissions(discord_id):
    connection = connect()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT id, whop_username, google_drive_link, total_views,
                   status, created_at, week_start, payout, decline_reason
            FROM submissions
            WHERE discord_id = %s
            ORDER BY id DESC
        """, (str(discord_id),))
        return cursor.fetchall()
    finally:
        connection.close()

def get_all_submissions():
    connection = connect()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT id, discord_id, discord_username, whop_username,
                   google_drive_link, total_views, status, created_at,
                   week_start, payout, reviewed_at, reviewed_by, decline_reason
            FROM submissions ORDER BY id DESC
        """)
        return cursor.fetchall()
    finally:
        connection.close()

def get_submissions_by_week(week_start):
    connection = connect()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT id, discord_id, discord_username, whop_username,
                   google_drive_link, total_views, status, created_at,
                   week_start, payout, reviewed_at, reviewed_by, decline_reason
            FROM submissions
            WHERE week_start = %s
            ORDER BY id DESC
        """, (str(week_start),))
        return cursor.fetchall()
    finally:
        connection.close()

def update_submission_status(
    submission_id, status, payout=None, reviewed_by=None, decline_reason=None
):
    connection = connect()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            UPDATE submissions
            SET status = %s, payout = %s, reviewed_at = %s,
                reviewed_by = %s, decline_reason = %s
            WHERE id = %s
        """, (
            str(status), payout, datetime.now().isoformat(),
            str(reviewed_by) if reviewed_by else None,
            decline_reason, int(submission_id)
        ))
        updated = cursor.rowcount
        connection.commit()
        return updated
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

def set_submissions_status(is_open):
    connection = connect()
    cursor = connection.cursor()
    try:
        value = "1" if is_open else "0"
        cursor.execute("""
            INSERT INTO settings (key, value)
            VALUES ('submissions_open', %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """, (value,))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

def are_submissions_open():
    connection = connect()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "SELECT value FROM settings WHERE key = 'submissions_open'"
        )
        result = cursor.fetchone()
        return True if not result else result[0] == "1"
    finally:
        connection.close()

setup_database()
