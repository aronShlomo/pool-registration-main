from flask import Blueprint, request, jsonify, redirect
import stripe
import threading

import psycopg2.extras

from config import Config
from database import get_db_connection

from email_service import (
    send_booking_confirmation,
    send_admin_notification,
)


# ============================================================
# BLUEPRINT
# ============================================================

payment_bp = Blueprint(
    "payment",
    __name__
)


# ============================================================
# STRIPE
# ============================================================

stripe.api_key = Config.STRIPE_SECRET_KEY


# ============================================================
# HELPERS
# ============================================================

def get_booking(booking_id):

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


def send_email_background(
    booking,
    notify_owner=False
):

    def worker():

        try:

            send_booking_confirmation(
                booking
            )

            print(
                f"PAYMENT CONFIRMATION EMAIL SENT "
                f"FOR BOOKING #{booking['id']}"
            )

            if notify_owner:

                send_admin_notification(
                    booking
                )

        except Exception as error:

            print(
                "PAYMENT EMAIL ERROR:",
                repr(error)
            )

    thread = threading.Thread(
        target=worker,
        daemon=True
    )

    thread.start()


def stripe_error_message(error):

    print(
        "STRIPE ERROR:",
        repr(error)
    )

    return (
        "We were unable to start the payment. "
        "Please try again or contact Millrod Swim Academy."
    )


# ============================================================
# CREATE STRIPE CHECKOUT SESSION
# ============================================================

@payment_bp.route(
    "/create-checkout-session",
    methods=["POST"]
)
def create_checkout_session():

    try:

        data = request.get_json(
            silent=True
        )

        if not data:

            return jsonify({
                "success": False,
                "error": "No payment information was received."
            }), 400


        booking_id = data.get(
            "booking_id"
        )


        if not booking_id:

            return jsonify({
                "success": False,
                "error": "Booking ID is missing."
            }), 400


        booking = get_booking(
            booking_id
        )


        if not booking:

            return jsonify({
                "success": False,
                "error": "Booking not found."
            }), 404


        if booking["status"] != "confirmed":

            return jsonify({
                "success": False,
                "error":
                    "This booking has not been approved yet."
            }), 400


        if booking["payment_status"] == "paid":

            return jsonify({
                "success": False,
                "error":
                    "This booking has already been paid."
            }), 400


        price = Config.LESSON_PRICES[
            booking["lesson_type"]
        ][
            booking["package"]
        ]


        if not price or price <= 0:

            return jsonify({
                "success": False,
                "error":
                    "Unable to determine the booking price."
            }), 400


        session = stripe.checkout.Session.create(

            payment_method_types=[
                "card"
            ],

            mode="payment",

            customer_email=booking["email"],

            line_items=[

                {
                    "price_data": {

                        "currency":
                            Config.CURRENCY,

                        "product_data": {

                            "name":
                                (
                                    f"{booking['lesson_type']} "
                                    f"- {booking['package']}"
                                ),

                        },

                        "unit_amount":
                            int(price),

                    },

                    "quantity": 1,

                }

            ],

            metadata={

                "booking_id":
                    str(booking_id)

            },

            success_url=(
                f"{Config.DOMAIN}"
                "/payment-success"
                "?session_id={CHECKOUT_SESSION_ID}"
            ),

            cancel_url=(
                f"{Config.DOMAIN}"
                "/payment-cancel"
            )

        )


        return jsonify({

            "success": True,

            "checkout_url":
                session.url

        })


    except stripe.error.StripeError as error:

        return jsonify({

            "success": False,

            "error":
                stripe_error_message(error)

        }), 500


    except Exception as error:

        print(
            "CREATE CHECKOUT ERROR:",
            repr(error)
        )

        return jsonify({

            "success": False,

            "error":
                "Unable to start payment."

        }), 500


# ============================================================
# PAY NOW
# ============================================================

@payment_bp.route(
    "/pay-now/<int:booking_id>",
    methods=["GET"]
)
def pay_now(
    booking_id
):

    try:

        booking = get_booking(
            booking_id
        )


        if not booking:

            return """
            <h2>Booking Not Found</h2>
            <p>
                We could not find your swimming lesson booking.
            </p>
            """, 404


        if booking["status"] != "confirmed":

            return """
            <h2>Booking Not Approved</h2>
            <p>
                Your booking has not been approved yet.
            </p>
            """, 400


        if booking["payment_status"] == "paid":

            return """
            <h2>Payment Already Completed ✓</h2>
            <p>
                This swimming lesson has already been paid.
            </p>
            """, 200


        price = Config.LESSON_PRICES[
            booking["lesson_type"]
        ][
            booking["package"]
        ]


        if not price or price <= 0:

            return """
            <h2>Payment Error</h2>
            <p>
                We could not determine the price for this booking.
            </p>
            """, 400


        session = stripe.checkout.Session.create(

            payment_method_types=[
                "card"
            ],

            mode="payment",

            customer_email=
                booking["email"],

            line_items=[

                {

                    "price_data": {

                        "currency":
                            Config.CURRENCY,

                        "product_data": {

                            "name":
                                (
                                    f"{booking['lesson_type']} "
                                    f"- {booking['package']}"
                                ),

                        },

                        "unit_amount":
                            int(price),

                    },

                    "quantity": 1,

                }

            ],

            metadata={

                "booking_id":
                    str(booking_id)

            },

            success_url=(
                f"{Config.DOMAIN}"
                "/payment-success"
                "?session_id={CHECKOUT_SESSION_ID}"
            ),

            cancel_url=(
                f"{Config.DOMAIN}"
                "/payment-cancel"
            )

        )


        return redirect(
            session.url
        )


    except stripe.error.StripeError as error:

        print(
            "PAY NOW STRIPE ERROR:",
            repr(error)
        )

        return """

        <!DOCTYPE html>

        <html>

        <head>

            <meta charset="UTF-8">

            <meta
                name="viewport"
                content="width=device-width, initial-scale=1.0"
            >

            <title>Payment Error</title>

        </head>

        <body
            style="
                margin:0;
                padding:40px 20px;
                background:#eef7fb;
                font-family:Arial,sans-serif;
            "
        >

            <div
                style="
                    max-width:600px;
                    margin:auto;
                    background:white;
                    padding:40px;
                    border-radius:18px;
                    text-align:center;
                    box-shadow:0 10px 30px rgba(0,0,0,.08);
                "
            >

                <div
                    style="
                        font-size:55px;
                    "
                >
                    💳
                </div>

                <h1
                    style="
                        color:#023e8a;
                    "
                >
                    Payment Could Not Start
                </h1>

                <p
                    style="
                        color:#555;
                        line-height:1.6;
                    "
                >
                    We were unable to start your secure
                    Stripe payment.
                    Please try again.
                </p>

                <a
                    href="/"
                    style="
                        display:inline-block;
                        margin-top:20px;
                        background:#0077b6;
                        color:white;
                        padding:14px 25px;
                        border-radius:10px;
                        text-decoration:none;
                        font-weight:bold;
                    "
                >
                    Return to Millrod Swim Academy
                </a>

            </div>

        </body>

        </html>

        """, 500


    except Exception as error:

        print(
            "PAY NOW ERROR:",
            repr(error)
        )

        return """

        <h2>Payment Error</h2>

        <p>
            We were unable to start your payment.
            Please try again.
        </p>

        """, 500


# ============================================================
# PAY LATER
# ============================================================

@payment_bp.route(
    "/pay-later/<int:booking_id>",
    methods=["GET"]
)
def pay_later(
    booking_id
):

    conn = None

    try:

        booking = get_booking(
            booking_id
        )


        if not booking:

            return """

            <h2>Booking Not Found</h2>

            <p>
                We could not find your swimming lesson booking.
            </p>

            """, 404


        if booking["status"] != "confirmed":

            return """

            <h2>Booking Not Approved</h2>

            <p>
                Your lesson must be approved before selecting
                Pay Later.
            </p>

            """, 400


        if booking["payment_status"] == "paid":

            return """

            <h2>Payment Already Completed ✓</h2>

            <p>
                This booking has already been paid.
            </p>

            """, 200


        conn = get_db_connection()

        cursor = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        )


        cursor.execute(
            """
            UPDATE bookings

            SET
                status = 'confirmed',
                payment_status = 'pending',
                payment_method = 'pay_later'

            WHERE id = %s

            RETURNING *
            """,
            (
                booking_id,
            )
        )


        booking = cursor.fetchone()


        conn.commit()


        conn.close()

        conn = None


        if not booking:

            return """

            <h2>Booking Error</h2>

            <p>
                We could not update your booking.
            </p>

            """, 500


        # ----------------------------------------------------
        # SEND EMAILS IN BACKGROUND
        # ----------------------------------------------------

        send_email_background(
            booking,
            notify_owner=True
        )


        # ----------------------------------------------------
        # PRICE
        # ----------------------------------------------------

        price_cents = Config.LESSON_PRICES[
            booking["lesson_type"]
        ][
            booking["package"]
        ]


        amount = (
            f"${price_cents / 100:.2f}"
        )


        # ----------------------------------------------------
        # PAY LATER CONFIRMATION PAGE
        # ----------------------------------------------------

        return f"""

        <!DOCTYPE html>

        <html>

        <head>

            <meta charset="UTF-8">

            <meta
                name="viewport"
                content="width=device-width, initial-scale=1.0"
            >

            <title>
                Pay Later Confirmed
            </title>

        </head>


        <body
            style="
                margin:0;
                padding:0;
                background:#eef7fb;
                font-family:
                    Arial,
                    Helvetica,
                    sans-serif;
                color:#263238;
            "
        >

            <div
                style="
                    max-width:650px;
                    margin:50px auto;
                    padding:20px;
                "
            >

                <div
                    style="
                        background:#ffffff;
                        border-radius:22px;
                        overflow:hidden;
                        box-shadow:
                            0 12px 40px
                            rgba(0,0,0,.10);
                    "
                >

                    <div
                        style="
                            background:
                                linear-gradient(
                                    135deg,
                                    #0077b6,
                                    #023e8a
                                );
                            padding:40px 25px;
                            text-align:center;
                            color:white;
                        "
                    >

                        <div
                            style="
                                font-size:55px;
                            "
                        >
                            🏊
                        </div>

                        <h1
                            style="
                                margin:10px 0 0;
                                font-size:28px;
                            "
                        >
                            Booking Confirmed!
                        </h1>

                        <p>
                            Pay Later Selected
                        </p>

                    </div>


                    <div
                        style="
                            padding:35px;
                        "
                    >

                        <h2
                            style="
                                color:#023e8a;
                            "
                        >
                            Thank you,
                            {booking['name']}! 👋
                        </h2>


                        <p
                            style="
                                font-size:16px;
                                line-height:1.7;
                            "
                        >
                            Your swimming lesson has been
                            confirmed.
                        </p>


                        <div
                            style="
                                background:#f6fbfe;
                                border:1px solid #dceef7;
                                border-radius:15px;
                                padding:24px;
                                margin:25px 0;
                            "
                        >

                            <h3
                                style="
                                    margin-top:0;
                                    color:#023e8a;
                                "
                            >
                                Lesson Details
                            </h3>


                            <p>
                                <strong>
                                    Student:
                                </strong>

                                {booking['name']}
                            </p>


                            <p>
                                <strong>
                                    Lesson:
                                </strong>

                                {booking['lesson_type']}
                            </p>


                            <p>
                                <strong>
                                    Package:
                                </strong>

                                {booking['package']}
                            </p>


                            <p>
                                <strong>
                                    Date:
                                </strong>

                                {booking['lesson_date']}
                            </p>


                            <p>
                                <strong>
                                    Time:
                                </strong>

                                {booking['lesson_time']}
                            </p>


                            <p
                                style="
                                    font-size:20px;
                                    margin-bottom:0;
                                "
                            >
                                <strong>
                                    Amount Due:
                                </strong>

                                <span
                                    style="
                                        color:#0077b6;
                                        font-weight:bold;
                                    "
                                >
                                    {amount}
                                </span>
                            </p>

                        </div>


                        <div
                            style="
                                background:#fff8e8;
                                border-left:
                                    5px solid
                                    #f4b400;
                                padding:22px;
                                border-radius:10px;
                                margin:25px 0;
                            "
                        >

                            <h3
                                style="
                                    margin-top:0;
                                    color:#8a6500;
                                "
                            >
                                🕒 Please Pay When You Arrive
                            </h3>


                            <p
                                style="
                                    line-height:1.7;
                                    margin-bottom:0;
                                "
                            >
                                You selected
                                <strong>
                                    Pay Later
                                </strong>.

                                Please bring your payment
                                when you arrive for your
                                swimming lesson.

                                <br><br>

                                <strong>
                                    Amount to pay:
                                    {amount}
                                </strong>
                            </p>

                        </div>


                        <div
                            style="
                                text-align:center;
                                margin-top:30px;
                            "
                        >

                            <a
                                href="/"
                                style="
                                    display:inline-block;
                                    background:#0077b6;
                                    color:white;
                                    padding:15px 30px;
                                    border-radius:10px;
                                    text-decoration:none;
                                    font-weight:bold;
                                "
                            >
                                Return to Millrod Swim Academy
                            </a>

                        </div>


                        <p
                            style="
                                text-align:center;
                                color:#777;
                                font-size:13px;
                                margin-top:30px;
                            "
                        >
                            Booking ID:
                            <strong>
                                #{booking_id}
                            </strong>
                        </p>

                    </div>


                    <div
                        style="
                            background:#f5f8fa;
                            padding:20px;
                            text-align:center;
                            color:#777;
                            font-size:13px;
                        "
                    >

                        <strong>
                            Millrod Swim Academy
                        </strong>

                        <br>

                        Professional Swimming Lessons

                    </div>

                </div>

            </div>

        </body>

        </html>

        """


    except Exception as error:

        if conn:

            try:
                conn.rollback()
            except Exception:
                pass


        print(
            "PAY LATER ERROR:",
            repr(error)
        )


        return """

        <h2>Unable to Process Pay Later</h2>

        <p>
            We could not update your payment selection.
            Please contact Millrod Swim Academy.
        </p>

        """, 500


    finally:

        if conn:

            conn.close()


# ============================================================
# PAYMENT SUCCESS
# ============================================================

@payment_bp.route(
    "/payment-success"
)
def payment_success():

    session_id = request.args.get(
        "session_id"
    )


    if not session_id:

        return """

        <h2>Invalid Payment</h2>

        <p>
            No Stripe payment session was provided.
        </p>

        """, 400


    try:

        session = stripe.checkout.Session.retrieve(
                session_id
            )


        if session.payment_status != "paid":

            return """

            <h2>Payment Not Completed</h2>

            <p>
                The Stripe payment was not completed.
            </p>

            """, 400


        metadata = session.metadata or {}


        booking_id = metadata.get(
                "booking_id"
            )


        if not booking_id:

            return """

            <h2>Payment Error</h2>

            <p>
                The payment was received but the booking
                could not be identified.
            </p>

            """, 500


        conn = get_db_connection()

        cursor = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        )


        cursor.execute(
            """
            UPDATE bookings

            SET
                payment_method = 'card',
                payment_status = 'paid',
                status = 'confirmed',
                stripe_payment_id = %s

            WHERE id = %s

            RETURNING *
            """,
            (
                session.id,
                booking_id
            )
        )


        booking = cursor.fetchone()


        conn.commit()

        conn.close()


        if not booking:

            return """

            <h2>Booking Not Found</h2>

            <p>
                The payment was completed, but the booking
                could not be found.
            </p>

            """, 404


        send_email_background(
            booking,
            notify_owner=True
        )


        return """

        <!DOCTYPE html>

        <html>

        <head>

            <meta charset="UTF-8">

            <meta
                name="viewport"
                content="width=device-width, initial-scale=1.0"
            >

            <title>
                Payment Successful
            </title>

        </head>

        <body
            style="
                margin:0;
                padding:50px 20px;
                background:#eef7fb;
                font-family:Arial,sans-serif;
            "
        >

            <div
                style="
                    max-width:600px;
                    margin:auto;
                    background:white;
                    padding:45px;
                    border-radius:20px;
                    text-align:center;
                    box-shadow:
                        0 10px 35px
                        rgba(0,0,0,.10);
                "
            >

                <div
                    style="
                        font-size:60px;
                    "
                >
                    ✓
                </div>

                <h1
                    style="
                        color:#198754;
                    "
                >
                    Payment Successful!
                </h1>

                <p
                    style="
                        font-size:17px;
                        line-height:1.6;
                        color:#555;
                    "
                >
                    Your payment has been received and
                    your swimming lesson is confirmed.
                </p>

                <a
                    href="/"
                    style="
                        display:inline-block;
                        margin-top:20px;
                        background:#0077b6;
                        color:white;
                        padding:15px 30px;
                        border-radius:10px;
                        text-decoration:none;
                        font-weight:bold;
                    "
                >
                    Return Home
                </a>

            </div>

        </body>

        </html>

        """


    except Exception as error:

        print(
            "PAYMENT SUCCESS ERROR:",
            repr(error)
        )


        return """

        <h2>Payment Processing Error</h2>

        <p>
            Your payment may have been received.
            Please contact Millrod Swim Academy
            before attempting another payment.
        </p>

        """, 500


# ============================================================
# PAYMENT CANCEL
# ============================================================

@payment_bp.route(
    "/payment-cancel"
)
def payment_cancel():

    return """

    <!DOCTYPE html>

    <html>

    <head>

        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <title>
            Payment Cancelled
        </title>

    </head>


    <body
        style="
            margin:0;
            padding:50px 20px;
            background:#eef7fb;
            font-family:Arial,sans-serif;
        "
    >

        <div
            style="
                max-width:600px;
                margin:auto;
                background:white;
                padding:45px;
                border-radius:20px;
                text-align:center;
                box-shadow:
                    0 10px 35px
                    rgba(0,0,0,.10);
            "
        >

            <div
                style="
                    font-size:55px;
                "
            >
                💳
            </div>


            <h1
                style="
                    color:#023e8a;
                "
            >
                Payment Cancelled
            </h1>


            <p
                style="
                    color:#555;
                    line-height:1.6;
                "
            >
                Your payment was cancelled.
                Your booking has not been marked as paid.
            </p>


            <a
                href="/"
                style="
                    display:inline-block;
                    margin-top:20px;
                    background:#0077b6;
                    color:white;
                    padding:15px 30px;
                    border-radius:10px;
                    text-decoration:none;
                    font-weight:bold;
                "
            >
                Return Home
            </a>

        </div>

    </body>

    </html>

    """