from flask import (
    Blueprint,
    render_template,
    jsonify,
    request,
    session,
    redirect,
    url_for
)

from database import get_db_connection
from config import Config

from datetime import datetime

import psycopg2.extras
import threading
import traceback


# ============================================================
# BLUEPRINT
# ============================================================

admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin"
)


# ============================================================
# LOGIN CHECK
# ============================================================

def admin_required():
    """
    Check whether the administrator completed the new
    email-only two-factor authentication flow.

    admin_auth.py sets this flag only after:
      1. Username/password are correct.
      2. The 6-digit code sent to the owner email is verified.
    """
    return session.get(
        "admin_authenticated",
        False
    )


# ============================================================
# AUTHENTICATION
# ============================================================
#
# Authentication is handled by admin_auth.py.
# This blueprint intentionally does NOT define /admin/login.
#
# ============================================================

# ============================================================
# ADMIN DASHBOARD
# ============================================================

@admin_bp.route(
    "/"
)
def admin_dashboard():

    if not admin_required():

        return redirect(
            url_for(
                "admin.admin_login"
            )
        )


    conn = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        )


        # ====================================================
        # ALL BOOKINGS
        # ====================================================

        cursor.execute(
            """
            SELECT *
            FROM bookings
            ORDER BY
                lesson_date ASC,
                lesson_time ASC,
                created_at DESC
            """
        )

        bookings = cursor.fetchall()


        # ====================================================
        # TODAY
        # ====================================================

        today = datetime.now().strftime(
            "%Y-%m-%d"
        )


        # ====================================================
        # TODAY'S CONFIRMED LESSONS
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM bookings
            WHERE lesson_date = %s
              AND status = 'confirmed'
            """,
            (today,)
        )

        today_lessons = cursor.fetchone()["count"]


        # ====================================================
        # PENDING APPROVALS
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM bookings
            WHERE status = 'pending'
            """
        )

        pending_approvals = cursor.fetchone()["count"]


        # ====================================================
        # PENDING PAYMENTS
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM bookings
            WHERE status = 'confirmed'
              AND payment_status = 'pending'
            """
        )

        pending_payments = cursor.fetchone()["count"]


        # ====================================================
        # CONFIRMED LESSONS
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM bookings
            WHERE status = 'confirmed'
            """
        )

        confirmed_lessons = cursor.fetchone()["count"]


        # ====================================================
        # REJECTED BOOKINGS
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM bookings
            WHERE status = 'rejected'
            """
        )

        rejected_bookings = cursor.fetchone()["count"]


        # ====================================================
        # PAID BOOKINGS
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM bookings
            WHERE payment_status = 'paid'
            """
        )

        paid_bookings = cursor.fetchone()["count"]


        # ====================================================
        # REVENUE
        # ====================================================
        #
        # price is stored as "$80.00".
        #
        # PostgreSQL removes the "$" and converts it to numeric.
        # ====================================================

        cursor.execute(
            """
            SELECT
                COALESCE(
                    SUM(
                        CAST(
                            REPLACE(price, '$', '')
                            AS NUMERIC
                        )
                    ),
                    0
                ) AS revenue
            FROM bookings
            WHERE payment_status = 'paid'
            """
        )

        revenue_value = (
            cursor.fetchone()["revenue"]
            or 0
        )


        revenue = (
            f"{float(revenue_value):,.2f}"
        )


        # ====================================================
        # PAY LATER COUNT
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM bookings
            WHERE status = 'confirmed'
              AND payment_method = 'cash_or_zelle'
              AND payment_status = 'pending'
            """
        )

        pay_later_bookings = (
            cursor.fetchone()["count"]
        )


        return render_template(
            "admin.html",

            bookings=bookings,

            today_lessons=today_lessons,

            pending_approvals=pending_approvals,

            pending_payments=pending_payments,

            confirmed_lessons=confirmed_lessons,

            rejected_bookings=rejected_bookings,

            paid_bookings=paid_bookings,

            pay_later_bookings=pay_later_bookings,

            revenue=revenue
        )


    except Exception as error:

        print(
            "ADMIN DASHBOARD ERROR:",
            repr(error)
        )

        return (
            "Unable to load the admin dashboard."
        ), 500


    finally:

        if conn:

            conn.close()


# ============================================================
# GET SINGLE BOOKING
# ============================================================

@admin_bp.route(
    "/booking/<int:id>",
    methods=["GET"]
)
def get_booking(id):

    if not admin_required():

        return jsonify({
            "success": False,
            "error": "Unauthorized"
        }), 401


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
            (id,)
        )


        booking = cursor.fetchone()


        if not booking:

            return jsonify({
                "success": False,
                "error": "Booking not found."
            }), 404


        return jsonify({
            "success": True,
            "booking": dict(booking)
        })


    except Exception as error:

        print(
            "GET BOOKING ERROR:",
            repr(error)
        )

        return jsonify({
            "success": False,
            "error": "Unable to load booking."
        }), 500


    finally:

        if conn:

            conn.close()


# ============================================================
# EMAIL HELPERS
# ============================================================

def _send_approval_email_background(booking):
    """Send the approval email without blocking the admin request."""
    try:
        from email_service import send_user_approved_email

        result = send_user_approved_email(dict(booking))

        print(
            "APPROVAL EMAIL BACKGROUND RESULT:",
            repr(result)
        )

    except Exception as email_error:
        print(
            "APPROVAL EMAIL BACKGROUND ERROR:",
            repr(email_error)
        )
        traceback.print_exc()


def _send_rejection_email_background(booking):
    """Send the rejection email without blocking the admin request."""
    try:
        from email_service import send_user_rejected_email

        result = send_user_rejected_email(dict(booking))

        print(
            "REJECTION EMAIL BACKGROUND RESULT:",
            repr(result)
        )

    except Exception as email_error:
        print(
            "REJECTION EMAIL BACKGROUND ERROR:",
            repr(email_error)
        )
        traceback.print_exc()


def _start_background_email(target, booking):
    """Start a daemon thread so email cannot freeze the browser request."""
    thread = threading.Thread(
        target=target,
        args=(dict(booking),),
        daemon=True,
        name="millrod-admin-email"
    )
    thread.start()
    return thread


# ============================================================
# UPDATE BOOKING STATUS
# ============================================================

@admin_bp.route(
    "/update-status/<int:id>",
    methods=["POST"]
)
def update_status(id):

    if not admin_required():
        return jsonify({
            "success": False,
            "error": "Unauthorized"
        }), 401

    data = request.get_json(silent=True) or {}
    status = str(data.get("status", "")).strip().lower()

    if status not in [
        "pending",
        "confirmed",
        "rejected"
    ]:
        return jsonify({
            "success": False,
            "error": "Invalid booking status."
        }), 400

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
            (id,)
        )

        booking = cursor.fetchone()

        if not booking:
            return jsonify({
                "success": False,
                "error": "Booking not found."
            }), 404

        old_status = booking["status"]

        # ----------------------------------------------------
        # PREVENT INVALID APPROVAL
        # ----------------------------------------------------
        if old_status == "rejected" and status == "confirmed":
            return jsonify({
                "success": False,
                "error": (
                    "A rejected booking cannot be approved "
                    "from the dashboard."
                )
            }), 400

        # ----------------------------------------------------
        # UPDATE STATUS
        # ----------------------------------------------------
        if status == "confirmed":
            cursor.execute(
                """
                UPDATE bookings
                SET
                    status = 'confirmed',
                    payment_status = CASE
                        WHEN payment_status = 'paid'
                        THEN payment_status
                        ELSE 'pending'
                    END
                WHERE id = %s
                RETURNING *
                """,
                (id,)
            )

        elif status == "rejected":
            cursor.execute(
                """
                UPDATE bookings
                SET status = 'rejected'
                WHERE id = %s
                RETURNING *
                """,
                (id,)
            )

        else:
            cursor.execute(
                """
                UPDATE bookings
                SET status = 'pending'
                WHERE id = %s
                RETURNING *
                """,
                (id,)
            )

        updated_booking = cursor.fetchone()

        if not updated_booking:
            conn.rollback()
            return jsonify({
                "success": False,
                "error": "The booking could not be updated."
            }), 500

        # IMPORTANT:
        # Commit BEFORE starting email. The browser gets a successful
        # response immediately and the email can never hold the DB lock.
        conn.commit()

        booking_dict = dict(updated_booking)

        # ----------------------------------------------------
        # SEND EMAIL IN BACKGROUND
        # ----------------------------------------------------
        if status == "confirmed":
            _start_background_email(
                _send_approval_email_background,
                booking_dict
            )
            email_message = (
                "Approval saved. The customer approval email "
                "is being sent."
            )

        elif status == "rejected":
            _start_background_email(
                _send_rejection_email_background,
                booking_dict
            )
            email_message = (
                "Rejection saved. The customer notification "
                "is being sent."
            )

        else:
            email_message = "Booking returned to pending."

        return jsonify({
            "success": True,
            "booking": booking_dict,
            "email_queued": status in ["confirmed", "rejected"],
            "message": (
                "Booking approved successfully. "
                "Customer email queued."
                if status == "confirmed"
                else email_message
            )
        }), 200

    except Exception as error:
        if conn:
            conn.rollback()

        print(
            "UPDATE BOOKING STATUS ERROR:",
            repr(error)
        )
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": "Unable to update the booking."
        }), 500

    finally:
        if conn:
            conn.close()


# ============================================================
# RESEND APPROVAL EMAIL
# ============================================================

@admin_bp.route(
    "/resend-approval/<int:id>",
    methods=["POST"]
)
def resend_approval_email(id):

    if not admin_required():
        return jsonify({
            "success": False,
            "error": "Unauthorized"
        }), 401

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
            (id,)
        )
        booking = cursor.fetchone()

        if not booking:
            return jsonify({
                "success": False,
                "error": "Booking not found."
            }), 404

        if booking["status"] != "confirmed":
            return jsonify({
                "success": False,
                "error": "Only confirmed bookings can receive an approval email."
            }), 400

        _start_background_email(
            _send_approval_email_background,
            dict(booking)
        )

        return jsonify({
            "success": True,
            "email_queued": True,
            "message": "Approval email queued for delivery."
        })

    except Exception as error:
        print(
            "RESEND APPROVAL EMAIL ERROR:",
            repr(error)
        )
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": "Unable to queue the approval email."
        }), 500

    finally:
        if conn:
            conn.close()


# ============================================================
# RESEND REJECTION EMAIL
# ============================================================

@admin_bp.route(
    "/resend-rejection/<int:id>",
    methods=["POST"]
)
def resend_rejection_email(id):

    if not admin_required():
        return jsonify({
            "success": False,
            "error": "Unauthorized"
        }), 401

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
            (id,)
        )
        booking = cursor.fetchone()

        if not booking:
            return jsonify({
                "success": False,
                "error": "Booking not found."
            }), 404

        if booking["status"] != "rejected":
            return jsonify({
                "success": False,
                "error": "Only rejected bookings can receive a rejection email."
            }), 400

        _start_background_email(
            _send_rejection_email_background,
            dict(booking)
        )

        return jsonify({
            "success": True,
            "email_queued": True,
            "message": "Rejection email queued for delivery."
        })

    except Exception as error:
        print(
            "RESEND REJECTION EMAIL ERROR:",
            repr(error)
        )
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": "Unable to queue the rejection email."
        }), 500

    finally:
        if conn:
            conn.close()


# ============================================================
# UPDATE PAYMENT STATUS
# ============================================================

@admin_bp.route(
    "/update-payment/<int:id>",
    methods=["POST"]
)
def update_payment(id):

    if not admin_required():
        return jsonify({
            "success": False,
            "error": "Unauthorized"
        }), 401

    data = request.get_json(silent=True) or {}
    payment_status = str(
        data.get("payment_status", "")
    ).strip().lower()

    if payment_status not in ["paid", "pending"]:
        return jsonify({
            "success": False,
            "error": "Invalid payment status."
        }), 400

    conn = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        )

        cursor.execute(
            """
            UPDATE bookings
            SET payment_status = %s
            WHERE id = %s
            RETURNING *
            """,
            (payment_status, id)
        )

        booking = cursor.fetchone()

        if not booking:
            return jsonify({
                "success": False,
                "error": "Booking not found."
            }), 404

        conn.commit()

        return jsonify({
            "success": True,
            "booking": dict(booking),
            "message": (
                "Payment marked as paid."
                if payment_status == "paid"
                else "Payment returned to pending."
            )
        })

    except Exception as error:
        if conn:
            conn.rollback()

        print(
            "UPDATE PAYMENT ERROR:",
            repr(error)
        )
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": "Unable to update payment status."
        }), 500

    finally:
        if conn:
            conn.close()


# ============================================================
# CANCEL / REJECT BOOKING
# ============================================================

@admin_bp.route(
    "/delete/<int:id>",
    methods=["DELETE"]
)
def delete_booking(id):

    if not admin_required():
        return jsonify({
            "success": False,
            "error": "Unauthorized"
        }), 401

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
            (id,)
        )

        booking = cursor.fetchone()

        if not booking:
            return jsonify({
                "success": False,
                "error": "Booking not found."
            }), 404

        cursor.execute(
            """
            UPDATE bookings
            SET status = 'rejected'
            WHERE id = %s
            RETURNING *
            """,
            (id,)
        )

        booking = cursor.fetchone()
        conn.commit()

        _start_background_email(
            _send_rejection_email_background,
            dict(booking)
        )

        return jsonify({
            "success": True,
            "email_queued": True,
            "message": "Booking rejected successfully."
        })

    except Exception as error:
        if conn:
            conn.rollback()

        print(
            "REJECT BOOKING ERROR:",
            repr(error)
        )
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": "Unable to reject booking."
        }), 500

    finally:
        if conn:
            conn.close()
