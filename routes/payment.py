import stripe

from flask import (
    Blueprint,
    jsonify,
    redirect,
    request,
    render_template
)

from config import Config
from database import get_db_connection

import psycopg2.extras

from email_service import (
    send_booking_confirmation,
    send_admin_notification
)


# ============================================================
# BLUEPRINT
# ============================================================

payment_bp = Blueprint(
    "payment",
    __name__
)


# ============================================================
# STRIPE CONFIGURATION
# ============================================================

stripe.api_key = Config.STRIPE_SECRET_KEY


# ============================================================
# HELPERS
# ============================================================

def get_booking(booking_id):
    """
    Retrieve one booking from PostgreSQL.
    """

    conn = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        )

        cursor.execute(
            """
            SELECT *
            FROM bookings
            WHERE id = %s
            LIMIT 1
            """,
            (booking_id,)
        )

        return cursor.fetchone()

    finally:

        if conn:
            conn.close()


def get_price_in_cents(booking):
    """
    Get the official price from Config.

    The customer's browser is never trusted for payment amount.
    """

    lesson_type = booking["lesson_type"]

    package = booking["package"]

    try:

        return Config.LESSON_PRICES[
            lesson_type
        ][
            package
        ]

    except KeyError:

        return None


# ============================================================
# PAY NOW
# ============================================================

@payment_bp.route(
    "/api/pay-now/<int:booking_id>",
    methods=["GET"]
)
def pay_now(booking_id):

    try:

        # ----------------------------------------------------
        # GET BOOKING
        # ----------------------------------------------------

        booking = get_booking(
            booking_id
        )

        if not booking:

            return (
                "<h2>Registration Not Found</h2>"
                "<p>We could not find this registration.</p>"
            ), 404


        # ----------------------------------------------------
        # CHECK APPROVAL
        # ----------------------------------------------------

        if booking["status"] != "confirmed":

            return (
                "<div style='"
                "font-family:Arial,sans-serif;"
                "max-width:600px;"
                "margin:60px auto;"
                "padding:40px;"
                "text-align:center;"
                "'>"
                "<h2>Registration Not Yet Approved</h2>"
                "<p>"
                "Your registration must be approved "
                "before payment can be completed."
                "</p>"
                "</div>"
            ), 400


        # ----------------------------------------------------
        # ALREADY PAID
        # ----------------------------------------------------

        if booking["payment_status"] == "paid":

            return (
                "<div style='"
                "font-family:Arial,sans-serif;"
                "max-width:600px;"
                "margin:60px auto;"
                "padding:40px;"
                "text-align:center;"
                "'>"
                "<div style='font-size:55px;'>✔</div>"
                "<h2>Payment Already Completed</h2>"
                "<p>"
                "This registration has already been paid."
                "</p>"
                "</div>"
            )


        # ----------------------------------------------------
        # STRIPE KEY CHECK
        # ----------------------------------------------------

        if not Config.STRIPE_SECRET_KEY:

            print(
                "STRIPE ERROR: "
                "STRIPE_SECRET_KEY is missing."
            )

            return (
                "<h2>Payment Temporarily Unavailable</h2>"
                "<p>Please contact Millrod Swim Academy.</p>"
            ), 500


        # ----------------------------------------------------
        # OFFICIAL SERVER PRICE
        # ----------------------------------------------------

        price_cents = get_price_in_cents(
            booking
        )

        if price_cents is None:

            return (
                "<h2>Payment Error</h2>"
                "<p>"
                "We could not determine the registration price."
                "</p>"
            ), 400


        # ----------------------------------------------------
        # UPDATE STORED PRICE
        # ----------------------------------------------------

        price_display = (
            f"${price_cents / 100:.2f}"
        )

        conn = None

        try:

            conn = get_db_connection()

            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE bookings
                SET price = %s
                WHERE id = %s
                """,
                (
                    price_display,
                    booking_id
                )
            )

            conn.commit()

        finally:

            if conn:
                conn.close()


        # ----------------------------------------------------
        # CREATE STRIPE CHECKOUT SESSION
        # ----------------------------------------------------

        checkout_session = stripe.checkout.Session.create(

            mode="payment",

            payment_method_types=[
                "card"
            ],

            line_items=[

                {
                    "price_data": {

                        "currency": Config.CURRENCY,

                        "product_data": {

                            "name": (
                                f"{booking['lesson_type']} "
                                f"- "
                                f"{booking['package']}"
                            ),

                            "description": (
                                f"Lesson date: "
                                f"{booking['lesson_date']} "
                                f"at "
                                f"{booking['lesson_time']}"
                            )
                        },

                        "unit_amount": price_cents
                    },

                    "quantity": 1
                }
            ],

            metadata={

                "booking_id": str(
                    booking_id
                )
            },

            customer_email=booking["email"],

            success_url=(
                f"{Config.DOMAIN}"
                f"/payment-success"
                f"?session_id={{CHECKOUT_SESSION_ID}}"
            ),

            cancel_url=(
                f"{Config.DOMAIN}"
                f"/payment-cancel"
            )
        )


        # ----------------------------------------------------
        # REDIRECT TO STRIPE
        # ----------------------------------------------------

        return redirect(
            checkout_session.url
        )


    except stripe.error.StripeError as error:

        print(
            "STRIPE CHECKOUT ERROR:",
            repr(error)
        )

        return (
            "<div style='"
            "font-family:Arial,sans-serif;"
            "max-width:600px;"
            "margin:60px auto;"
            "padding:40px;"
            "text-align:center;"
            "'>"
            "<h2>Payment Could Not Be Started</h2>"
            "<p>"
            "We were unable to start your secure payment."
            "</p>"
            "<p>"
            "Please try again or contact Millrod Swim Academy."
            "</p>"
            "</div>"
        ), 500


    except Exception as error:

        print(
            "PAY NOW ERROR:",
            repr(error)
        )

        return (
            "<h2>Payment Error</h2>"
            "<p>"
            "Something went wrong while starting payment."
            "</p>"
        ), 500


# ============================================================
# PAY LATER
# ============================================================

@payment_bp.route(
    "/api/pay-later/<int:booking_id>",
    methods=["GET"]
)
def pay_later(booking_id):

    conn = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        )


        # ----------------------------------------------------
        # GET BOOKING
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT *
            FROM bookings
            WHERE id = %s
            LIMIT 1
            """,
            (booking_id,)
        )


        booking = cursor.fetchone()


        if not booking:

            return (
                "<h2>Registration Not Found</h2>"
                "<p>"
                "We could not find this registration."
                "</p>"
            ), 404


        # ----------------------------------------------------
        # CHECK APPROVAL
        # ----------------------------------------------------

        if booking["status"] != "confirmed":

            return (
                "<h2>Registration Not Yet Approved</h2>"
                "<p>"
                "Your registration must be approved "
                "before selecting Pay Later."
                "</p>"
            ), 400


        # ----------------------------------------------------
        # ALREADY PAID
        # ----------------------------------------------------

        if booking["payment_status"] == "paid":

            conn.close()

            return (
                "<h2>Payment Already Completed</h2>"
                "<p>"
                "This registration has already been paid."
                "</p>"
            )


        # ----------------------------------------------------
        # UPDATE PAYMENT METHOD
        # ----------------------------------------------------

        cursor.execute(
            """
            UPDATE bookings
            SET
                payment_method = %s,
                payment_status = %s,
                status = %s
            WHERE id = %s
            RETURNING *
            """,
            (
                "cash_or_zelle",
                "pending",
                "confirmed",
                booking_id
            )
        )


        booking = cursor.fetchone()

        conn.commit()

        conn.close()

        conn = None


        # ----------------------------------------------------
        # SEND CUSTOMER CONFIRMATION
        # ----------------------------------------------------

        try:

            send_booking_confirmation(
                customer_email=booking["email"],
                customer_name=booking["name"],
                lesson_type=booking["lesson_type"],
                package=booking["package"],
                lesson_date=booking["lesson_date"],
                lesson_time=booking["lesson_time"],
                payment_status=booking["payment_status"],
                price=booking["price"]
            )

        except Exception as email_error:

            print(
                "PAY LATER CUSTOMER EMAIL ERROR:",
                repr(email_error)
            )


        # ----------------------------------------------------
        # NOTIFY OWNER
        # ----------------------------------------------------

        try:

            send_admin_notification(
                booking
            )

        except Exception as email_error:

            print(
                "PAY LATER OWNER EMAIL ERROR:",
                repr(email_error)
            )


        # ----------------------------------------------------
        # FRIENDLY CONFIRMATION PAGE
        # ----------------------------------------------------

        return render_template(
            "payment_success.html",
            booking=booking,
            payment_method="cash_or_zelle"
        )


    except Exception as error:

        if conn:

            conn.rollback()

        print(
            "PAY LATER ERROR:",
            repr(error)
        )

        return (
            "<h2>Unable to Confirm Pay Later</h2>"
            "<p>"
            "Please try again or contact Millrod Swim Academy."
            "</p>"
        ), 500


    finally:

        if conn:

            conn.close()


# ============================================================
# PAYMENT SUCCESS
# ============================================================

@payment_bp.route(
    "/payment-success",
    methods=["GET"]
)
def payment_success():

    session_id = request.args.get(
        "session_id"
    )


    if not session_id:

        return render_template(
            "payment_success.html",
            booking=None,
            payment_method="card"
        )


    try:

        checkout_session = stripe.checkout.Session.retrieve(
            session_id
        )

        booking_id = (
            checkout_session
            .get("metadata", {})
            .get("booking_id")
        )


        if not booking_id:

            return render_template(
                "payment_success.html",
                booking=None,
                payment_method="card"
            )


        booking = get_booking(
            int(booking_id)
        )


        return render_template(
            "payment_success.html",
            booking=booking,
            payment_method="card"
        )


    except Exception as error:

        print(
            "PAYMENT SUCCESS ERROR:",
            repr(error)
        )

        return render_template(
            "payment_success.html",
            booking=None,
            payment_method="card"
        )


# ============================================================
# PAYMENT CANCEL
# ============================================================

@payment_bp.route(
    "/payment-cancel",
    methods=["GET"]
)
def payment_cancel():

    return render_template(
        "payment_cancel.html"
    )