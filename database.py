import os
import sqlite3
from datetime import datetime, timedelta


# =========================================================
# DATABASE PATH
# =========================================================

DATABASE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "CreativeXfame.db"
)

print("🗄️ DATABASE PATH:", DATABASE)

# =========================================================
# DATABASE CONNECTION
# =========================================================

def connect():
    connection = sqlite3.connect(DATABASE)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


# =========================================================
# SETUP DATABASE
# =========================================================

def setup_database():

    connection = sqlite3.connect(DATABASE)

    try:

        cursor = connection.cursor()

        cursor.execute("PRAGMA foreign_keys = OFF")

        # =====================================================
        # ACCOUNTS TABLE
        # =====================================================

        cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name = 'accounts'
        """)

        accounts_exists = cursor.fetchone() is not None

        if not accounts_exists:

            cursor.execute("""
                CREATE TABLE accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discord_id TEXT NOT NULL,
                    discord_username TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    username TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

        else:

            cursor.execute("""
                PRAGMA table_info(accounts)
            """)

            columns = [
                row[1]
                for row in cursor.fetchall()
            ]

            if "content_type" in columns:

                print("🔄 Updating accounts table...")

                cursor.execute("""
                    CREATE TABLE accounts_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        discord_id TEXT NOT NULL,
                        discord_username TEXT NOT NULL,
                        platform TEXT NOT NULL,
                        username TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                """)

                cursor.execute("""
                    INSERT INTO accounts_new (
                        id,
                        discord_id,
                        discord_username,
                        platform,
                        username,
                        created_at
                    )
                    SELECT
                        id,
                        discord_id,
                        discord_username,
                        platform,
                        username,
                        created_at
                    FROM accounts
                """)

                cursor.execute("""
                    DROP TABLE accounts
                """)

                cursor.execute("""
                    ALTER TABLE accounts_new
                    RENAME TO accounts
                """)

                print("✅ content_type removed successfully!")


        # =====================================================
        # SUBMISSIONS TABLE
        # =====================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id TEXT NOT NULL,
                discord_username TEXT NOT NULL,
                whop_username TEXT NOT NULL,
                google_drive_link TEXT NOT NULL,
                total_views INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'Pending',
                created_at TEXT NOT NULL
            )
        """)


        # =====================================================
        # CHECK SUBMISSION COLUMNS
        # =====================================================

        cursor.execute("""
            PRAGMA table_info(submissions)
        """)

        submission_columns = [
            row[1]
            for row in cursor.fetchall()
        ]


        # =====================================================
        # ADD WEEK_START
        # =====================================================

        if "week_start" not in submission_columns:

            cursor.execute("""
                ALTER TABLE submissions
                ADD COLUMN week_start TEXT
            """)

            cursor.execute("""
                SELECT id, created_at
                FROM submissions
                WHERE week_start IS NULL
            """)

            old_submissions = cursor.fetchall()

            for submission_id, created_at in old_submissions:

                try:

                    date = datetime.fromisoformat(
                        created_at
                    ).date()

                    monday = date - timedelta(
                        days=date.weekday()
                    )

                    cursor.execute("""
                        UPDATE submissions
                        SET week_start = ?
                        WHERE id = ?
                    """, (
                        monday.isoformat(),
                        submission_id
                    ))

                except Exception:
                    pass


        # =====================================================
        # ADD PAYOUT
        # =====================================================

        if "payout" not in submission_columns:

            cursor.execute("""
                ALTER TABLE submissions
                ADD COLUMN payout TEXT
            """)

            print("✅ payout column added!")


        # =====================================================
        # ADD REVIEWED_AT
        # =====================================================

        if "reviewed_at" not in submission_columns:

            cursor.execute("""
                ALTER TABLE submissions
                ADD COLUMN reviewed_at TEXT
            """)


        # =====================================================
        # ADD REVIEWED_BY
        # =====================================================

        if "reviewed_by" not in submission_columns:

            cursor.execute("""
                ALTER TABLE submissions
                ADD COLUMN reviewed_by TEXT
            """)


        # =====================================================
        # ADD DECLINE_REASON
        # =====================================================

        if "decline_reason" not in submission_columns:

            cursor.execute("""
                ALTER TABLE submissions
                ADD COLUMN decline_reason TEXT
            """)


        # =====================================================
        # SUBMISSION ACCOUNTS
        # =====================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS submission_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id INTEGER NOT NULL,
                account_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                username TEXT NOT NULL,
                views INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (submission_id)
                    REFERENCES submissions(id)
            )
        """)


        # =====================================================
        # SETTINGS
        # =====================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)


        # =====================================================
        # DEFAULT PORTAL STATUS
        # =====================================================

        cursor.execute("""
            INSERT OR IGNORE INTO settings (
                key,
                value
            )
            VALUES (
                'submissions_open',
                '1'
            )
        """)


        connection.commit()

        print("✅ Database setup completed!")

    except Exception as error:

        connection.rollback()

        print("❌ Database setup error:")
        print(error)

        raise

    finally:

        connection.close()


# =========================================================
# ADD ACCOUNT
# =========================================================

def add_account(
    discord_id,
    discord_username,
    platform,
    username
):

    connection = connect()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            INSERT INTO accounts (
                discord_id,
                discord_username,
                platform,
                username,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            str(discord_id),
            str(discord_username),
            str(platform),
            str(username),
            datetime.now().isoformat()
        ))

        connection.commit()

        return cursor.lastrowid

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


# =========================================================
# GET USER ACCOUNTS
# =========================================================

def get_user_accounts(discord_id):

    connection = connect()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            platform,
            username,
            created_at
        FROM accounts
        WHERE discord_id = ?
        ORDER BY id ASC
    """, (
        str(discord_id),
    ))

    accounts = cursor.fetchall()

    connection.close()

    return accounts


# =========================================================
# GET ALL ACCOUNTS
# =========================================================

def get_all_accounts():

    connection = connect()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            discord_id,
            discord_username,
            platform,
            username,
            created_at
        FROM accounts
        ORDER BY id ASC
    """)

    accounts = cursor.fetchall()

    connection.close()

    return accounts


# =========================================================
# DELETE ACCOUNT
# =========================================================

def delete_account(
    account_id,
    discord_id=None
):

    connection = connect()
    cursor = connection.cursor()

    try:

        if discord_id is not None:

            cursor.execute("""
                DELETE FROM accounts
                WHERE id = ?
                AND discord_id = ?
            """, (
                int(account_id),
                str(discord_id)
            ))

        else:

            cursor.execute("""
                DELETE FROM accounts
                WHERE id = ?
            """, (
                int(account_id),
            ))

        deleted = cursor.rowcount

        connection.commit()

        return deleted

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


# =========================================================
# CURRENT WEEK START
# =========================================================

def get_current_week_start():

    today = datetime.now().date()

    monday = today - timedelta(
        days=today.weekday()
    )

    return monday.isoformat()


# =========================================================
# CREATE SUBMISSION
# =========================================================

def create_submission(
    discord_id,
    discord_username,
    whop_username,
    google_drive_link,
    account_views
):

    connection = connect()
    cursor = connection.cursor()

    try:

        # IMPORTANT:
        # Do not allow creation when portal is closed.

        cursor.execute("""
            SELECT value
            FROM settings
            WHERE key = 'submissions_open'
        """)

        result = cursor.fetchone()

        if result and result[0] != "1":

            raise PermissionError(
                "Submissions are currently closed."
            )


        week_start = get_current_week_start()

        total_views = sum(
            int(account["views"])
            for account in account_views
        )


        cursor.execute("""
            INSERT INTO submissions (
                discord_id,
                discord_username,
                whop_username,
                google_drive_link,
                total_views,
                status,
                created_at,
                week_start,
                payout,
                reviewed_at,
                reviewed_by,
                decline_reason
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(discord_id),
            str(discord_username),
            str(whop_username),
            str(google_drive_link),
            total_views,
            "Pending",
            datetime.now().isoformat(),
            week_start,
            None,
            None,
            None,
            None
        ))

        submission_id = cursor.lastrowid


        for account in account_views:

            cursor.execute("""
                INSERT INTO submission_accounts (
                    submission_id,
                    account_id,
                    platform,
                    username,
                    views
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                submission_id,
                account["account_id"],
                account["platform"],
                account["username"],
                int(account["views"])
            ))


        connection.commit()

        return submission_id

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


# =========================================================
# GET SINGLE SUBMISSION
# =========================================================

def get_submission(submission_id):

    connection = connect()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            discord_id,
            discord_username,
            whop_username,
            google_drive_link,
            total_views,
            status,
            created_at,
            week_start,
            payout,
            reviewed_at,
            reviewed_by,
            decline_reason
        FROM submissions
        WHERE id = ?
    """, (
        int(submission_id),
    ))

    submission = cursor.fetchone()

    if not submission:

        connection.close()
        return None


    cursor.execute("""
        SELECT
            account_id,
            platform,
            username,
            views
        FROM submission_accounts
        WHERE submission_id = ?
        ORDER BY id ASC
    """, (
        int(submission_id),
    ))

    accounts = cursor.fetchall()

    connection.close()


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


# =========================================================
# GET PENDING SUBMISSIONS
# =========================================================

def get_pending_submissions():

    connection = connect()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            discord_id,
            discord_username,
            whop_username,
            google_drive_link,
            total_views,
            status,
            created_at,
            week_start,
            payout,
            reviewed_at,
            reviewed_by,
            decline_reason
        FROM submissions
        WHERE status = 'Pending'
        ORDER BY id ASC
    """)

    submissions = cursor.fetchall()

    connection.close()

    return submissions


# =========================================================
# GET USER SUBMISSIONS
# =========================================================

def get_user_submissions(discord_id):

    connection = connect()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            whop_username,
            google_drive_link,
            total_views,
            status,
            created_at,
            week_start,
            payout,
            decline_reason
        FROM submissions
        WHERE discord_id = ?
        ORDER BY id DESC
    """, (
        str(discord_id),
    ))

    submissions = cursor.fetchall()

    connection.close()

    return submissions


# =========================================================
# GET ALL SUBMISSIONS
# =========================================================

def get_all_submissions():

    connection = connect()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            discord_id,
            discord_username,
            whop_username,
            google_drive_link,
            total_views,
            status,
            created_at,
            week_start,
            payout,
            reviewed_at,
            reviewed_by,
            decline_reason
        FROM submissions
        ORDER BY id DESC
    """)

    submissions = cursor.fetchall()

    connection.close()

    return submissions


# =========================================================
# GET SUBMISSIONS BY WEEK
# =========================================================

def get_submissions_by_week(week_start):

    connection = connect()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            discord_id,
            discord_username,
            whop_username,
            google_drive_link,
            total_views,
            status,
            created_at,
            week_start,
            payout,
            reviewed_at,
            reviewed_by,
            decline_reason
        FROM submissions
        WHERE week_start = ?
        ORDER BY id DESC
    """, (
        str(week_start),
    ))

    submissions = cursor.fetchall()

    connection.close()

    return submissions


# =========================================================
# UPDATE SUBMISSION STATUS
# =========================================================

def update_submission_status(
    submission_id,
    status,
    payout=None,
    reviewed_by=None,
    decline_reason=None
):

    connection = connect()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            UPDATE submissions
            SET
                status = ?,
                payout = ?,
                reviewed_at = ?,
                reviewed_by = ?,
                decline_reason = ?
            WHERE id = ?
        """, (
            str(status),
            payout,
            datetime.now().isoformat(),
            str(reviewed_by) if reviewed_by else None,
            decline_reason,
            int(submission_id)
        ))

        updated = cursor.rowcount

        connection.commit()

        return updated

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


# =========================================================
# OPEN / CLOSE SUBMISSIONS
# =========================================================

def set_submissions_status(is_open):

    connection = connect()
    cursor = connection.cursor()

    try:

        value = "1" if is_open else "0"

        cursor.execute("""
            INSERT OR REPLACE INTO settings (
                key,
                value
            )
            VALUES (
                'submissions_open',
                ?
            )
        """, (
            value,
        ))

        connection.commit()

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


# =========================================================
# CHECK SUBMISSIONS STATUS
# =========================================================

def are_submissions_open():

    connection = connect()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT value
        FROM settings
        WHERE key = 'submissions_open'
    """)

    result = cursor.fetchone()

    connection.close()

    if not result:
        return True

    return result[0] == "1"
