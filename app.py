import os
import stripe

from flask import Flask, render_template, jsonify

from config import Config

# PostgreSQL initializer
from database import init_db, remove_expired_pending_bookings

# Blueprints
from routes.payment import payment_bp
from routes.booking import booking_bp
from routes.stripe_webhook import webhook_bp
from routes.admin import admin_bp

# Scheduler
from apscheduler.schedulers.background import BackgroundScheduler
from reminder_service import send_lesson_reminders


# ==========================
# CREATE APPLICATION
# ==========================

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)

app.config.from_object(Config)
app.config["SECRET_KEY"] = Config.SECRET_KEY


# ==========================
# STRIPE
# ==========================

stripe.api_key = Config.STRIPE_SECRET_KEY


# ==========================
# DATABASE INIT
# ==========================

# Remove expired pending bookings on startup
remove_expired_pending_bookings()

# Initialize PostgreSQL database + create tables
init_db()


# ==========================
# SCHEDULER
# ==========================

scheduler = BackgroundScheduler()

scheduler.add_job(
    func=send_lesson_reminders,
    trigger="cron",
    hour=9,
    minute=0
)

# Prevent scheduler from running twice in debug mode
if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    scheduler.start()


# ==========================
# BLUEPRINTS
# ==========================

app.register_blueprint(payment_bp)
app.register_blueprint(booking_bp)
app.register_blueprint(webhook_bp)
app.register_blueprint(admin_bp)


# ==========================
# ROUTES
# ==========================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/test")
def test():
    return "Millrod Swim Academy Flask Server Running!"


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "academy": Config.COMPANY_NAME
    })


# ==========================
# ERROR HANDLERS
# ==========================

@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(error):
    return render_template("500.html"), 500


# ==========================
# RUN (LOCAL ONLY)
# ==========================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )
