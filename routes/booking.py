# ============================================================
# MILLROD SWIM ACADEMY
# BOOKING ROUTES
# ============================================================

from flask import (
    Blueprint,
    request,
    jsonify,
    render_template,
)

from datetime import datetime
import secrets

from config import Config
from database import get_db_connection

import email_service


# ============================================================
# BLUEPRINT
# ============================================================

booking_bp = Blueprint(
    "booking",
    __name__,
    url_prefix="/api",
)


# ============================================================
# GENERATE APPROVAL TOKEN
# ============================================================

def generate_approval_token():
    return secrets.token_urlsafe(32)


# ============================================================
# CONVERT DATABASE ROW TO DICTIONARY
# ============================================================

def row_to_dict(cursor, row):

    if row is None:
        return None

    if hasattr(row, "keys"):
        return dict(row)

    columns = [
        description[0]
        for description in cursor.description
    ]

    return dict(
        zip(
            columns,
            row,
        )
    )


# ============================================================
# CREATE BOOKING
# ============================================================

@booking_bp.route(
    "/create-booking",
    methods=["POST"],
)
def create_booking():

    conn = None

    try:

        data = request.get_json(
            silent=True
        ) or {}

        print("========================================")
        print("NEW BOOKING REQUEST")
        print("BOOKING DATA:")
        print(data)
        print("========================================")

        # ----------------------------------------------------
        # CUSTOMER
        # ----------------------------------------------------

        student_name = (
            data.get("student_name")
            or data.get("name")
            or ""
        ).strip()

        parent_name = (
            data.get("parent_name")
            or ""
        ).strip()

        email = (
            data.get("email")
            or ""
        ).strip()

        phone = (
            data.get("phone")
            or ""
        ).strip()

        # ----------------------------------------------------
        # LESSON
        # ----------------------------------------------------

        lesson_type = (
            data.get("lesson_type")
            or ""
        ).strip()

        package = (
            data.get("package")
            or ""
        ).strip()

        lesson_date = (
            data.get("lesson_date")
            or data.get("date")
            or ""
        ).strip()

        lesson_time = (
            data.get("lesson_time")
            or data.get("time")
            or ""
        ).strip()

        # ----------------------------------------------------
        # OTHER INFORMATION
        # ----------------------------------------------------

        dob = (
            data.get("dob")
            or ""
        ).strip()

        age = data.get("age") or ""

        emergency_contact = (
            data.get("emergency_contact")
            or ""
        ).strip()

        emergency_phone = (
            data.get("emergency_phone")
            or ""
        ).strip()

        swimming_experience = (
            data.get("swimming_experience")
            or ""
        ).strip()

        medical = (
            data.get("medical")
            or ""
        ).strip()

        notes = (
            data.get("notes")
            or ""
        ).strip()

        price = (
            data.get("price")
            or ""
        ).strip()

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not student_name:
            return jsonify({
                "success": False,
                "error": "Student name is required.",
            }), 400

        if not email:
            return jsonify({
                "success": False,
                "error": "Email address is required.",
            }), 400

        if not phone:
            return jsonify({
                "success": False,
                "error": "Phone number is required.",
            }), 400

        if not lesson_type:
            return jsonify({
                "success": False,
                "error": "Lesson type is required.",
            }), 400

        if not package:
            return jsonify({
                "success": False,
                "error": "Package is required.",
            }), 400

        if not lesson_date:
            return jsonify({
                "success": False,
                "error": "Lesson date is required.",
            }), 400

        if not lesson_time:
            return jsonify({
                "success": False,
                "error": "Lesson time is required.",
            }), 400

        # ----------------------------------------------------
        # DATABASE
        # ----------------------------------------------------

        conn = get_db_connection()
        cursor = conn.cursor()

        # ----------------------------------------------------
        # CHECK EXISTING BOOKING
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT id
            FROM bookings
            WHERE lesson_date = %s
              AND lesson_time = %s
              AND status != 'cancelled'
            LIMIT 1
            """,
            (
                lesson_date,
                lesson_time,
            ),
        )

        existing_booking = cursor.fetchone()

        if existing_booking:

            return jsonify({
                "success": False,
                "error": (
                    "This lesson time is already booked. "
                    "Please choose another time."
                ),
            }), 409

        # ----------------------------------------------------
        # APPROVAL TOKEN
        # ----------------------------------------------------

        approval_token = (
            generate_approval_token()
        )

        # ----------------------------------------------------
        # CREATE BOOKING
        # ----------------------------------------------------

        created_at = datetime.now()

        cursor.execute(
            """
            INSERT INTO bookings (
                name,
                email,
                phone,
                lesson_type,
                package,
                lesson_date,
                lesson_time,
                payment_status,
                stripe_payment_id,
                status,
                reminder_sent,
                approval_token,
                created_at
            )
            VALUES (
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
                %s,
                %s
            )
            RETURNING id
            """,
            (
                student_name,
                email,
                phone,
                lesson_type,
                package,
                lesson_date,
                lesson_time,
                "pending",
                None,
                "pending",
                False,
                approval_token,
                created_at,
            ),
        )

        booking_id = cursor.fetchone()[0]

        conn.commit()

        # ----------------------------------------------------
        # BOOKING DICTIONARY
        # ----------------------------------------------------

        booking = {
            "id": booking_id,

            "name": student_name,

            "student_name": student_name,

            "parent_name": parent_name,

            "email": email,

            "phone": phone,

            "dob": dob,

            "age": age,

            "emergency_contact":
                emergency_contact,

            "emergency_phone":
                emergency_phone,

            "swimming_experience":
                swimming_experience,

            "lesson_type":
                lesson_type,

            "package":
                package,

            "lesson_date":
                lesson_date,

            "lesson_time":
                lesson_time,

            "price":
                price,

            "medical":
                medical,

            "notes":
                notes,

            "payment_status":
                "pending",

            "status":
                "pending",

            "approval_token":
                approval_token,

            "created_at":
                created_at,
        }

        print("========================================")
        print("BOOKING CREATED")
        print(
            "BOOKING ID:",
            booking_id,
        )
        print(
            "APPROVAL TOKEN PRESENT:",
            bool(approval_token),
        )
        print("========================================")

        # ----------------------------------------------------
        # SEND OWNER EMAIL
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

            print(
                "SENDING OWNER APPROVAL EMAIL..."
            )

            email_result = (
                email_service
                .send_admin_notification(
                    booking
                )
            )

            print(
                "OWNER EMAIL RESULT:",
                repr(email_result),
            )

            if not email_result:
                raise RuntimeError(
                    "send_admin_notification() "
                    "returned False."
                )

            print(
                f"OWNER APPROVAL EMAIL SENT "
                f"FOR BOOKING #{booking_id}"
            )

        except Exception as email_error:

            print(
                "========================================"
            )

            print(
                "OWNER EMAIL ERROR:"
            )

            print(
                repr(email_error)
            )

            print(
                "========================================"
            )

            return jsonify({
                "success": False,
                "booking_id": booking_id,
                "error": (
                    "Your booking was saved, "
                    "but the owner approval email "
                    "could not be sent."
                ),
            }), 500

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        return jsonify({
            "success": True,
            "booking_id": booking_id,
            "message": (
                "Booking request sent for approval."
            ),
        }), 201

    except Exception as error:

        if conn:

            try:
                conn.rollback()
            except Exception:
                pass

        print(
            "CREATE BOOKING ERROR:",
            repr(error),
        )

        return jsonify({
            "success": False,
            "error": (
                "Unable to create your booking. "
                "Please try again."
            ),
        }), 500

    finally:

        if conn:
            conn.close()


# ============================================================
# APPROVE BOOKING
# ============================================================

@booking_bp.route(
    "/approve-booking",
    methods=["GET"],
)
def approve_booking():

    conn = None

    try:

        token = (
            request.args.get(
                "token",
                "",
            ).strip()
        )

        booking_id = (
            request.args.get(
                "booking_id",
                "",
            ).strip()
        )

        print("========================================")
        print("APPROVE BOOKING REQUEST")
        print(
            "TOKEN PRESENT:",
            bool(token),
        )
        print(
            "BOOKING ID:",
            booking_id,
        )
        print("========================================")

        conn = get_db_connection()
        cursor = conn.cursor()

        # ----------------------------------------------------
        # FIND BY SECURE TOKEN
        # ----------------------------------------------------

        if token:

            cursor.execute(
                """
                SELECT *
                FROM bookings
                WHERE approval_token = %s
                LIMIT 1
                """,
                (token,),
            )

        # ----------------------------------------------------
        # BACKWARD COMPATIBILITY
        # ----------------------------------------------------

        elif booking_id:

            if not booking_id.isdigit():

                return (
                    "Invalid booking_id",
                    400,
                )

            cursor.execute(
                """
                SELECT *
                FROM bookings
                WHERE id = %s
                LIMIT 1
                """,
                (int(booking_id),),
            )

        else:

            return (
                "Invalid approval link",
                400,
            )

        booking_row = cursor.fetchone()

        if not booking_row:

            return (
                "Booking not found",
                404,
            )

        booking = row_to_dict(
            cursor,
            booking_row,
        )

        print(
            "FOUND BOOKING:",
            booking.get("id"),
        )

        # ----------------------------------------------------
        # ALREADY CONFIRMED
        # ----------------------------------------------------

        if (
            booking.get("status")
            == "confirmed"
        ):

            return render_template(
                "approval_result.html",
                success=True,
                title="Booking Already Confirmed",
                message=(
                    "This booking has already "
                    "been approved."
                ),
            )

        # ----------------------------------------------------
        # CANCELLED
        # ----------------------------------------------------

        if (
            booking.get("status")
            == "cancelled"
        ):

            return render_template(
                "approval_result.html",
                success=False,
                title="Booking Cancelled",
                message=(
                    "This booking has already "
                    "been cancelled."
                ),
            )

        # ----------------------------------------------------
        # CONFIRM BOOKING
        # ----------------------------------------------------

        cursor.execute(
            """
            UPDATE bookings
            SET status = 'confirmed'
            WHERE id = %s
            """,
            (booking["id"],),
        )

        conn.commit()

        booking["status"] = "confirmed"

        print(
            f"BOOKING #{booking['id']} "
            "CONFIRMED"
        )

        # ----------------------------------------------------
        # CUSTOMER APPROVAL EMAIL
        # ----------------------------------------------------

        try:

            if hasattr(
                email_service,
                "send_booking_approved",
            ):

                email_result = (
                    email_service
                    .send_booking_approved(
                        booking
                    )
                )

                print(
                    "CUSTOMER APPROVAL EMAIL RESULT:",
                    repr(email_result),
                )

            else:

                print(
                    "WARNING: "
                    "send_booking_approved() "
                    "does not exist."
                )

        except Exception as email_error:

            print(
                "CUSTOMER APPROVAL EMAIL ERROR:",
                repr(email_error),
            )

        # ----------------------------------------------------
        # SUCCESS PAGE
        # ----------------------------------------------------

        return render_template(
            "approval_result.html",
            success=True,
            title="Booking Approved!",
            message=(
                f"Booking #{booking['id']} "
                "has been successfully approved. "
                "The customer has been notified."
            ),
        )

    except Exception as error:

        if conn:

            try:
                conn.rollback()
            except Exception:
                pass

        print(
            "APPROVE BOOKING ERROR:",
            repr(error),
        )

        return render_template(
            "approval_result.html",
            success=False,
            title="Approval Error",
            message=(
                "We could not approve this booking. "
                "Please try again."
            ),
        ), 500

    finally:

        if conn:
            conn.close()


# ============================================================
# REJECT BOOKING
# ============================================================

@booking_bp.route(
    "/reject-booking",
    methods=["GET"],
)
def reject_booking():

    conn = None

    try:

        token = (
            request.args.get(
                "token",
                "",
            ).strip()
        )

        booking_id = (
            request.args.get(
                "booking_id",
                "",
            ).strip()
        )

        conn = get_db_connection()
        cursor = conn.cursor()

        # ----------------------------------------------------
        # FIND BY TOKEN
        # ----------------------------------------------------

        if token:

            cursor.execute(
                """
                SELECT *
                FROM bookings
                WHERE approval_token = %s
                LIMIT 1
                """,
                (token,),
            )

        # ----------------------------------------------------
        # OLD BOOKING ID
        # ----------------------------------------------------

        elif booking_id:

            if not booking_id.isdigit():

                return (
                    "Invalid booking_id",
                    400,
                )

            cursor.execute(
                """
                SELECT *
                FROM bookings
                WHERE id = %s
                LIMIT 1
                """,
                (int(booking_id),),
            )

        else:

            return (
                "Invalid approval link",
                400,
            )

        booking_row = cursor.fetchone()

        if not booking_row:

            return (
                "Booking not found",
                404,
            )

        booking = row_to_dict(
            cursor,
            booking_row,
        )

        # ----------------------------------------------------
        # ALREADY CANCELLED
        # ----------------------------------------------------

        if (
            booking.get("status")
            == "cancelled"
        ):

            return render_template(
                "approval_result.html",
                success=False,
                title="Booking Already Cancelled",
                message=(
                    "This booking has already "
                    "been cancelled."
                ),
            )

        # ----------------------------------------------------
        # CANCEL BOOKING
        # ----------------------------------------------------

        cursor.execute(
            """
            UPDATE bookings
            SET status = 'cancelled'
            WHERE id = %s
            """,
            (booking["id"],),
        )

        conn.commit()

        booking["status"] = "cancelled"

        print(
            f"BOOKING #{booking['id']} "
            "CANCELLED"
        )

        # ----------------------------------------------------
        # CUSTOMER REJECTION EMAIL
        # ----------------------------------------------------

        try:

            if hasattr(
                email_service,
                "send_booking_rejected",
            ):

                email_result = (
                    email_service
                    .send_booking_rejected(
                        booking
                    )
                )

                print(
                    "CUSTOMER REJECTION EMAIL RESULT:",
                    repr(email_result),
                )

            else:

                print(
                    "WARNING: "
                    "send_booking_rejected() "
                    "does not exist."
                )

        except Exception as email_error:

            print(
                "CUSTOMER REJECTION EMAIL ERROR:",
                repr(email_error),
            )

        # ----------------------------------------------------
        # SUCCESS PAGE
        # ----------------------------------------------------

        return render_template(
            "approval_result.html",
            success=True,
            title="Booking Cancelled",
            message=(
                f"Booking #{booking['id']} "
                "has been cancelled. "
                "The customer has been notified."
            ),
        )

    except Exception as error:

        if conn:

            try:
                conn.rollback()
            except Exception:
                pass

        print(
            "REJECT BOOKING ERROR:",
            repr(error),
        )

        return render_template(
            "approval_result.html",
            success=False,
            title="Cancellation Error",
            message=(
                "We could not cancel this booking. "
                "Please try again."
            ),
        ), 500

    finally:

        if conn:
            conn.close()


# ============================================================
# BOOKED SLOTS
# ============================================================

@booking_bp.route(
    "/booked-slots",
    methods=["GET"],
)
def booked_slots():

    conn = None

    try:

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                lesson_date,
                lesson_time
            FROM bookings
            WHERE status != 'cancelled'
            ORDER BY lesson_date, lesson_time
            """
        )

        rows = cursor.fetchall()

        slots = []

        for row in rows:

            item = row_to_dict(
                cursor,
                row,
            )

            slots.append({
                "date": str(
                    item.get(
                        "lesson_date"
                    )
                ),

                "time": str(
                    item.get(
                        "lesson_time"
                    )
                ),
            })

        return jsonify(slots)

    except Exception as error:

        print(
            "BOOKED SLOTS ERROR:",
            repr(error),
        )

        return jsonify({
            "success": False,
            "error":
                "Unable to load booked slots.",
        }), 500

    finally:

        if conn:
            conn.close()