# ============================================================
# MILLROD SWIM ACADEMY - EMAIL-ONLY ADMIN 2FA
# ============================================================
#
# Login flow:
#
#   Username
#       ↓
#   Password
#       ↓
#   6-digit code sent to OWNER_EMAIL
#       ↓
#   Verify code
#       ↓
#   Admin dashboard
#
# Security:
#
#   - Verification code expires after 10 minutes
#   - Maximum 5 incorrect code attempts
#   - Resend cooldown: 60 seconds
#   - Admin session starts after successful 2FA
#   - admin_last_activity is stored for the 5-minute
#     inactivity timeout enforced by app.py
#   - No phone/Twilio authentication
#
# ============================================================


import hashlib
import hmac
import secrets
import time

import resend

from functools import wraps

from flask import (
    Blueprint,
    current_app,
    redirect,
    render_template,
    request,
    session,
)

from config import Config


# ============================================================
# BLUEPRINT
# ============================================================

admin_auth_bp = Blueprint(
    "admin_auth",
    __name__,
    url_prefix="/admin",
)


# ============================================================
# SECURITY SETTINGS
# ============================================================

# Email verification code lifetime.
CODE_TTL_SECONDS = 10 * 60


# Minimum time between resend requests.
RESEND_COOLDOWN_SECONDS = 60


# Maximum incorrect verification attempts.
MAX_VERIFY_ATTEMPTS = 5


# Admin dashboard inactivity period.
#
# app.py performs the real server-side enforcement.
#
# admin.js displays the visible countdown.
ADMIN_SESSION_TIMEOUT_SECONDS = 5 * 60


# ============================================================
# TEMPORARY 2FA STORAGE
# ============================================================
#
# This stores the current verification attempt.
#
# NOTE:
# For a single-admin/local deployment this is acceptable.
# If the application later runs multiple Render workers,
# move this to Redis/database storage so every worker shares
# the same verification state.
# ============================================================

_pending_2fa = {}


# ============================================================
# OWNER EMAIL
# ============================================================

def _owner_email():

    return (
        Config.OWNER_EMAIL
        or "themillrodswim@gmail.com"
    ).strip()


# ============================================================
# HASH VERIFICATION CODE
# ============================================================

def _hash_code(code):

    secret = (
        Config.SECRET_KEY
        or "change-this-secret-key"
    ).encode("utf-8")


    return hmac.new(
        secret,
        code.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


# ============================================================
# GENERATE 6-DIGIT CODE
# ============================================================

def _new_code():

    return f"{secrets.randbelow(1_000_000):06d}"


# ============================================================
# MASK OWNER EMAIL
# ============================================================

def _masked_email():

    email_address = _owner_email()


    if "@" not in email_address:
        return email_address


    name, domain = (
        email_address.split(
            "@",
            1
        )
    )


    if len(name) <= 2:

        masked = (
            "•" * len(name)
        )

    else:

        masked = (
            name[:2]
            +
            "•" * (
                len(name) - 2
            )
        )


    return (
        f"{masked}@{domain}"
    )


# ============================================================
# SEND EMAIL VERIFICATION CODE
# ============================================================

def _send_code(code):

    # --------------------------------------------------------
    # RESEND API KEY
    # --------------------------------------------------------

    if not Config.RESEND_API_KEY:

        raise RuntimeError(
            "RESEND_API_KEY is not configured."
        )


    # --------------------------------------------------------
    # EMAIL FROM
    # --------------------------------------------------------

    if not Config.EMAIL_FROM:

        raise RuntimeError(
            "EMAIL_FROM is not configured."
        )


    # --------------------------------------------------------
    # CONFIGURE RESEND
    # --------------------------------------------------------

    resend.api_key = (
        Config.RESEND_API_KEY
    )


    recipient = _owner_email()


    # ========================================================
    # EMAIL HTML
    # ========================================================

    html = f"""
    <!doctype html>

    <html lang="en">

    <head>

        <meta charset="utf-8">

        <meta
            name="viewport"
            content="width=device-width,initial-scale=1"
        >

        <title>
            Millrod Swim Academy
        </title>

    </head>


    <body
        style="
            margin:0;
            padding:32px;
            background:#eef8fc;
            font-family:
                Arial,
                Helvetica,
                sans-serif;
            color:#102a43;
        "
    >

        <div
            style="
                max-width:560px;
                margin:auto;
                background:#ffffff;
                border-radius:22px;
                padding:34px;
                box-shadow:
                    0 14px 40px
                    rgba(6,59,115,.13);
            "
        >

            <!-- BRAND ICON -->

            <div
                style="
                    width:58px;
                    height:58px;
                    border-radius:16px;
                    background:#087fc1;
                    color:#ffffff;
                    text-align:center;
                    line-height:58px;
                    font-size:28px;
                "
            >
                🌊
            </div>


            <!-- TITLE -->

            <h1
                style="
                    color:#063b73;
                    margin:18px 0 6px;
                "
            >
                Millrod Swim Academy
            </h1>


            <p
                style="
                    color:#71869a;
                    margin-top:0;
                "
            >
                Administrator verification
            </p>


            <!-- MESSAGE -->

            <p>
                A sign-in attempt was made for the
                Millrod Swim Academy administrator portal.
            </p>


            <p>
                Enter the verification code below:
            </p>


            <!-- VERIFICATION CODE -->

            <div
                style="
                    text-align:center;
                    padding:22px;
                    margin:24px 0;
                    border-radius:16px;
                    background:#eef9fe;
                    color:#063b73;
                    font-size:34px;
                    font-weight:800;
                    letter-spacing:8px;
                "
            >
                {code}
            </div>


            <!-- EXPIRATION -->

            <p
                style="
                    color:#71869a;
                    font-size:14px;
                "
            >
                This code expires in 10 minutes and
                can only be used once.
            </p>


            <p
                style="
                    color:#71869a;
                    font-size:14px;
                "
            >
                If you did not try to sign in,
                you can safely ignore this email.
            </p>


            <hr
                style="
                    border:0;
                    border-top:
                        1px solid #e5eef4;
                    margin:28px 0;
                "
            >


            <!-- FOOTER -->

            <p
                style="
                    color:#9aaab7;
                    font-size:12px;
                "
            >
                Millrod Swim Academy
                • Secure Administrator Portal
            </p>

        </div>

    </body>

    </html>
    """


    # ========================================================
    # SEND WITH RESEND
    # ========================================================

    return resend.Emails.send({

        "from": Config.EMAIL_FROM,

        "to": [
            recipient
        ],

        "subject":
            (
                "Millrod Swim Academy "
                "administrator verification code"
            ),

        "html": html,
    })


# ============================================================
# ISSUE NEW VERIFICATION CODE
# ============================================================

def _issue_code():

    code = _new_code()


    # --------------------------------------------------------
    # Remove previous verification code
    # --------------------------------------------------------

    _pending_2fa.clear()


    # --------------------------------------------------------
    # Create new verification attempt
    # --------------------------------------------------------

    now = time.time()


    _pending_2fa.update({

        "hash":
            _hash_code(code),

        "expires_at":
            (
                now
                +
                CODE_TTL_SECONDS
            ),

        "attempts":
            0,

        "last_sent_at":
            now,
    })


    # --------------------------------------------------------
    # Send email
    # --------------------------------------------------------

    _send_code(code)


# ============================================================
# VERIFY CODE
# ============================================================

def _verify_code(code):

    # --------------------------------------------------------
    # CHECK ACTIVE CODE
    # --------------------------------------------------------

    if not _pending_2fa.get("hash"):

        return (
            False,
            "No active verification code."
        )


    # --------------------------------------------------------
    # CHECK EXPIRATION
    # --------------------------------------------------------

    if (
        time.time()
        >
        _pending_2fa.get(
            "expires_at",
            0
        )
    ):

        _pending_2fa.clear()

        return (
            False,
            "Your verification code has expired."
        )


    # --------------------------------------------------------
    # CHECK ATTEMPTS
    # --------------------------------------------------------

    attempts = _pending_2fa.get(
        "attempts",
        0
    )


    if attempts >= MAX_VERIFY_ATTEMPTS:

        return (
            False,
            "Too many incorrect attempts. "
            "Request a new code."
        )


    # --------------------------------------------------------
    # HASH SUPPLIED CODE
    # --------------------------------------------------------

    supplied_hash = _hash_code(
        code
    )


    # --------------------------------------------------------
    # SECURE COMPARISON
    # --------------------------------------------------------

    if not hmac.compare_digest(
        _pending_2fa["hash"],
        supplied_hash,
    ):

        _pending_2fa["attempts"] = (
            attempts + 1
        )


        remaining = (
            MAX_VERIFY_ATTEMPTS
            -
            _pending_2fa["attempts"]
        )


        if remaining <= 0:

            return (
                False,
                "Too many incorrect attempts. "
                "Request a new code."
            )


        return (
            False,
            (
                f"Incorrect code. "
                f"{remaining} attempt(s) remaining."
            )
        )


    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    return (
        True,
        ""
    )


# ============================================================
# ADMIN LOGIN
# ============================================================

@admin_auth_bp.route(
    "/login",
    methods=["GET", "POST"],
)
def admin_login():

    # --------------------------------------------------------
    # ALREADY AUTHENTICATED
    # --------------------------------------------------------

    if session.get(
        "admin_authenticated"
    ) is True:

        return redirect(
            "/admin/"
        )


    error = None


    # ========================================================
    # POST LOGIN
    # ========================================================

    if request.method == "POST":

        username = (
            request.form
            .get(
                "username",
                ""
            )
            .strip()
        )


        password = (
            request.form
            .get(
                "password",
                ""
            )
        )


        # ----------------------------------------------------
        # USERNAME CHECK
        # ----------------------------------------------------

        username_ok = hmac.compare_digest(
            username,
            str(
                Config.ADMIN_USERNAME
                or ""
            )
        )


        # ----------------------------------------------------
        # PASSWORD CHECK
        # ----------------------------------------------------

        password_ok = hmac.compare_digest(
            password,
            str(
                Config.ADMIN_PASSWORD
                or ""
            )
        )


        # ====================================================
        # CORRECT LOGIN
        # ====================================================

        if username_ok and password_ok:

            try:

                _issue_code()


            except Exception:

                current_app.logger.exception(
                    "ADMIN 2FA EMAIL ERROR"
                )


                error = (
                    "Your login details are correct, "
                    "but we could not send the "
                    "verification email. "
                    "Check your Resend configuration."
                )


            else:

                # ------------------------------------------------
                # CLEAR ANY OLD SESSION
                # ------------------------------------------------

                session.clear()


                # ------------------------------------------------
                # SESSION IS PERMANENT
                # ------------------------------------------------

                session.permanent = True


                # ------------------------------------------------
                # MARK 2FA AS PENDING
                # ------------------------------------------------

                session[
                    "admin_2fa_pending"
                ] = True


                # ------------------------------------------------
                # GO TO VERIFICATION PAGE
                # ------------------------------------------------

                return redirect(
                    "/admin/verify"
                )


        # ====================================================
        # INCORRECT LOGIN
        # ====================================================

        else:

            error = (
                "Invalid username or password."
            )


    # ========================================================
    # RENDER LOGIN PAGE
    # ========================================================

    return render_template(
        "login.html",
        error=error,
    )


# ============================================================
# VERIFY EMAIL CODE
# ============================================================

@admin_auth_bp.route(
    "/verify",
    methods=["GET", "POST"],
)
def verify_2fa():

    # --------------------------------------------------------
    # ALREADY AUTHENTICATED
    # --------------------------------------------------------

    if session.get(
        "admin_authenticated"
    ) is True:

        return redirect(
            "/admin/"
        )


    # --------------------------------------------------------
    # CHECK PENDING 2FA
    # --------------------------------------------------------

    if not session.get(
        "admin_2fa_pending"
    ):

        return redirect(
            "/admin/login"
        )


    error = None


    # ========================================================
    # POST VERIFICATION
    # ========================================================

    if request.method == "POST":

        code = (
            request.form
            .get(
                "code",
                ""
            )
            .strip()
        )


        # ----------------------------------------------------
        # CODE FORMAT
        # ----------------------------------------------------

        if (
            not code.isdigit()
            or len(code) != 6
        ):

            error = (
                "Enter the 6-digit "
                "verification code."
            )


        else:

            # ------------------------------------------------
            # VERIFY CODE
            # ------------------------------------------------

            valid, message = (
                _verify_code(code)
            )


            # =================================================
            # SUCCESSFUL VERIFICATION
            # =================================================

            if valid:

                # ------------------------------------------------
                # Remove temporary 2FA information
                # ------------------------------------------------

                _pending_2fa.clear()


                # ------------------------------------------------
                # Create a fresh authenticated session
                # ------------------------------------------------

                session.clear()


                session.permanent = True


                # ------------------------------------------------
                # ADMIN AUTHENTICATED
                # ------------------------------------------------

                session[
                    "admin_authenticated"
                ] = True


                session[
                    "admin_2fa_verified"
                ] = True


                # ------------------------------------------------
                # START 5-MINUTE INACTIVITY TIMER
                # ------------------------------------------------
                #
                # app.py is responsible for enforcing the
                # timeout on the server.
                #
                # admin.js displays the visible countdown.
                # ------------------------------------------------

                session[
                    "admin_last_activity"
                ] = time.time()


                # ------------------------------------------------
                # ADMIN DASHBOARD
                # ------------------------------------------------

                return redirect(
                    "/admin/"
                )


            # =================================================
            # INVALID CODE
            # =================================================

            error = message


    # ========================================================
    # VERIFICATION PAGE
    # ========================================================

    return render_template(
        "verify_2fa.html",
        error=error,
        email_hint=_masked_email(),
    )


# ============================================================
# RESEND VERIFICATION CODE
# ============================================================

@admin_auth_bp.route(
    "/resend-code",
    methods=["POST"],
)
def resend_code():

    # --------------------------------------------------------
    # MUST HAVE PENDING 2FA
    # --------------------------------------------------------

    if not session.get(
        "admin_2fa_pending"
    ):

        return redirect(
            "/admin/login"
        )


    # --------------------------------------------------------
    # CHECK RESEND COOLDOWN
    # --------------------------------------------------------

    elapsed = (
        time.time()
        -
        _pending_2fa.get(
            "last_sent_at",
            0
        )
    )


    if (
        elapsed
        <
        RESEND_COOLDOWN_SECONDS
    ):

        remaining = max(
            1,
            int(
                RESEND_COOLDOWN_SECONDS
                -
                elapsed
            ),
        )


        return render_template(
            "verify_2fa.html",

            error=(
                f"Please wait {remaining} "
                "second(s) before requesting "
                "another code."
            ),

            email_hint=_masked_email(),
        )


    # ========================================================
    # ISSUE NEW CODE
    # ========================================================

    try:

        _issue_code()


    except Exception:

        current_app.logger.exception(
            "ADMIN 2FA RESEND ERROR"
        )


        return render_template(
            "verify_2fa.html",

            error=(
                "We could not send a new code. "
                "Please try again."
            ),

            email_hint=_masked_email(),
        )


    # ========================================================
    # RETURN TO VERIFY PAGE
    # ========================================================

    return redirect(
        "/admin/verify"
    )


# ============================================================
# LOGOUT
# ============================================================

@admin_auth_bp.route(
    "/logout"
)
def admin_logout():

    # --------------------------------------------------------
    # Remove pending verification
    # --------------------------------------------------------

    _pending_2fa.clear()


    # --------------------------------------------------------
    # Destroy entire session
    # --------------------------------------------------------

    session.clear()


    # --------------------------------------------------------
    # Return to login
    # --------------------------------------------------------

    return redirect(
        "/admin/login"
    )


# ============================================================
# OPTIONAL ADMIN DECORATOR
# ============================================================

def admin_required(view):

    @wraps(view)
    def wrapped(
        *args,
        **kwargs
    ):

        # ----------------------------------------------------
        # AUTHENTICATION CHECK
        # ----------------------------------------------------

        if session.get(
            "admin_authenticated"
        ) is not True:

            return redirect(
                "/admin/login"
            )


        # ----------------------------------------------------
        # UPDATE ACTIVITY TIMESTAMP
        # ----------------------------------------------------
        #
        # app.py performs the main server-side timeout check.
        # This decorator also keeps the timestamp current for
        # routes that explicitly use @admin_required.
        # ----------------------------------------------------

        session[
            "admin_last_activity"
        ] = time.time()


        session.permanent = True


        # ----------------------------------------------------
        # RUN VIEW
        # ----------------------------------------------------

        return view(
            *args,
            **kwargs
        )


    return wrapped