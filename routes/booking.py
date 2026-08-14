print("Booking blueprint LOADED")

from flask import Blueprint, request, jsonify, redirect
from database import get_db_connection
import email_service
import stripe
import os
import psycopg2

booking_bp = Blueprint(
    "booking",
    __name__,
    url_prefix="/api"
)

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def dict_row(row):
    """Convert psycopg2 row (tuple) into dict using cursor.description."""
    if row is None:
        return None
    return {desc[0]: row[i] for i, desc in enumerate(row)}

def safe_price_to_cents(price_str):
    """Convert '$50' or '50' or '50.00' into cents."""
    cleaned = price_str.replace("$", "").strip()
    return int(float(cleaned) * 100)

def first_nonempty(d, *keys):
    """Return first non-empty value from multiple possible keys."""
    for k in keys:
        v = d.get(k)
        if v is not None and str(v).strip() != "":
            return str(v).strip()
    return None

def get_conn():
    return get_db_connection()

# ---------------------------------------------------------
# DEBUG ROUTES
# ---------------------------------------------------------

@booking_bp.route("/debug")
def debug():
    return "Booking blueprint is loaded!"

@booking_bp.route("/debug-approve")
def debug_approve():
    return "Approve route is registered!"

# ---------------------------------------------------------
# CREATE BOOKING
# ---------------------------------------------------------

@booking_bp.route("/create-booking", methods=["POST"])
def create_booking():
    conn = None

    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No booking data received"}), 400

        # Extract fields
        lesson_date = first_nonempty(data, "lesson_date", "date", "lessonDate")
        lesson_time = first_nonempty(data, "lesson_time", "time", "lessonTime")
        name = first_nonempty(data, "name", "full_name", "student_name", "first_name")
        email = first_nonempty(data, "email", "email_address")
        phone = first_nonempty(data, "phone", "phone_number")
        lesson_type = first_nonempty(data, "lesson_type", "lessonType")
        package = first_nonempty(data, "package", "package_type")
        price = first_nonempty(data, "price")

        required = {
            "name": name,
            "email": email,
            "phone": phone,
            "lesson_type": lesson_type,
            "package": package,
            "price": price,
            "lesson_date": lesson_date,
            "lesson_time": lesson_time
        }

        # Validate required fields
        for key, value in required.items():
            if not value:
                return jsonify({"success": False, "error": f"Missing {key}"}), 400

        conn = get_conn()
        cursor = conn.cursor()

        # Check slot availability
        cursor.execute(
            """
            SELECT id FROM bookings
            WHERE lesson_date = %s
            AND lesson_time = %s
            AND status IN ('pending','confirmed')
            """,
            (lesson_date, lesson_time)
        )

        if cursor.fetchone():
            return jsonify({
                "success": False,
                "error": "This time is already reserved. Please choose another time."
            }), 409

        # Insert booking (PostgreSQL)
        cursor.execute(
            """
            INSERT INTO bookings
            (
                name, email, phone,
                lesson_type, package, price,
                lesson_date, lesson_time,
                payment_method, payment_status, status
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (
                name, email, phone,
                lesson_type, package, price,
                lesson_date, lesson_time,
                "cash_or_zelle", "pending", "pending"
            )
        )

        booking_id = cursor.fetchone()[0]
        conn.commit()

        # Fetch booking
        cursor.execute("SELECT * FROM bookings WHERE id = %s", (booking_id,))
        booking = dict_row(cursor.fetchone())

        # Send emails
        try:
            email_service.send_booking_confirmation(
                customer_email=booking["email"],
                customer_name=booking["name"],
                lesson_type=booking["lesson_type"],
                package=booking["package"],
                lesson_date=booking["lesson_date"],
                lesson_time=booking["lesson_time"],
                payment_status=booking["payment_status"],
                price=booking["price"]
            )

            email_service.send_admin_notification(booking)

        except Exception as e:
            print("EMAIL FAILED:", repr(e))

        return jsonify({
            "success": True,
            "booking_id": booking_id,
            "message": "Lesson reserved successfully! Please pay Cash or Zelle when you arrive."
        })

    except Exception as e:
        if conn:
            conn.rollback()
        print("BOOKING ERROR:", repr(e))
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        if conn:
            conn.close()

# ---------------------------------------------------------
# CALENDAR BOOKINGS
# ---------------------------------------------------------

@booking_bp.route("/bookings")
def get_bookings():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT lesson_date, lesson_time
        FROM bookings
        WHERE status IN ('pending','confirmed')
        """
    )

    rows = cursor.fetchall()
    conn.close()

    return jsonify([
        {
            "title": "Booked",
            "start": f"{row[0]}T{row[1]}"
        }
        for row in rows
    ])

# ---------------------------------------------------------
# BOOKED SLOTS
# ---------------------------------------------------------

@booking_bp.route("/booked-slots")
def booked_slots():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT lesson_date, lesson_time
        FROM bookings
        WHERE status IN ('pending','confirmed')
        """
    )

    rows = cursor.fetchall()
    conn.close()

    return jsonify([
        {
            "date": row[0],
            "time": row[1]
        }
        for row in rows
    ])

# ---------------------------------------------------------
# OWNER APPROVES BOOKING
# ---------------------------------------------------------

DOMAIN = os.getenv("DOMAIN")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
stripe.api_key = STRIPE_SECRET_KEY

@booking_bp.route("/approve-booking")
def approve_booking():
    try:
        booking_id = int(request.args.get("booking_id", ""))
    except ValueError:
        return "Invalid booking_id."

    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM bookings WHERE id = %s", (booking_id,))
    booking = cursor.fetchone()

    if not booking:
        conn.close()
        return "Booking not found."

    cursor.execute("UPDATE bookings SET status = 'confirmed' WHERE id = %s", (booking_id,))
    conn.commit()
    conn.close()

    email_service.send_user_approved_email(dict_row(booking))

    return "<h2>Booking Approved ✔</h2><p>The user has been notified.</p>"

# ---------------------------------------------------------
# OWNER REJECTS BOOKING
# ---------------------------------------------------------

@booking_bp.route("/reject-booking")
def reject_booking():
    try:
        booking_id = int(request.args.get("booking_id", ""))
    except ValueError:
        return "Invalid booking_id."

    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM bookings WHERE id = %s", (booking_id,))
    booking = cursor.fetchone()

    if not booking:
        conn.close()
        return "Booking not found."

    cursor.execute("UPDATE bookings SET status = 'rejected' WHERE id = %s", (booking_id,))
    conn.commit()
    conn.close()

    email_service.send_user_rejected_email(dict_row(booking))

    return "<h2>Booking Rejected ✖</h2>"

# ---------------------------------------------------------
# PAY NOW (STRIPE)
# ---------------------------------------------------------

@booking_bp.route("/pay-now")
def pay_now():
    try:
        booking_id = int(request.args.get("booking_id", ""))
    except ValueError:
        return "Invalid booking_id."

    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM bookings WHERE id = %s", (booking_id,))
    booking = dict_row(cursor.fetchone())
    conn.close()

    if not booking:
        return "Booking not found."

    price_cents = safe_price_to_cents(booking["price"])

    session = stripe.checkout.Session.create(
        mode="payment",
        success_url=f"{DOMAIN}/payment-success",
        cancel_url=f"{DOMAIN}/payment-cancel",
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"{booking['lesson_type']} – {booking['package']}"
                    },
                    "unit_amount": price_cents,
                },
                "quantity": 1,
            }
        ],
    )

    return redirect(session.url)

# ---------------------------------------------------------
# PAY LATER
# ---------------------------------------------------------

@booking_bp.route("/pay-later")
def pay_later():
    return """
    <h2>Pay Later Confirmed</h2>
    <p>You may pay Cash or Zelle when you arrive.</p>
    """
