import os

import stripe

from flask import (
    Flask,
    render_template,
    jsonify
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

    # Do not hide the error.
    #
    # Render should show the actual database problem
    # in the deployment logs.

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
#
# IMPORTANT:
#
# Render/Gunicorn can run multiple workers.
#
# If every worker starts APScheduler, the same reminder
# could potentially be sent multiple times.
#
# Therefore the scheduler is controlled with:
#
# ENABLE_SCHEDULER=true
#
# For a Render service dedicated to one application process,
# enable it.
#
# If you later use multiple Gunicorn workers, move scheduled
# jobs to a separate worker/service or external scheduler.
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
    # DAILY REMINDER
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
    # EXPIRED PENDING BOOKINGS
    # --------------------------------------------------------

    scheduler.add_job(

        func=lambda: remove_expired_pending_bookings(
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
# ENABLE SCHEDULER ONLY WHEN REQUESTED
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
# PAYMENT SUCCESS
# ============================================================
#
# payment.py owns the actual /payment-success route.
#
# We intentionally do NOT create another route here.
# ============================================================


# ============================================================
# PAYMENT CANCEL
# ============================================================
#
# payment.py owns the actual /payment-cancel route.
# ============================================================


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