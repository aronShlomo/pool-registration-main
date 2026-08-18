import os
from dotenv import load_dotenv


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


class Config:

    # ========================================================
    # FLASK
    # ========================================================

    SECRET_KEY = os.getenv("SECRET_KEY")

    if not SECRET_KEY:
        SECRET_KEY = "development-only-change-this"


    # ========================================================
    # DATABASE
    # ========================================================
    #
    # Render PostgreSQL provides DATABASE_URL.
    #
    # Example:
    # postgresql://username:password@host/database
    #
    # Do NOT put the actual database URL directly in this file.
    # ========================================================

    DATABASE_URL = os.getenv("DATABASE_URL")


    # ========================================================
    # EMAIL / RESEND
    # ========================================================

    RESEND_API_KEY = os.getenv("RESEND_API_KEY")

    OWNER_EMAIL = os.getenv(
        "OWNER_EMAIL",
        "themillrodswim@gmail.com"
    )

    EMAIL_FROM = os.getenv(
        "EMAIL_FROM",
        "Millrod Swim Academy <info@millrodswim.com>"
    )


    # ========================================================
    # STRIPE
    # ========================================================

    STRIPE_SECRET_KEY = os.getenv(
        "STRIPE_SECRET_KEY"
    )

    STRIPE_PUBLISHABLE_KEY = os.getenv(
        "STRIPE_PUBLISHABLE_KEY"
    )

    STRIPE_WEBHOOK_SECRET = os.getenv(
        "STRIPE_WEBHOOK_SECRET"
    )

    CURRENCY = os.getenv(
        "CURRENCY",
        "usd"
    )


    # ========================================================
    # ADMIN LOGIN
    # ========================================================

    ADMIN_USERNAME = os.getenv(
        "ADMIN_USERNAME",
        "admin"
    )

    ADMIN_PASSWORD = os.getenv(
        "ADMIN_PASSWORD",
        "change-me"
    )


    # ========================================================
    # WEBSITE / PRODUCTION DOMAIN
    # ========================================================
    #
    # IMPORTANT:
    #
    # Local:
    # http://127.0.0.1:5000
    #
    # Render:
    # https://your-app.onrender.com
    #
    # Set DOMAIN in Render Environment Variables.
    # ========================================================

    DOMAIN = os.getenv(
        "DOMAIN",
        "http://127.0.0.1:5000"
    ).rstrip("/")


    # ========================================================
    # ENVIRONMENT
    # ========================================================

    ENVIRONMENT = os.getenv(
        "ENVIRONMENT",
        "development"
    ).lower()


    TEST_MODE = os.getenv(
        "TEST_MODE",
        "False"
    ).lower() == "true"


    # ========================================================
    # LESSON PRICES
    # ========================================================
    #
    # IMPORTANT:
    #
    # Prices are stored in CENTS.
    #
    # 8000  = $80.00
    # 30000 = $300.00
    #
    # The backend will be the final authority for pricing.
    # The browser will NEVER be trusted for the final amount.
    # ========================================================

    LESSON_PRICES = {

        "Private Lesson": {

            "Single Lesson": 8000,

            "4 Lessons Package": 30000,

            "8 Lessons Package": 56000,

            "Monthly Program": 100000,
        },


        "Semi-Private Lesson": {

            "Single Lesson": 12000,

            "4 Lessons Package": 45000,

            "8 Lessons Package": 85000,

            "Monthly Program": 150000,
        },


        "Group Lesson": {

            "Single Lesson": 6000,

            "4 Lessons Package": 22000,

            "8 Lessons Package": 40000,

            "Monthly Program": 70000,
        },
    }


    # ========================================================
    # COMPANY INFORMATION
    # ========================================================

    COMPANY_NAME = "Millrod Swim Academy"

    COMPANY_EMAIL = "info@millrodswim.com"

    COMPANY_PHONE = "(555) 555-5555"


    # ========================================================
    # APPLICATION SETTINGS
    # ========================================================

    TIMEZONE = os.getenv(
        "TIMEZONE",
        "America/New_York"
    )

    BOOKING_HOLD_MINUTES = int(
        os.getenv(
            "BOOKING_HOLD_MINUTES",
            "30"
        )
    )


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def validate_production_config():
    """
    Checks that the important production environment variables
    exist.

    This does not print secret values.
    """

    required = {
        "DATABASE_URL": Config.DATABASE_URL,
        "RESEND_API_KEY": Config.RESEND_API_KEY,
        "STRIPE_SECRET_KEY": Config.STRIPE_SECRET_KEY,
        "STRIPE_PUBLISHABLE_KEY": Config.STRIPE_PUBLISHABLE_KEY,
        "STRIPE_WEBHOOK_SECRET": Config.STRIPE_WEBHOOK_SECRET,
        "DOMAIN": Config.DOMAIN,
    }

    missing = [
        name
        for name, value in required.items()
        if not value
    ]

    return missing