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


# =========================================================
# BASE DIRECTORY
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

sys.path.insert(0, BASE_DIR)


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv(
    os.path.join(BASE_DIR, ".env")
)


import database


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)

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

REDIRECT_URI = (
    "http://127.0.0.1:5000/callback"
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


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    if "discord_id" in session:

        return redirect(
            "/accounts"
        )


    return """
    <!DOCTYPE html>
    <html>

    <head>

        <title>
            CreativeXfame Portal
        </title>

        <style>

            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 80px auto;
                padding: 20px;
                text-align: center;
            }

            button {
                padding: 14px 25px;
                font-size: 17px;
                cursor: pointer;
                border: none;
                border-radius: 8px;
            }

        </style>

    </head>

    <body>

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

    </body>

    </html>
    """


# =========================================================
# DISCORD LOGIN
# =========================================================

@app.route("/login")
def login():

    if not DISCORD_CLIENT_ID:

        return """
        <h2>❌ Configuration Error</h2>

        <p>
            DISCORD_CLIENT_ID is missing from .env
        </p>
        """


    state = secrets.token_urlsafe(32)

    session["oauth_state"] = state


    params = {

        "client_id":
            DISCORD_CLIENT_ID,

        "redirect_uri":
            REDIRECT_URI,

        "response_type":
            "code",

        "scope":
            "identify",

        "state":
            state

    }


    authorization_url = (
        DISCORD_AUTHORIZE_URL
        + "?"
        + urllib.parse.urlencode(
            params
        )
    )


    return redirect(
        authorization_url
    )


# =========================================================
# DISCORD CALLBACK
# =========================================================

@app.route("/callback")
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


    if oauth_error:

        return f"""
        <h2>
            ❌ Discord Authorization Failed
        </h2>

        <p>
            <strong>Error:</strong>
            {safe_text(oauth_error)}
        </p>

        <p>
            <strong>Description:</strong>
            {safe_text(oauth_error_description)}
        </p>

        <a href="/">
            Back to Portal
        </a>
        """


    if not code:

        return """
        <h2>
            ❌ Discord Login Failed
        </h2>

        <p>
            No authorization code received.
        </p>

        <a href="/">
            Back to Portal
        </a>
        """


    if (
        not returned_state
        or returned_state != saved_state
    ):

        return """
        <h2>
            ❌ Security Check Failed
        </h2>

        <p>
            OAuth state did not match.
        </p>

        <a href="/">
            Try Again
        </a>
        """


    session.pop(
        "oauth_state",
        None
    )


    if not DISCORD_CLIENT_ID:

        return """
        <h2>
            ❌ Client ID Missing
        </h2>
        """


    if not DISCORD_CLIENT_SECRET:

        return """
        <h2>
            ❌ Client Secret Missing
        </h2>
        """


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

        "grant_type":
            "authorization_code",

        "code":
            code,

        "redirect_uri":
            REDIRECT_URI

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


        return f"""
        <h1>
            ❌ Token Exchange Failed
        </h1>

        <p>
            HTTP Status:
            <strong>{e.code}</strong>
        </p>

        <p>
            Discord Error:
            {safe_text(error_name)}
        </p>

        <p>
            Description:
            {safe_text(error_description)}
        </p>

        <a href="/">
            Back to Portal
        </a>
        """


    except Exception as e:

        return f"""
        <h2>
            ❌ Unexpected Error
        </h2>

        <p>
            {safe_text(e)}
        </p>

        <a href="/">
            Back to Portal
        </a>
        """


    access_token = token_response.get(
        "access_token"
    )


    if not access_token:

        return """
        <h2>
            ❌ Access Token Missing
        </h2>

        <a href="/">
            Back to Portal
        </a>
        """


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


    except Exception as e:

        return f"""
        <h2>
            ❌ Discord User Error
        </h2>

        <p>
            {safe_text(e)}
        </p>

        <a href="/">
            Back to Portal
        </a>
        """


    session["discord_id"] = str(
        user_data.get("id")
    )


    session["discord_username"] = (

        user_data.get("global_name")

        or user_data.get("username")

        or "Discord User"

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


    user_accounts = (
        database.get_user_accounts(
            discord_id
        )
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

    # =====================================================
    # LOGIN CHECK
    # =====================================================

    if "discord_id" not in session:

        return redirect(
            "/login"
        )


    # =====================================================
    # IMPORTANT:
    # CHECK PORTAL STATUS EVERY TIME
    # =====================================================

    if not database.are_submissions_open():

        return """
        <!DOCTYPE html>

        <html>

        <head>

            <title>
                Submissions Closed
            </title>

            <style>

                body {
                    font-family: Arial, sans-serif;
                    max-width: 700px;
                    margin: 100px auto;
                    padding: 30px;
                    text-align: center;
                }

                .box {
                    border-radius: 12px;
                    padding: 30px;
                    border: 1px solid #ddd;
                }

                h1 {
                    color: #d32f2f;
                }

            </style>

        </head>

        <body>

            <div class="box">

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
    # POST
    # =====================================================

    # SECOND STATUS CHECK
    # Prevents submitting if portal was closed
    # between page load and button click.

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

            error=(
                "Please enter your Whop username."
            )

        )


    if not google_drive_link:

        return render_template(

            "submit.html",

            username=discord_username,

            accounts=user_accounts,

            error=(
                "Please enter your Google Drive link."
            )

        )


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
    # CREATE
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


    except Exception:

        return render_template(

            "submit.html",

            username=discord_username,

            accounts=user_accounts,

            error=(
                "Submission failed. "
                "Please try again."
            )

        )


    submission = (
        database.get_submission(
            submission_id
        )
    )


    return render_template(

        "submission_success.html",

        submission=submission,

        username=discord_username

    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )