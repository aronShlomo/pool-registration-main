print("Booking blueprint LOADED")

from flask import (
    Blueprint,
    request,
    jsonify,
    redirect
)

from database import (
    get_db_connection,
    booking_slot_is_available
)

from config import Config

import email_service

import secrets

import psycopg2.extras


# ============================================================
# BLUEPRINT
# ============================================================

booking_bp = Blueprint(
    "booking",
    __name__,
    url_prefix="/api"
)

# Email configuration diagnostics are intentionally kept out of the
# browser response. They appear in Render/server logs only.
print(
    "BOOKING EMAIL CONFIG:",
    {
        "owner_email_configured": bool(Config.OWNER_EMAIL),
        "resend_key_configured": bool(Config.RESEND_API_KEY),
        "email_from_configured": bool(Config.EMAIL_FROM),
        "domain_configured": bool(Config.DOMAIN),
    }
)


# ============================================================
# HELPERS
# ============================================================

def first_nonempty(data, *keys):
    """
    Return the first non-empty value from a list of possible
    frontend field names.
    """

    for key in keys:

        value = data.get(key)

        if value is not None:

            value = str(value).strip()

            if value:
                return value

    return None


def get_server_price(lesson_type, package):
    """
    Calculate the official price on the SERVER.

    Never trust the price sent by JavaScript.
    """

    try:

        price_cents = Config.LESSON_PRICES[
            lesson_type
        ][
            package
        ]

        return price_cents

    except KeyError:

        return None


def format_price(price_cents):
    """
    Convert cents into a friendly dollar amount.
    """

    return f"${price_cents / 100:.2f}"


def generate_approval_token():
    """
    Generate a secure random approval token.
    """

    return secrets.token_urlsafe(32)


# ============================================================
# CREATE BOOKING
# ============================================================

@booking_bp.route(
    "/create-booking",
    methods=["POST"]
)
def create_booking():

    conn = None

    try:

        # ----------------------------------------------------
        # READ REQUEST
        # ----------------------------------------------------

        data = request.get_json(
            silent=True
        )

        if not data:

            return jsonify({
                "success": False,
                "error": "No registration information was received."
            }), 400


        # ----------------------------------------------------
        # CUSTOMER INFORMATION
        # ----------------------------------------------------

        name = first_nonempty(
            data,
            "name",
            "full_name",
            "student_name",
            "first_name"
        )

        email = first_nonempty(
            data,
            "email",
            "email_address"
        )

        phone = first_nonempty(
            data,
            "phone",
            "phone_number"
        )


        # ----------------------------------------------------
        # LESSON INFORMATION
        # ----------------------------------------------------

        lesson_type = first_nonempty(
            data,
            "lesson_type",
            "lessonType",
            "lesson",
            "selectedLesson",
            "type"
        )

        package = first_nonempty(
            data,
            "package",
            "package_type"
        )

        lesson_date = first_nonempty(
            data,
            "lesson_date",
            "date",
            "lessonDate",
            "selectedDate"
        )

        lesson_time = first_nonempty(
            data,
            "lesson_time",
            "time",
            "lessonTime",
            "selectedTime"
        )


        # ----------------------------------------------------
        # VALIDATE REQUIRED INFORMATION
        # ----------------------------------------------------

        required_fields = {

            "name": name,

            "email": email,

            "phone": phone,

            "lesson_type": lesson_type,

            "package": package,

            "lesson_date": lesson_date,

            "lesson_time": lesson_time
        }


        missing_fields = [
            field
            for field, value in required_fields.items()
            if not value
        ]


        if missing_fields:

            return jsonify({
                "success": False,
                "error": (
                    "Please complete all required fields: "
                    + ", ".join(missing_fields)
                )
            }), 400


        # ----------------------------------------------------
        # VALIDATE LESSON TYPE
        # ----------------------------------------------------

        if lesson_type not in Config.LESSON_PRICES:

            return jsonify({
                "success": False,
                "error": "The selected lesson type is not available."
            }), 400


        # ----------------------------------------------------
        # VALIDATE PACKAGE
        # ----------------------------------------------------

        if package not in Config.LESSON_PRICES[
            lesson_type
        ]:

            return jsonify({
                "success": False,
                "error": "The selected package is not available."
            }), 400


        # ----------------------------------------------------
        # SERVER-SIDE PRICE
        # ----------------------------------------------------
        #
        # IMPORTANT:
        #
        # We intentionally IGNORE any price sent by the browser.
        #
        # The server calculates the official price.
        # ----------------------------------------------------

        price_cents = get_server_price(
            lesson_type,
            package
        )


        if price_cents is None:

            return jsonify({
                "success": False,
                "error": "Unable to determine the lesson price."
            }), 400


        price = format_price(
            price_cents
        )


        # ----------------------------------------------------
        # CHECK AVAILABILITY
        # ----------------------------------------------------

        if not booking_slot_is_available(
            lesson_date,
            lesson_time
        ):

            return jsonify({
                "success": False,
                "error": (
                    "This lesson time is already reserved. "
                    "Please choose another time."
                )
            }), 409


        # ----------------------------------------------------
        # DATABASE
        # ----------------------------------------------------

        conn = get_db_connection()

        cursor = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        )


        # ----------------------------------------------------
        # DOUBLE-CHECK SLOT
        # ----------------------------------------------------
        #
        # This protects against a second request arriving
        # between the first availability check and INSERT.
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT id
            FROM bookings
            WHERE lesson_date = %s
              AND lesson_time = %s
              AND status IN (
                  'pending',
                  'confirmed'
              )
            LIMIT 1
            """,
            (
                lesson_date,
                lesson_time
            )
        )


        if cursor.fetchone():

            conn.rollback()

            return jsonify({
                "success": False,
                "error": (
                    "This lesson time was just reserved "
                    "by another customer. Please choose "
                    "another time."
                )
            }), 409


        # ----------------------------------------------------
        # SECURE APPROVAL TOKEN
        # ----------------------------------------------------

        approval_token = generate_approval_token()


        # ----------------------------------------------------
        # INSERT BOOKING
        # ----------------------------------------------------

        cursor.execute(
            """
            INSERT INTO bookings
            (
                name,
                email,
                phone,
                lesson_type,
                package,
                price,
                lesson_date,
                lesson_time,
                payment_method,
                payment_status,
                status,
                approval_token
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            RETURNING *
            """,
            (
                name,
                email,
                phone,
                lesson_type,
                package,
                price,
                lesson_date,
                lesson_time,
                "not_selected",
                "pending",
                "pending",
                approval_token
            )
        )


        booking = cursor.fetchone()

        conn.commit()


        # ----------------------------------------------------
        # SEND OWNER NOTIFICATION
        # ----------------------------------------------------
        #
        # The customer is NOT approved yet.
        #
        # Owner receives:
        #
        # APPROVE
        # REJECT
        #
        # ----------------------------------------------------

        # ----------------------------------------------------
        # SEND OWNER NOTIFICATION
        # ----------------------------------------------------
        #
        # IMPORTANT:
        # Do NOT silently report success if the owner email fails.
        # The previous version caught the email exception and still
        # returned success to the customer, which made it look like
        # everything worked even when Resend rejected the email.
        #
        # The booking is already committed, so if email delivery fails
        # we keep the booking and return a clear server error. This
        # prevents losing the registration while making the failure
        # visible in the browser and Render logs.
        # ----------------------------------------------------

        try:

            if not Config.OWNER_EMAIL:
                raise RuntimeError(
                    "OWNER_EMAIL is not configured."
                )

            if not Config.RESEND_API_KEY:
                raise RuntimeError(
                    "RESEND_API_KEY is not configured."
                )

            if not Config.EMAIL_FROM:
                raise RuntimeError(
                    "EMAIL_FROM is not configured."
                )

            email_result = email_service.send_admin_notification(
                booking
            )

            if not email_result:
                raise RuntimeError(
                    "Owner notification did not return a Resend response."
                )

            print(
                f"OWNER NOTIFICATION SENT "
                f"FOR BOOKING #{booking['id']}: "
                f"{email_result}"
            )

        except Exception as email_error:

            print(
                "OWNER EMAIL ERROR:",
                repr(email_error)
            )

            return jsonify({
                "success": False,
                "booking_id": booking["id"],
                "error": (
                    "Your registration was saved, but we could not "
                    "send the approval email to the owner. "
                    "Please contact the academy or try again later."
                )
            }), 500


        # ----------------------------------------------------
        # CUSTOMER RESPONSE
        # ----------------------------------------------------

        return jsonify({

            "success": True,

            "booking_id": booking["id"],

            "price": price,

            "status": "pending",

            "message": (
                "Thank you! Your registration request "
                "has been sent for approval. "
                "We will email you once your request "
                "has been reviewed."
            )
        }), 201


    except Exception as error:

        if conn:

            conn.rollback()


        print(
            "CREATE BOOKING ERROR:",
            repr(error)
        )


        return jsonify({

            "success": False,

            "error": (
                "We were unable to submit your registration "
                "right now. Please try again."
            )

        }), 500


    finally:

        if conn:

            conn.close()


# ============================================================
# GET BOOKINGS FOR CALENDAR
# ============================================================

@booking_bp.route(
    "/bookings",
    methods=["GET"]
)
def get_bookings():

    conn = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        )


        cursor.execute(
            """
            SELECT
                id,
                lesson_date,
                lesson_time,
                status
            FROM bookings
            WHERE status IN (
                'pending',
                'confirmed'
            )
            ORDER BY lesson_date, lesson_time
            """
        )


        rows = cursor.fetchall()


        return jsonify([

            {
                "id": row["id"],

                "title": "Reserved",

                "start": (
                    f"{row['lesson_date']}"
                    f"T"
                    f"{row['lesson_time']}"
                ),

                "status": row["status"]
            }

            for row in rows

        ])


    except Exception as error:

        print(
            "GET BOOKINGS ERROR:",
            repr(error)
        )

        return jsonify({
            "success": False,
            "error": "Unable to load bookings."
        }), 500


    finally:

        if conn:

            conn.close()


# ============================================================
# GET BOOKED SLOTS
# ============================================================

@booking_bp.route(
    "/booked-slots",
    methods=["GET"]
)
def booked_slots():

    conn = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        )


        cursor.execute(
            """
            SELECT
                lesson_date,
                lesson_time
            FROM bookings
            WHERE status IN (
                'pending',
                'confirmed'
            )
            ORDER BY lesson_date, lesson_time
            """
        )


        rows = cursor.fetchall()


        return jsonify([

            {
                "date": row["lesson_date"],

                "time": row["lesson_time"]
            }

            for row in rows

        ])


    except Exception as error:

        print(
            "BOOKED SLOTS ERROR:",
            repr(error)
        )

        return jsonify({
            "success": False,
            "error": "Unable to load available times."
        }), 500


    finally:

        if conn:

            conn.close()


# ============================================================
# OWNER APPROVES BOOKING
# ============================================================

@booking_bp.route(
    "/approve-booking",
    methods=["GET"]
)
def approve_booking():

    booking = None

    conn = None

    try:

        token = request.args.get(
            "token",
            ""
        ).strip()


        if not token:

            return (
                "<h2>Invalid approval link</h2>"
                "<p>This approval link is missing its secure token.</p>"
            ), 400


        conn = get_db_connection()

        cursor = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        )


        # ----------------------------------------------------
        # FIND BOOKING BY SECURE TOKEN
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT *
            FROM bookings
            WHERE approval_token = %s
            LIMIT 1
            """,
            (token,)
        )


        booking = cursor.fetchone()


        if not booking:

            return (
                "<h2>Booking Not Found</h2>"
                "<p>This approval link is invalid or expired.</p>"
            ), 404


        # ----------------------------------------------------
        # ALREADY REJECTED
        # ----------------------------------------------------

        if booking["status"] == "rejected":

            return (
                "<h2>Booking Already Rejected</h2>"
                "<p>This registration has already been rejected.</p>"
            ), 409


        # ----------------------------------------------------
        # ALREADY APPROVED
        # ----------------------------------------------------

        if booking["status"] == "confirmed":

            return (
                "<h2>Booking Already Approved ✔</h2>"
                "<p>The customer has already been notified.</p>"
            ), 200


        # ----------------------------------------------------
        # APPROVE
        # ----------------------------------------------------

        cursor.execute(
            """
            UPDATE bookings
            SET
                status = 'confirmed',
                payment_status = 'pending'
            WHERE id = %s
            RETURNING *
            """,
            (booking["id"],)
        )


        booking = cursor.fetchone()

        conn.commit()


        # ----------------------------------------------------
        # SEND CUSTOMER APPROVAL EMAIL
        # ----------------------------------------------------

        try:

            email_service.send_user_approved_email(
                booking
            )

            print(
                f"APPROVAL EMAIL SENT "
                f"FOR BOOKING #{booking['id']}"
            )

        except Exception as email_error:

            print(
                "APPROVAL EMAIL ERROR:",
                repr(email_error)
            )


        # ----------------------------------------------------
        # OWNER RESULT
        # ----------------------------------------------------

        return (
            "<div style='"
            "font-family:Arial,sans-serif;"
            "max-width:600px;"
            "margin:60px auto;"
            "padding:40px;"
            "text-align:center;"
            "border-radius:16px;"
            "background:#f7fbff;"
            "box-shadow:0 10px 30px rgba(0,0,0,.08);"
            "'>"
            "<div style='font-size:55px;'>✔</div>"
            "<h2 style='color:#0077b6;'>Booking Approved</h2>"
            "<p style='font-size:17px;color:#555;'>"
            "The registration has been approved and "
            "the customer has been notified."
            "</p>"
            "</div>"
        )


    except Exception as error:

        if conn:

            conn.rollback()


        print(
            "APPROVE BOOKING ERROR:",
            repr(error)
        )


        return (
            "<h2>Unable to Approve Booking</h2>"
            "<p>Please try again or contact the administrator.</p>"
        ), 500


    finally:

        if conn:

            conn.close()


# ============================================================
# OWNER REJECTS BOOKING
# ============================================================

@booking_bp.route(
    "/reject-booking",
    methods=["GET"]
)
def reject_booking():

    conn = None

    try:

        token = request.args.get(
            "token",
            ""
        ).strip()


        if not token:

            return (
                "<h2>Invalid rejection link</h2>"
                "<p>This rejection link is missing its secure token.</p>"
            ), 400


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
            WHERE approval_token = %s
            LIMIT 1
            """,
            (token,)
        )


        booking = cursor.fetchone()


        if not booking:

            return (
                "<h2>Booking Not Found</h2>"
                "<p>This link is invalid or expired.</p>"
            ), 404


        # ----------------------------------------------------
        # ALREADY APPROVED
        # ----------------------------------------------------

        if booking["status"] == "confirmed":

            return (
                "<h2>Booking Already Approved</h2>"
                "<p>This registration has already been approved.</p>"
            ), 409


        # ----------------------------------------------------
        # ALREADY REJECTED
        # ----------------------------------------------------

        if booking["status"] == "rejected":

            return (
                "<h2>Booking Already Rejected</h2>"
                "<p>The customer has already been notified.</p>"
            ), 200


        # ----------------------------------------------------
        # REJECT
        # ----------------------------------------------------

        cursor.execute(
            """
            UPDATE bookings
            SET
                status = 'rejected'
            WHERE id = %s
            RETURNING *
            """,
            (booking["id"],)
        )


        booking = cursor.fetchone()

        conn.commit()


        # ----------------------------------------------------
        # SEND CUSTOMER REJECTION EMAIL
        # ----------------------------------------------------

        try:

            email_service.send_user_rejected_email(
                booking
            )

            print(
                f"REJECTION EMAIL SENT "
                f"FOR BOOKING #{booking['id']}"
            )

        except Exception as email_error:

            print(
                "REJECTION EMAIL ERROR:",
                repr(email_error)
            )


        # ----------------------------------------------------
        # OWNER RESULT
        # ----------------------------------------------------

        return (
            "<div style='"
            "font-family:Arial,sans-serif;"
            "max-width:600px;"
            "margin:60px auto;"
            "padding:40px;"
            "text-align:center;"
            "border-radius:16px;"
            "background:#fff8f8;"
            "box-shadow:0 10px 30px rgba(0,0,0,.08);"
            "'>"
            "<div style='font-size:55px;'>✖</div>"
            "<h2 style='color:#dc3545;'>Booking Rejected</h2>"
            "<p style='font-size:17px;color:#555;'>"
            "The customer has been notified."
            "</p>"
            "</div>"
        )


    except Exception as error:

        if conn:

            conn.rollback()


        print(
            "REJECT BOOKING ERROR:",
            repr(error)
        )


        return (
            "<h2>Unable to Reject Booking</h2>"
            "<p>Please try again or contact the administrator.</p>"
        ), 500


    finally:

        if conn:

            conn.close()
            