import stripe

from flask import (
    Blueprint,
    request,
    jsonify
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

webhook_bp = Blueprint(
    "webhook",
    __name__
)


# ============================================================
# STRIPE CONFIGURATION
# ============================================================

stripe.api_key = Config.STRIPE_SECRET_KEY


# ============================================================
# STRIPE WEBHOOK
# ============================================================

@webhook_bp.route(
    "/stripe-webhook",
    methods=["POST"]
)
def stripe_webhook():

    payload = request.data

    signature = request.headers.get(
        "Stripe-Signature"
    )


    # ========================================================
    # VERIFY STRIPE EVENT
    # ========================================================

    if not Config.STRIPE_WEBHOOK_SECRET:

        print(
            "STRIPE WEBHOOK ERROR: "
            "STRIPE_WEBHOOK_SECRET is missing."
        )

        return jsonify({
            "error": "Webhook configuration error"
        }), 500


    try:

        event = stripe.Webhook.construct_event(

            payload,

            signature,

            Config.STRIPE_WEBHOOK_SECRET
        )


    except ValueError:

        print(
            "STRIPE WEBHOOK ERROR: Invalid payload"
        )

        return jsonify({
            "error": "Invalid payload"
        }), 400


    except stripe.error.SignatureVerificationError:

        print(
            "STRIPE WEBHOOK ERROR: Invalid signature"
        )

        return jsonify({
            "error": "Invalid signature"
        }), 400


    except Exception as error:

        print(
            "STRIPE WEBHOOK CONSTRUCTION ERROR:",
            repr(error)
        )

        return jsonify({
            "error": "Unable to process webhook"
        }), 400


    # ========================================================
    # LOG EVENT
    # ========================================================

    event_type = event.get(
        "type"
    )

    print(
        "STRIPE EVENT:",
        event_type
    )


    # ========================================================
    # CHECKOUT COMPLETED
    # ========================================================

    if event_type != "checkout.session.completed":

        return jsonify({
            "received": True
        })


    session = (
        event
        .get("data", {})
        .get("object", {})
    )


    # ========================================================
    # ONLY PROCESS COMPLETED PAYMENTS
    # ========================================================

    payment_status = session.get(
        "payment_status"
    )


    if payment_status != "paid":

        print(
            "STRIPE CHECKOUT COMPLETED "
            "BUT PAYMENT IS NOT MARKED PAID:",
            payment_status
        )

        return jsonify({
            "received": True
        })


    # ========================================================
    # GET BOOKING ID
    # ========================================================

    metadata = session.get(
        "metadata",
        {}
    )


    booking_id = metadata.get(
        "booking_id"
    )


    if not booking_id:

        print(
            "STRIPE WEBHOOK ERROR: "
            "Booking ID missing from metadata."
        )

        return jsonify({
            "error": "Booking ID missing"
        }), 400


    try:

        booking_id = int(
            booking_id
        )

    except (TypeError, ValueError):

        print(
            "STRIPE WEBHOOK ERROR: "
            "Invalid booking ID."
        )

        return jsonify({
            "error": "Invalid booking ID"
        }), 400


    # ========================================================
    # DATABASE
    # ========================================================

    conn = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        )


        # ----------------------------------------------------
        # FIND BOOKING
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

            print(
                f"STRIPE WEBHOOK: "
                f"Booking #{booking_id} not found."
            )

            conn.close()

            return jsonify({
                "error": "Booking not found"
            }), 404


        # ----------------------------------------------------
        # IMPORTANT:
        #
        # DO NOT CHECK:
        #
        #     status == confirmed
        #
        # because owner approval already makes the booking
        # confirmed BEFORE the customer pays.
        #
        # We only check payment_status.
        # ----------------------------------------------------

        if booking["payment_status"] == "paid":

            print(
                f"BOOKING #{booking_id} "
                f"ALREADY PAID."
            )

            conn.close()

            return jsonify({
                "received": True,
                "already_processed": True
            })


        # ----------------------------------------------------
        # STRIPE PAYMENT ID
        # ----------------------------------------------------

        stripe_payment_id = (
            session.get("payment_intent")
            or session.get("id")
        )


        # ----------------------------------------------------
        # UPDATE PAYMENT
        # ----------------------------------------------------

        cursor.execute(
            """
            UPDATE bookings
            SET
                payment_status = 'paid',
                status = 'confirmed',
                payment_method = 'card',
                stripe_payment_id = %s
            WHERE id = %s
            RETURNING *
            """,
            (
                stripe_payment_id,
                booking_id
            )
        )


        booking = cursor.fetchone()


        conn.commit()


        print(
            f"BOOKING #{booking_id} "
            f"PAYMENT MARKED PAID."
        )


    except Exception as error:

        if conn:

            conn.rollback()


        print(
            "STRIPE DATABASE ERROR:",
            repr(error)
        )


        return jsonify({
            "error": "Database update failed"
        }), 500


    finally:

        if conn:

            conn.close()


    # ========================================================
    # SEND PAYMENT CONFIRMATION EMAILS
    # ========================================================

    customer_email_sent = False

    owner_email_sent = False


    # --------------------------------------------------------
    # CUSTOMER
    # --------------------------------------------------------

    try:

        send_booking_confirmation(

            customer_email=booking["email"],

            customer_name=booking["name"],

            lesson_type=booking["lesson_type"],

            package=booking["package"],

            lesson_date=booking["lesson_date"],

            lesson_time=booking["lesson_time"],

            payment_status="paid",

            price=booking["price"]
        )


        customer_email_sent = True


        print(
            f"PAYMENT CONFIRMATION SENT "
            f"TO CUSTOMER FOR BOOKING #{booking_id}"
        )


    except Exception as error:

        print(
            "CUSTOMER PAYMENT EMAIL ERROR:",
            repr(error)
        )


    # --------------------------------------------------------
    # OWNER
    # --------------------------------------------------------

    try:

        send_admin_notification(
            booking
        )


        owner_email_sent = True


        print(
            f"OWNER PAYMENT NOTIFICATION SENT "
            f"FOR BOOKING #{booking_id}"
        )


    except Exception as error:

        print(
            "OWNER PAYMENT EMAIL ERROR:",
            repr(error)
        )


    # ========================================================
    # RETURN SUCCESS TO STRIPE
    # ========================================================

    return jsonify({

        "received": True,

        "booking_id": booking_id,

        "payment_status": "paid",

        "customer_email_sent": customer_email_sent,

        "owner_email_sent": owner_email_sent
    })