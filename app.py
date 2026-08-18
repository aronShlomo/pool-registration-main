import os
from admin_auth import admin_auth_bp
import stripe

from datetime import datetime, timezone

from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    session,
    redirect,
    url_for,
)

from config import (
    Config,
    validate_production_config
)

from database import (
    init_db,
    remove_expired_pending_bookings
)

from routes.payment import payment_bp
from routes.booking import booking_bp
from routes.stripe_webhook import webhook_bp
from routes.admin import admin_bp

from apscheduler.schedulers.background import BackgroundScheduler

from reminder_service import send_lesson_reminders


# ============================================================
# APPLICATION
# ============================================================

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)


# ============================================================
# FLASK CONFIGURATION
# ============================================================

app.config.from_object(Config)

app.config["SECRET_KEY"] = Config.SECRET_KEY


# ============================================================
# ADMIN SECURITY
# ============================================================
#
# The admin dashboard automatically logs out after
# 5 minutes without activity.
#
# This is enforced SERVER-SIDE.
#
# The JavaScript timer is only the visual countdown.
# The server is the actual security protection.
# ============================================================

ADMIN_SESSION_TIMEOUT = 5 * 60


# ============================================================
# ADMIN AUTHENTICATION PATHS
# ============================================================
#
# These routes must remain accessible while the user is
# logging in or verifying the email security code.
# ============================================================

ADMIN_AUTH_PATHS = {
    "/admin/login",
    "/admin/verify",
    "/admin/resend-code",
    "/admin/logout",
}


# ============================================================
# ADMIN SESSION TIMEOUT
# ============================================================

@app.before_request
def enforce_admin_session_timeout():

    path = request.path.rstrip("/") or "/"


    # --------------------------------------------------------
    # ONLY PROTECT ADMIN ROUTES
    # --------------------------------------------------------

    if not path.startswith("/admin"):
        return None


    # --------------------------------------------------------
    # LOGIN / VERIFICATION ROUTES
    # --------------------------------------------------------
    #
    # These routes must never be blocked by the timeout.
    # --------------------------------------------------------

    if path in ADMIN_AUTH_PATHS:
        return None


    # --------------------------------------------------------
    # CHECK AUTHENTICATION
    # --------------------------------------------------------

    if session.get(
        "admin_authenticated"
    ) is not True:

        return redirect(
            url_for(
                "admin_auth.admin_login"
            )
        )


    # --------------------------------------------------------
    # CURRENT TIME
    # --------------------------------------------------------

    now = datetime.now(
        timezone.utc
    ).timestamp()


    # --------------------------------------------------------
    # LAST ADMIN ACTIVITY
    # --------------------------------------------------------

    last_activity = session.get(
        "admin_last_activity"
    )


    # --------------------------------------------------------
    # NO ACTIVITY TIMESTAMP
    # --------------------------------------------------------

    if last_activity is None:

        print(
            "ADMIN SESSION HAS NO ACTIVITY TIMESTAMP."
        )

        session.clear()

        return redirect(
            url_for(
                "admin_auth.admin_login",
                timeout=1
            )
        )


    # --------------------------------------------------------
    # CONVERT TIMESTAMP
    # --------------------------------------------------------

    try:

        last_activity = float(
            last_activity
        )

    except (
        TypeError,
        ValueError
    ):

        print(
            "INVALID ADMIN ACTIVITY TIMESTAMP."
        )

        session.clear()

        return redirect(
            url_for(
                "admin_auth.admin_login",
                timeout=1
            )
        )


    # --------------------------------------------------------
    # CALCULATE INACTIVITY
    # --------------------------------------------------------

    elapsed = (
        now -
        last_activity
    )


    # --------------------------------------------------------
    # 5 MINUTES EXPIRED
    # --------------------------------------------------------

    if elapsed >= ADMIN_SESSION_TIMEOUT:

        print(
            "ADMIN SESSION EXPIRED "
            "AFTER 5 MINUTES OF INACTIVITY."
        )

        session.clear()

        return redirect(
            url_for(
                "admin_auth.admin_login",
                timeout=1
            )
        )


    # --------------------------------------------------------
    # UPDATE LAST ACTIVITY
    # --------------------------------------------------------

    session["admin_last_activity"] = now

    return None


# ============================================================
# STRIPE
# ============================================================

stripe.api_key = Config.STRIPE_SECRET_KEY


# ============================================================
# PRODUCTION CONFIGURATION CHECK
# ============================================================

missing_config = validate_production_config()


if missing_config:

    print(
        "WARNING: Missing environment variables:"
    )

    for variable in missing_config:

        print(
            f"  - {variable}"
        )

else:

    print(
        "Production environment configuration loaded."
    )


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

try:

    init_db()

    print(
        "Database initialization completed."
    )

except Exception as database_error:

    print(
        "DATABASE STARTUP ERROR:",
        repr(database_error)
    )

    raise


# ============================================================
# REMOVE OLD PENDING BOOKINGS
# ============================================================

try:

    removed = remove_expired_pending_bookings(
        Config.BOOKING_HOLD_MINUTES
    )

    print(
        f"Startup cleanup completed. "
        f"Removed {removed} expired booking(s)."
    )

except Exception as cleanup_error:

    print(
        "BOOKING CLEANUP ERROR:",
        repr(cleanup_error)
    )


# ============================================================
# REGISTER BLUEPRINTS
# ============================================================

app.register_blueprint(
    booking_bp
)

app.register_blueprint(admin_auth_bp)

app.register_blueprint(
    payment_bp
)

app.register_blueprint(
    webhook_bp
)

app.register_blueprint(
    admin_bp
)


# ============================================================
# SCHEDULER
# ============================================================

scheduler = None


def start_scheduler():

    global scheduler


    if scheduler is not None:
        return


    scheduler = BackgroundScheduler(
        timezone=Config.TIMEZONE
    )


    # --------------------------------------------------------
    # DAILY LESSON REMINDERS
    # --------------------------------------------------------

    scheduler.add_job(

        func=send_lesson_reminders,

        trigger="cron",

        hour=9,

        minute=0,

        id="daily_lesson_reminders",

        replace_existing=True,

        max_instances=1,

        coalesce=True
    )


    # --------------------------------------------------------
    # EXPIRED BOOKING CLEANUP
    # --------------------------------------------------------

    scheduler.add_job(

        func=lambda:
            remove_expired_pending_bookings(
                Config.BOOKING_HOLD_MINUTES
            ),

        trigger="interval",

        minutes=10,

        id="expired_booking_cleanup",

        replace_existing=True,

        max_instances=1,

        coalesce=True
    )


    scheduler.start()


    print(
        "APScheduler started successfully."
    )


# ============================================================
# ENABLE SCHEDULER
# ============================================================

ENABLE_SCHEDULER = (
    os.getenv(
        "ENABLE_SCHEDULER",
        "False"
    ).lower()
    == "true"
)


if ENABLE_SCHEDULER:

    start_scheduler()

else:

    print(
        "APScheduler is disabled. "
        "Set ENABLE_SCHEDULER=True to enable scheduled jobs."
    )


# ============================================================
# HOME PAGE
# ============================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():

    return jsonify({

        "status": "ok",

        "academy": Config.COMPANY_NAME,

        "environment": Config.ENVIRONMENT
    })


# ============================================================
# SIMPLE TEST
# ============================================================

@app.route("/test")
def test():

    return (
        "Millrod Swim Academy Flask Server Running!"
    )


# ============================================================
# 404 ERROR
# ============================================================

@app.errorhandler(404)
def page_not_found(error):

    try:

        return render_template(
            "404.html"
        ), 404

    except Exception:

        return (
            "<h1>404 - Page Not Found</h1>",
            404
        )


# ============================================================
# 500 ERROR
# ============================================================

@app.errorhandler(500)
def server_error(error):

    try:

        return render_template(
            "500.html"
        ), 500

    except Exception:

        return (
            "<h1>500 - Server Error</h1>",
            500
        )


# ============================================================
# APPLICATION START
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )


    app.run(

        host="0.0.0.0",

        port=port,

        debug=(
            Config.ENVIRONMENT
            == "development"
        )
    )