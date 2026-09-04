import os
import sys
import urllib.parse
import urllib.request
import urllib.error
import json
import secrets
import base64
import html
import time

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


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv(
    os.path.join(BASE_DIR, ".env")
)


# =========================================================
# DATABASE
# =========================================================

import database


# =========================================================
# INITIALIZE DATABASE
# =========================================================

try:

    database.setup_database()

    print(
        "✅ Database initialized successfully."
    )

except Exception as error:

    print(
        "❌ Database initialization failed:"
    )

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
# DISCORD REQUEST SETTINGS
# =========================================================

DISCORD_USER_AGENT = (
    "CreativeXfame-Portal/1.0"
)

DISCORD_TIMEOUT = 15

# Maximum automatic retries for temporary 429 responses.
DISCORD_MAX_RETRIES = 3


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
# DISCORD HTTP ERROR PAGE
# =========================================================

def discord_error_page(
    status_code,
    error_name,
    description
):

    return f"""
    <!DOCTYPE html>

    <html>

    <head>

        <title>
            Discord Login Error
        </title>

        <style>

            body {{
                font-family: Arial, sans-serif;
                max-width: 700px;
                margin: 80px auto;
                padding: 20px;
                text-align: center;
            }}

            .box {{
                border: 1px solid #ddd;
                border-radius: 12px;
                padding: 30px;
            }}

            a {{
                display: inline-block;
                margin-top: 20px;
                padding: 12px 20px;
                text-decoration: none;
                border-radius: 8px;
                background: #5865F2;
                color: white;
            }}

        </style>

    </head>

    <body>

        <div class="box">

            <h2>
                ❌ Discord Login Failed
            </h2>

            <p>
                <strong>
                    HTTP Status:
                </strong>
                {safe_text(status_code)}
            </p>

            <p>
                <strong>
                    Discord Error:
                </strong>
                {safe_text(error_name)}
            </p>

            <p>
                <strong>
                    Description:
                </strong>
                {safe_text(description)}
            </p>

            {"<p><strong>⚠️ Discord rate limit detected. Please wait a few minutes before trying again.</strong></p>" if status_code == 429 else ""}

            <a href="/">
                Back to Portal
            </a>

        </div>

    </body>

    </html>
    """


# =========================================================
# DISCORD JSON REQUEST
# =========================================================

def discord_request(
    url,
    method="GET",
    data=None,
    headers=None
):

    if headers is None:

        headers = {}


    headers = dict(
        headers
    )


    headers.setdefault(
        "User-Agent",
        DISCORD_USER_AGENT
    )


    for attempt in range(
        DISCORD_MAX_RETRIES + 1
    ):

        try:

            req = urllib.request.Request(

                url,

                data=data,

                headers=headers,

                method=method

            )


            with urllib.request.urlopen(
                req,
                timeout=DISCORD_TIMEOUT
            ) as response:

                response_body = (
                    response
                    .read()
                    .decode("utf-8")
                )


                if not response_body:

                    return (
                        response.status,
                        {}
                    )


                try:

                    parsed = json.loads(
                        response_body
                    )

                except json.JSONDecodeError:

                    parsed = {
                        "raw": response_body
                    }


                return (
                    response.status,
                    parsed
                )


        except urllib.error.HTTPError as error:

            # =================================================
            # RATE LIMIT
            # =================================================

            if error.code == 429:

                retry_after = None

                try:

                    body = (
                        error.read()
                        .decode("utf-8")
                    )

                    error_data = json.loads(
                        body
                    )

                    retry_after = (
                        error_data.get(
                            "retry_after"
                        )
                    )

                except Exception:

                    pass


                # Try Retry-After header too.

                if retry_after is None:

                    header_value = (
                        error.headers.get(
                            "Retry-After"
                        )
                    )

                    if header_value:

                        try:

                            retry_after = float(
                                header_value
                            )

                        except Exception:

                            retry_after = None


                if retry_after is None:

                    retry_after = 2


                # Never sleep for an unreasonable
                # amount of time inside a web request.

                retry_after = min(
                    max(
                        float(retry_after),
                        1
                    ),
                    10
                )


                print(
                    f"⚠️ Discord rate limit "
                    f"(429). Retry after "
                    f"{retry_after}s."
                )


                if attempt < DISCORD_MAX_RETRIES:

                    time.sleep(
                        retry_after
                    )

                    continue


                return (
                    429,
                    {
                        "message":
                            "Discord API rate limit exceeded.",
                        "retry_after":
                            retry_after
                    }
                )


            # =================================================
            # OTHER HTTP ERROR
            # =================================================

            try:

                body = (
                    error.read()
                    .decode("utf-8")
                )

                error_data = json.loads(
                    body
                )

            except Exception:

                error_data = {}


            return (
                error.code,
                error_data
            )


        except Exception as error:

            print(
                "❌ Discord request error:",
                repr(error)
            )

            return (
                0,
                {
                    "message":
                        str(error)
                }
            )


    return (
        0,
        {
            "message":
                "Discord request failed."
        }
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
        <h2>
            ❌ Configuration Error
        </h2>

        <p>
            DISCORD_CLIENT_ID is missing from
            Render Environment Variables.
        </p>

        <a href="/">
            Back to Portal
        </a>
        """


    if not DISCORD_CLIENT_SECRET:

        return """
        <h2>
            ❌ Configuration Error
        </h2>

        <p>
            DISCORD_CLIENT_SECRET is missing from
            Render Environment Variables.
        </p>

        <a href="/">
            Back to Portal
        </a>
        """


    if not REDIRECT_URI:

        return """
        <h2>
            ❌ Configuration Error
        </h2>

        <p>
            DISCORD_REDIRECT_URI is missing.
        </p>

        <a href="/">
            Back to Portal
        </a>
        """


    # =====================================================
    # CREATE OAUTH STATE
    # =====================================================

    state = secrets.token_urlsafe(
        32
    )

    session["oauth_state"] = state


    # =====================================================
    # DISCORD AUTHORIZE URL
    # =====================================================

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


    oauth_error_description = (
        request.args.get(
            "error_description"
        )
    )


    # =====================================================
    # DISCORD OAUTH ERROR
    # =====================================================

    if oauth_error:

        return discord_error_page(

            400,

            oauth_error,

            oauth_error_description
            or
            "Discord authorization was not completed."

        )


    # =====================================================
    # NO CODE
    # =====================================================

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


    # =====================================================
    # REMOVE USED STATE
    # =====================================================

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

            credentials.encode(
                "utf-8"
            )

        ).decode(
            "utf-8"
        )

    )


    token_data = urllib.parse.urlencode({

        "grant_type":
            "authorization_code",

        "code":
            code,

        "redirect_uri":
            REDIRECT_URI

    }).encode(
        "utf-8"
    )


    token_headers = {

        "Content-Type":
            "application/x-www-form-urlencoded",

        "Authorization":
            f"Basic {encoded_credentials}",

        "User-Agent":
            DISCORD_USER_AGENT

    }


    print(
        "🔵 Discord OAuth token exchange started."
    )


    token_status, token_response = (
        discord_request(

            DISCORD_TOKEN_URL,

            method="POST",

            data=token_data,

            headers=token_headers

        )
    )


    # =====================================================
    # TOKEN RATE LIMIT
    # =====================================================

    if token_status == 429:

        print(
            "⚠️ Discord token endpoint "
            "returned HTTP 429."
        )


        return discord_error_page(

            429,

            "Rate Limited",

            "Discord is temporarily rate-limiting "
            "the portal. Please wait a few minutes "
            "and try logging in again."

        )


    # =====================================================
    # TOKEN OTHER ERROR
    # =====================================================

    if token_status < 200 or token_status >= 300:

        error_name = (
            token_response.get(
                "error",
                "Unknown error"
            )
            if isinstance(
                token_response,
                dict
            )
            else
            "Unknown error"
        )


        error_description = (

            token_response.get(
                "error_description",

                token_response.get(
                    "message",
                    "No description provided."
                )

            )

            if isinstance(
                token_response,
                dict
            )

            else
            "No description provided."

        )


        print(
            "❌ Discord token exchange failed:",
            token_status,
            token_response
        )


        return discord_error_page(

            token_status,

            error_name,

            error_description

        )


    # =====================================================
    # ACCESS TOKEN
    # =====================================================

    access_token = (

        token_response.get(
            "access_token"
        )

        if isinstance(
            token_response,
            dict
        )

        else
        None

    )


    if not access_token:

        return """
        <h2>
            ❌ Access Token Missing
        </h2>

        <p>
            Discord did not return an access token.
        </p>

        <a href="/">
            Back to Portal
        </a>
        """


    # =====================================================
    # GET DISCORD USER
    # =====================================================

    user_headers = {

        "Authorization":
            f"Bearer {access_token}",

        "User-Agent":
            DISCORD_USER_AGENT

    }


    print(
        "🔵 Requesting Discord user information."
    )


    user_status, user_data = (
        discord_request(

            DISCORD_USER_URL,

            method="GET",

            headers=user_headers

        )
    )


    # =====================================================
    # USER RATE LIMIT
    # =====================================================

    if user_status == 429:

        print(
            "⚠️ Discord user endpoint "
            "returned HTTP 429."
        )


        return discord_error_page(

            429,

            "Rate Limited",

            "Discord is temporarily rate-limiting "
            "the portal. Please wait a few minutes "
            "and try logging in again."

        )


    # =====================================================
    # USER OTHER ERROR
    # =====================================================

    if user_status < 200 or user_status >= 300:

        error_message = (

            user_data.get(
                "message",
                "Could not retrieve Discord user."
            )

            if isinstance(
                user_data,
                dict
            )

            else
            "Could not retrieve Discord user."

        )


        print(
            "❌ Discord user request failed:",
            user_status,
            user_data
        )


        return discord_error_page(

            user_status,

            "User Request Failed",

            error_message

        )


    # =====================================================
    # VALIDATE USER RESPONSE
    # =====================================================

    if not isinstance(
        user_data,
        dict
    ):

        return """
        <h2>
            ❌ Discord User Error
        </h2>

        <p>
            Invalid response received from Discord.
        </p>

        <a href="/">
            Back to Portal
        </a>
        """


    # =====================================================
    # SAVE DISCORD USER
    # =====================================================

    discord_user_id = (
        user_data.get(
            "id"
        )
    )


    if not discord_user_id:

        return """
        <h2>
            ❌ Discord User ID Missing
        </h2>

        <p>
            Could not retrieve your Discord account.
        </p>

        <a href="/">
            Back to Portal
        </a>
        """


    session["discord_id"] = str(
        discord_user_id
    )


    session["discord_username"] = (

        user_data.get(
            "global_name"
        )

        or

        user_data.get(
            "username"
        )

        or

        "Discord User"

    )


    print(
        "✅ Discord login successful:",
        discord_user_id
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


        return """
        <h2>
            ❌ Database Error
        </h2>

        <p>
            The database could not be loaded.
        </p>

        <p>
            Please contact the administrator.
        </p>
        """


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

            <title>
                Submissions Closed
            </title>

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
