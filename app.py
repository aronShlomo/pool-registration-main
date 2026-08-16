import os
import stripe

from flask import Flask, render_template, jsonify

from config import Config
from database import init_database

from routes.payment import payment_bp
from routes.booking import booking_bp
from routes.stripe_webhook import webhook_bp
from routes.admin import admin_bp
from database import remove_expired_pending_bookings
from apscheduler.schedulers.background import BackgroundScheduler
from reminder_service import send_lesson_reminders

from database import init_database
init_database()



# ==========================
# CREATE APPLICATION
# ==========================

app = Flask(
    __name__,
    template_folder="templates",          # <-- REQUIRED for approval email templates
    static_folder="static"
)

app.config.from_object(Config)
app.config["SECRET_KEY"] = Config.SECRET_KEY


# Stripe
stripe.api_key = Config.STRIPE_SECRET_KEY

remove_expired_pending_bookings()


# ==========================
# DATABASE
# ==========================

init_database()


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

if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    scheduler.start()


# ==========================
# BLUEPRINTS
# ==========================

app.register_blueprint(payment_bp)
app.register_blueprint(booking_bp)        # <-- booking_bp now includes approve/reject/pay-now/pay-later
app.register_blueprint(webhook_bp)
app.register_blueprint(admin_bp)


# ==========================
# HOME
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
# ERRORS
# ==========================

@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(error):
    return render_template("500.html"), 500


# ==========================
# RUN
# ==========================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )
