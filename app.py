import os
import sys
import urllib.parse
import urllib.request
import urllib.error
import json
import secrets
import base64
import html

from flask import Flask, redirect, request, session, render_template
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix


# =========================================================
# BASE DIRECTORY
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PROJECT_ROOT = os.path.dirname(BASE_DIR)

sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, BASE_DIR)


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv(
    os.path.join(PROJECT_ROOT, ".env")
)

load_dotenv(
    os.path.join(BASE_DIR, ".env")
)


# =========================================================
# DATABASE
# =========================================================

import database


try:
    database.setup_database()
    print("✅ Database initialized successfully.")
except Exception as error:
    print("❌ Database initialization failed:")
    print(error)


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)


# =========================================================
# RENDER PROXY
# =========================================================

app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,
    x_proto=1,
    x_host=1
)


# =========================================================
# SECRET KEY
# =========================================================

app.secret_key = os.getenv(
    "PORTAL_SECRET_KEY",
    secrets.token_hex(32)
)


# =========================================================
# DISCORD OAUTH
# =========================================================

DISCORD_CLIENT_ID = os.getenv(
    "DISCORD_CLIENT_ID"
)

DISCORD_CLIENT_SECRET = os.getenv(
    "DISCORD_CLIENT_SECRET"
)

REDIRECT_URI = os.getenv(
    "DISCORD_REDIRECT_URI",
    "https://creativexfame-bot.onrender.com/callback"
)

DISCORD_AUTHORIZE_URL = (
    "https://discord.com/oauth2/authorize"
)

DISCORD_TOKEN_URL = (
    "https://discord.com/api/oauth2/token"
)

DISCORD_USER_URL = (
    "https://discord.com/api/users/@me"
)


# =========================================================
# HELPER
# =========================================================

def safe_text(value):
    if value is None:
        return ""

    return html.escape(
        str(value)
    )


def error_page(title, message):
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>CreativeXfame</title>

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1"
        >

        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #f5f5f5;
                margin: 0;
                padding: 30px;
            }}

            .box {{
                max-width: 650px;
                margin: 80px auto;
                background: white;
                padding: 30px;
                border-radius: 15px;
                text-align: center;
                box-shadow: 0 5px 25px rgba(0,0,0,0.08);
            }}

            a {{
                display: inline-block;
                margin-top: 20px;
                padding: 12px 20px;
                background: #5865F2;
                color: white;
                text-decoration: none;
                border-radius: 8px;
            }}

            .warning {{
                background: #fff3cd;
                padding: 15px;
                border-radius: 8px;
                margin-top: 20px;
            }}
        </style>
    </head>

    <body>

        <div class="box">

            <h2>{safe_text(title)}</h2>

            <p>
                {safe_text(message)}
            </p>

            <a href="/">
                Back to Portal
            </a>

        </div>

    </body>
    </html>
    """


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    if "discord_id" in session:
        return redirect("/accounts")

    return """
    <!DOCTYPE html>
    <html>

    <head>

        <title>CreativeXfame Portal</title>

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1"
        >

        <style>

            body {
                font-family: Arial, sans-serif;
                background: #f5f5f5;
                max-width: 800px;
                margin: 80px auto;
                padding: 20px;
                text-align: center;
            }

            .box {
                background: white;
                padding: 40px;
                border-radius: 15px;
                box-shadow: 0 5px 25px rgba(0,0,0,0.08);
            }

            button {
                padding: 14px 25px;
                font-size: 17px;
                cursor: pointer;
                border: none;
                border-radius: 8px;
                background: #5865F2;
                color: white;
            }

        </style>

    </head>

    <body>

        <div class="box">

            <h1>
                🎬 CreativeXfame Submission Portal
            </h1>

            <p>
                Login with Discord to continue.
            </p>

            <br>

            <a href="/login">
                <button>
                    🔵 Login with Discord
                </button>
            </a>

        </div>

    </body>

    </html>
    """


# =========================================================
# DISCORD LOGIN
# =========================================================

@app.route("/login")
def login():

    if not DISCORD_CLIENT_ID:
        return error_page(
            "❌ Configuration Error",
            "DISCORD_CLIENT_ID is missing from Render Environment Variables."
        )

    if not DISCORD_CLIENT_SECRET:
        return error_page(
            "❌ Configuration Error",
            "DISCORD_CLIENT_SECRET is missing from Render Environment Variables."
        )

    if not REDIRECT_URI:
        return error_page(
            "❌ Configuration Error",
            "DISCORD_REDIRECT_URI is missing."
        )

    # Create secure OAuth state
    state = secrets.token_urlsafe(32)

    session["oauth_state"] = state

    params = {
        "client_id": DISCORD_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "identify",
        "state": state
    }

    authorization_url = (
        DISCORD_AUTHORIZE_URL
        + "?"
        + urllib.parse.urlencode(params)
    )

    response = redirect(
        authorization_url
    )

    response.headers["Cache-Control"] = (
        "no-store, no-cache, must-revalidate, max-age=0"
    )

    return response


# =========================================================
# DISCORD CALLBACK
# =========================================================

@app.route(
    "/callback",
    methods=["GET"]
)
def callback():

    code = request.args.get(
        "code"
    )

    returned_state = request.args.get(
        "state"
    )

    saved_state = session.get(
        "oauth_state"
    )

    oauth_error = request.args.get(
        "error"
    )

    oauth_error_description = request.args.get(
        "error_description"
    )


    # =====================================================
    # DISCORD ERROR
    # =====================================================

    if oauth_error:

        return error_page(
            "❌ Discord Authorization Failed",
            (
                f"Error: {oauth_error}\n\n"
                f"Description: {oauth_error_description or 'No description provided.'}"
            )
        )


    # =====================================================
    # NO CODE
    # =====================================================

    if not code:

        return error_page(
            "❌ Discord Login Failed",
            "No authorization code received."
        )


    # =====================================================
    # STATE CHECK
    # =====================================================

    if (
        not returned_state
        or returned_state != saved_state
    ):

        session.pop(
            "oauth_state",
            None
        )

        return error_page(
            "❌ Security Check Failed",
            "OAuth state did not match. Please try logging in again."
        )


    session.pop(
        "oauth_state",
        None
    )


    # =====================================================
    # TOKEN REQUEST
    # =====================================================

    credentials = (
        f"{DISCORD_CLIENT_ID}:"
        f"{DISCORD_CLIENT_SECRET}"
    )

    encoded_credentials = (
        base64.b64encode(
            credentials.encode("utf-8")
        ).decode("utf-8")
    )

    token_data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }).encode("utf-8")


    token_request = urllib.request.Request(
        DISCORD_TOKEN_URL,
        data=token_data,
        headers={
            "Content-Type":
                "application/x-www-form-urlencoded",

            "Authorization":
                f"Basic {encoded_credentials}",

            "User-Agent":
                "CreativeXfame-Portal/1.0"
        },
        method="POST"
    )


    print("🔵 Discord OAuth token exchange started.")


    # =====================================================
    # IMPORTANT:
    # NO RETRY / NO SLEEP ON 429
    # =====================================================

    try:

        with urllib.request.urlopen(
            token_request,
            timeout=15
        ) as response:

            raw_response = (
                response
                .read()
                .decode("utf-8")
            )

            token_response = json.loads(
                raw_response
            )


    except urllib.error.HTTPError as e:

        try:

            error_body = (
                e.read()
                .decode("utf-8")
            )

            error_data = json.loads(
                error_body
            )

        except Exception:

            error_data = {}


        error_name = error_data.get(
            "error",
            "Unknown error"
        )

        error_description = (
            error_data.get(
                "error_description",
                error_data.get(
                    "message",
                    "No description provided."
                )
            )
        )


        # =================================================
        # DISCORD RATE LIMIT
        # =================================================

        if e.code == 429:

            retry_after = error_data.get(
                "retry_after"
            )

            print(
                "⚠️ Discord returned HTTP 429."
            )

            return error_page(
                "⚠️ Discord Rate Limit",
                (
                    "Discord is temporarily rate-limiting "
                    "the OAuth login request."
                    "\n\n"
                    f"Retry after: {retry_after or 'a short time'}"
                    "\n\n"
                    "Please wait a few minutes and try again."
                )
            ), 429


        # =================================================
        # OTHER DISCORD ERROR
        # =================================================

        return error_page(
            "❌ Token Exchange Failed",
            (
                f"HTTP Status: {e.code}\n\n"
                f"Discord Error: {error_name}\n\n"
                f"Description: {error_description}"
            )
        ), e.code


    except urllib.error.URLError as e:

        print(
            "❌ Discord connection error:",
            e
        )

        return error_page(
            "❌ Discord Connection Error",
            "Could not connect to Discord. Please try again."
        ), 502


    except Exception as e:

        print(
            "❌ Unexpected OAuth error:",
            e
        )

        return error_page(
            "❌ Unexpected Error",
            "Something went wrong while logging in."
        ), 500


    # =====================================================
    # ACCESS TOKEN
    # =====================================================

    access_token = token_response.get(
        "access_token"
    )


    if not access_token:

        return error_page(
            "❌ Access Token Missing",
            "Discord did not return an access token."
        )


    # =====================================================
    # GET DISCORD USER
    # =====================================================

    user_request = urllib.request.Request(
        DISCORD_USER_URL,
        headers={
            "Authorization":
                f"Bearer {access_token}",

            "User-Agent":
                "CreativeXfame-Portal/1.0"
        },
        method="GET"
    )


    try:

        with urllib.request.urlopen(
            user_request,
            timeout=15
        ) as response:

            user_response = (
                response
                .read()
                .decode("utf-8")
            )

            user_data = json.loads(
                user_response
            )


    except urllib.error.HTTPError as e:

        if e.code == 429:

            return error_page(
                "⚠️ Discord Rate Limit",
                "Discord is temporarily rate-limiting requests. Please wait a few minutes and try again."
            ), 429

        try:

            error_body = (
                e.read()
                .decode("utf-8")
            )

        except Exception:

            error_body = "Unknown Discord error."


        return error_page(
            "❌ Discord User Request Failed",
            f"HTTP Status: {e.code}\n\n{error_body}"
        ), e.code


    except Exception as e:

        print(
            "❌ Discord user request error:",
            e
        )

        return error_page(
            "❌ Discord User Error",
            "Could not retrieve your Discord account."
        ), 502


    # =====================================================
    # SAVE DISCORD USER
    # =====================================================

    discord_user_id = user_data.get(
        "id"
    )


    if not discord_user_id:

        return error_page(
            "❌ Discord User ID Missing",
            "Could not retrieve your Discord account."
        )


    session["discord_id"] = str(
        discord_user_id
    )

    session["discord_username"] = (
        user_data.get("global_name")
        or user_data.get("username")
        or "Discord User"
    )


    print(
        "✅ Discord OAuth login successful:",
        session["discord_username"]
    )


    return redirect(
        "/accounts"
    )


# =========================================================
# ACCOUNTS
# =========================================================

@app.route("/accounts")
def accounts():

    if "discord_id" not in session:

        return redirect(
            "/login"
        )


    discord_id = session[
        "discord_id"
    ]


    print(
        "🌐 PORTAL DISCORD ID:",
        discord_id
    )


    try:

        user_accounts = (
            database.get_user_accounts(
                discord_id
            )
        )

        print(
            "🌐 PORTAL ACCOUNTS:",
            user_accounts
        )


    except Exception as error:

        print(
            "❌ Accounts database error:",
            error
        )

        return error_page(
            "❌ Database Error",
            "The database could not be loaded. Please contact the administrator."
        )


    return render_template(
        "accounts.html",
        username=session.get(
            "discord_username",
            "Discord User"
        ),
        accounts=user_accounts
    )


# =========================================================
# SUBMIT
# =========================================================

@app.route(
    "/submit",
    methods=["GET", "POST"]
)
def submit():

    if "discord_id" not in session:

        return redirect(
            "/login"
        )


    # =====================================================
    # PORTAL STATUS
    # =====================================================

    if not database.are_submissions_open():

        return """
        <!DOCTYPE html>
        <html>

        <head>
            <title>Submissions Closed</title>
        </head>

        <body>

            <div style="
                max-width:700px;
                margin:100px auto;
                text-align:center;
                font-family:Arial;
            ">

                <h1>
                    🔴 Submissions Are Closed
                </h1>

                <p>
                    The CreativeXfame submission portal
                    is currently closed.
                </p>

                <p>
                    Please wait until submissions
                    are opened again.
                </p>

            </div>

        </body>

        </html>
        """


    discord_id = session[
        "discord_id"
    ]

    discord_username = session.get(
        "discord_username",
        "Discord User"
    )


    user_accounts = (
        database.get_user_accounts(
            discord_id
        )
    )


    if not user_accounts:

        return redirect(
            "/accounts"
        )


    # =====================================================
    # GET
    # =====================================================

    if request.method == "GET":

        return render_template(
            "submit.html",
            username=discord_username,
            accounts=user_accounts,
            error=None
        )


    # =====================================================
    # SECOND STATUS CHECK
    # =====================================================

    if not database.are_submissions_open():

        return """
        <h1>
            🔴 Submissions Closed
        </h1>

        <p>
            The portal was closed before your
            submission could be completed.
        </p>
        """


    # =====================================================
    # FORM DATA
    # =====================================================

    whop_username = (
        request.form
        .get(
            "whop_username",
            ""
        )
        .strip()
    )


    google_drive_link = (
        request.form
        .get(
            "google_drive_link",
            ""
        )
        .strip()
    )


    if not whop_username:

        return render_template(
            "submit.html",
            username=discord_username,
            accounts=user_accounts,
            error="Please enter your Whop username."
        )


    if not google_drive_link:

        return render_template(
            "submit.html",
            username=discord_username,
            accounts=user_accounts,
            error="Please enter your Google Drive link."
        )


    # =====================================================
    # ACCOUNT VIEWS
    # =====================================================

    account_views = []


    try:

        for account in user_accounts:

            account_id = account[0]
            platform = account[1]
            username = account[2]

            field_name = (
                f"views_{account_id}"
            )

            raw_views = (
                request.form
                .get(
                    field_name,
                    "0"
                )
                .strip()
            )


            if raw_views == "":
                raw_views = "0"


            views = int(
                raw_views
            )


            if views < 0:
                raise ValueError


            account_views.append({
                "account_id":
                    account_id,

                "platform":
                    platform,

                "username":
                    username,

                "views":
                    views
            })


    except (
        ValueError,
        TypeError
    ):

        return render_template(
            "submit.html",
            username=discord_username,
            accounts=user_accounts,
            error=(
                "Views must be valid numbers "
                "and cannot be negative."
            )
        )


    # =====================================================
    # CREATE SUBMISSION
    # =====================================================

    try:

        submission_id = (
            database.create_submission(
                discord_id=discord_id,
                discord_username=discord_username,
                whop_username=whop_username,
                google_drive_link=google_drive_link,
                account_views=account_views
            )
        )


    except PermissionError:

        return """
        <h1>
            🔴 Submissions Closed
        </h1>

        <p>
            The portal is currently closed.
        </p>
        """


    except Exception as error:

        print(
            "❌ Submission error:",
            error
        )

        return render_template(
            "submit.html",
            username=discord_username,
            accounts=user_accounts,
            error=(
                "Submission failed. "
                "Please try again."
            )
        )


    # =====================================================
    # GET SUBMISSION
    # =====================================================

    try:

        submission = (
            database.get_submission(
                submission_id
            )
        )

    except Exception as error:

        print(
            "❌ Could not load submission:",
            error
        )

        submission = None


    # =====================================================
    # SUCCESS
    # =====================================================

    try:

        return render_template(
            "submission_success.html",
            submission=submission,
            username=discord_username
        )

    except Exception:

        return """
        <!DOCTYPE html>
        <html>

        <head>
            <title>Submission Successful</title>
        </head>

        <body>

            <div style="
                max-width:700px;
                margin:100px auto;
                text-align:center;
                font-family:Arial;
            ">

                <h1>
                    ✅ Submission Successful!
                </h1>

                <p>
                    Your views have been submitted successfully.
                </p>

                <a href="/accounts">
                    Back to Accounts
                </a>

            </div>

        </body>

        </html>
        """


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health")
def health():

    return "OK", 200


# =========================================================
# CALLBACK TEST
# =========================================================

@app.route("/callback-test")
def callback_test():

    return """
    <h1>
        ✅ Callback route is working
    </h1>

    <p>
        Your Flask application can receive requests
        on the callback route.
    </p>

    <p>
        Production callback:
        <strong>/callback</strong>
    </p>
    """


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            "5000"
        )
    )


    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
