# ============================================================
# MILLROD SWIM ACADEMY - ADMIN BLUEPRINT
# ============================================================
#
# IMPORTANT:
# Authentication is handled by admin_auth.py.
#
# This blueprint intentionally does NOT define:
#   /admin/login
#   /admin/logout
#
# The administrator must complete:
#   username/password -> email 2FA -> admin_authenticated=True
#
# Features:
#   - Dashboard statistics
#   - Booking list
#   - Single booking details
#   - Safe booking approval/rejection
#   - Slot-conflict protection
#   - Customer approval/rejection emails
#   - Manual payment status management
#   - Resend approval/rejection emails
#   - Dashboard JSON statistics
#   - Booking JSON API
#   - Safe error handling
# ============================================================

from datetime import datetime

import psycopg2.extras

from flask import (
    Blueprint,
    jsonify,
    render_template,
    request,
    session,
    redirect,
    url_for,
)

from database import get_db_connection


# ============================================================
# BLUEPRINT
# ============================================================

admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin",
)


# ============================================================
# AUTHENTICATION
# ============================================================

def admin_required():
    """
    The new email-only 2FA system sets this flag only after
    the owner successfully verifies the email code.

    app.py also enforces the 5-minute inactivity timeout.
    """
    return session.get(
        "admin_authenticated",
        False,
    ) is True


def unauthorized():
    """
    JSON response for protected API requests.
    """
    return jsonify({
        "success": False,
        "error": "Unauthorized. Please sign in again.",
    }), 401


# ============================================================
# HELPERS
# ============================================================

def _get_booking(cursor, booking_id):
    cursor.execute(
        """
        SELECT *
        FROM bookings
        WHERE id = %s
        LIMIT 1
        """,
        (booking_id,),
    )

    return cursor.fetchone()


def _send_approval_email(booking):
    try:
        from email_service import send_user_approved_email

        send_user_approved_email(booking)

        return {
            "success": True,
            "error": None,
        }

    except Exception as error:
        print(
            "APPROVAL EMAIL ERROR:",
            repr(error),
        )

        return {
            "success": False,
            "error": str(error),
        }


def _send_rejection_email(booking):
    try:
        from email_service import send_user_rejected_email

        send_user_rejected_email(booking)

        return {
            "success": True,
            "error": None,
        }

    except Exception as error:
        print(
            "REJECTION EMAIL ERROR:",
            repr(error),
        )

        return {
            "success": False,
            "error": str(error),
        }


def _send_payment_email_if_available(booking):
    """
    Optional payment email hook.

    The existing project already sends the approval email.
    We do not assume a payment-email function exists, so this
    function safely looks for it and simply skips it when it
    isn't available.

    This prevents an admin payment update from breaking the
    booking workflow.
    """

    try:
        from email_service import send_payment_confirmation_email

    except ImportError:
        return {
            "success": True,
            "skipped": True,
        }

    try:
        send_payment_confirmation_email(booking)

        return {
            "success": True,
            "skipped": False,
        }

    except Exception as error:
        print(
            "PAYMENT EMAIL ERROR:",
            repr(error),
        )

        return {
            "success": False,
            "skipped": False,
            "error": str(error),
        }


def _booking_conflict(cursor, booking):
    """
    Check whether another confirmed booking already occupies
    the exact lesson date/time.

    This protects the calendar from accidentally approving the
    same slot twice.
    """

    lesson_date = booking.get("lesson_date")
    lesson_time = booking.get("lesson_time")
    booking_id = booking.get("id")

    if not lesson_date or not lesson_time:
        return False, None

    cursor.execute(
        """
        SELECT id, name, lesson_type, package
        FROM bookings
        WHERE lesson_date = %s
          AND lesson_time = %s
          AND status = 'confirmed'
          AND id <> %s
        LIMIT 1
        """,
        (
            lesson_date,
            lesson_time,
            booking_id,
        ),
    )

    conflict = cursor.fetchone()

    return (
        bool(conflict),
        conflict,
    )


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@admin_bp.route("/")
def admin_dashboard():

    if not admin_required():
        return redirect(
            url_for("admin_auth.admin_login")
        )

    conn = None

    try:
        conn = get_db_connection()

        cursor = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        )

        # ----------------------------------------------------
        # ALL BOOKINGS
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # TODAY
        # ----------------------------------------------------

        today = datetime.now().strftime(
            "%Y-%m-%d"
        )

        # ----------------------------------------------------
        # TODAY'S CONFIRMED LESSONS
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM bookings
            WHERE lesson_date = %s
              AND status = 'confirmed'
            """,
            (today,),
        )

        today_lessons = cursor.fetchone()["count"]

        # ----------------------------------------------------
        # PENDING APPROVALS
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM bookings
            WHERE status = 'pending'
            """
        )

        pending_approvals = cursor.fetchone()["count"]

        # ----------------------------------------------------
        # PENDING PAYMENTS
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM bookings
            WHERE status = 'confirmed'
              AND payment_status = 'pending'
            """
        )

        pending_payments = cursor.fetchone()["count"]

        # ----------------------------------------------------
        # CONFIRMED LESSONS
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM bookings
            WHERE status = 'confirmed'
            """
        )

        confirmed_lessons = cursor.fetchone()["count"]

        # ----------------------------------------------------
        # REJECTED BOOKINGS
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM bookings
            WHERE status = 'rejected'
            """
        )

        rejected_bookings = cursor.fetchone()["count"]

        # ----------------------------------------------------
        # PAID BOOKINGS
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM bookings
            WHERE payment_status = 'paid'
            """
        )

        paid_bookings = cursor.fetchone()["count"]

        # ----------------------------------------------------
        # REVENUE
        # ----------------------------------------------------

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

        revenue = f"{_safe_float(revenue_value):,.2f}"

        # ----------------------------------------------------
        # PAY LATER
        # ----------------------------------------------------

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
            revenue=revenue,
        )

    except Exception as error:

        print(
            "ADMIN DASHBOARD ERROR:",
            repr(error),
        )

        return (
            "Unable to load the admin dashboard.",
            500,
        )

    finally:

        if conn:
            conn.close()


# ============================================================
# DASHBOARD STATS API
# ============================================================

@admin_bp.route(
    "/api/stats",
    methods=["GET"],
)
def dashboard_stats():

    if not admin_required():
        return unauthorized()

    conn = None

    try:
        conn = get_db_connection()

        cursor = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        )

        today = datetime.now().strftime(
            "%Y-%m-%d"
        )

        queries = {
            "today_lessons": """
                SELECT COUNT(*)
                FROM bookings
                WHERE lesson_date = %s
                  AND status = 'confirmed'
            """,

            "pending_approvals": """
                SELECT COUNT(*)
                FROM bookings
                WHERE status = 'pending'
            """,

            "pending_payments": """
                SELECT COUNT(*)
                FROM bookings
                WHERE status = 'confirmed'
                  AND payment_status = 'pending'
            """,

            "confirmed_lessons": """
                SELECT COUNT(*)
                FROM bookings
                WHERE status = 'confirmed'
            """,

            "rejected_bookings": """
                SELECT COUNT(*)
                FROM bookings
                WHERE status = 'rejected'
            """,

            "paid_bookings": """
                SELECT COUNT(*)
                FROM bookings
                WHERE payment_status = 'paid'
            """,

            "pay_later_bookings": """
                SELECT COUNT(*)
                FROM bookings
                WHERE status = 'confirmed'
                  AND payment_method = 'cash_or_zelle'
                  AND payment_status = 'pending'
            """,
        }

        stats = {}

        for name, sql in queries.items():

            if name == "today_lessons":
                cursor.execute(
                    sql,
                    (today,),
                )
            else:
                cursor.execute(sql)

            stats[name] = (
                cursor.fetchone()["count"]
            )

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

        stats["revenue"] = _safe_float(
            cursor.fetchone()["revenue"]
            or 0
        )

        return jsonify({
            "success": True,
            "stats": stats,
        })

    except Exception as error:

        print(
            "ADMIN STATS ERROR:",
            repr(error),
        )

        return jsonify({
            "success": False,
            "error": "Unable to load dashboard statistics.",
        }), 500

    finally:

        if conn:
            conn.close()


# ============================================================
# GET SINGLE BOOKING
# ============================================================

@admin_bp.route(
    "/booking/<int:id>",
    methods=["GET"],
)
def get_booking(id):

    if not admin_required():
        return unauthorized()

    conn = None

    try:
        conn = get_db_connection()

        cursor = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        )

        booking = _get_booking(
            cursor,
            id,
        )

        if not booking:
            return jsonify({
                "success": False,
                "error": "Booking not found.",
            }), 404

        return jsonify({
            "success": True,
            "booking": dict(booking),
        })

    except Exception as error:

        print(
            "GET BOOKING ERROR:",
            repr(error),
        )

        return jsonify({
            "success": False,
            "error": "Unable to load booking.",
        }), 500

    finally:

        if conn:
            conn.close()


# ============================================================
# UPDATE BOOKING STATUS
# ============================================================

@admin_bp.route(
    "/update-status/<int:id>",
    methods=["POST"],
)
def update_status(id):

    if not admin_required():
        return unauthorized()

    data = request.get_json(
        silent=True
    ) or {}

    status = (
        str(
            data.get("status", "")
        )
        .strip()
        .lower()
    )

    allowed_statuses = {
        "pending",
        "confirmed",
        "rejected",
    }

    if status not in allowed_statuses:
        return jsonify({
            "success": False,
            "error": "Invalid booking status.",
        }), 400

    conn = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        )

        booking = _get_booking(
            cursor,
            id,
        )

        if not booking:
            return jsonify({
                "success": False,
                "error": "Booking not found.",
            }), 404

        old_status = booking["status"]

        # ----------------------------------------------------
        # APPROVAL
        # ----------------------------------------------------

        if status == "confirmed":

            if old_status == "rejected":
                return jsonify({
                    "success": False,
                    "error": (
                        "A rejected booking cannot be "
                        "approved from the dashboard."
                    ),
                }), 400

            # Prevent double-booking a confirmed time slot.
            conflict, conflicting_booking = (
                _booking_conflict(
                    cursor,
                    booking,
                )
            )

            if conflict:

                return jsonify({
                    "success": False,
                    "error": (
                        "This time slot is already confirmed "
                        "for another booking."
                    ),
                    "conflict": (
                        dict(conflicting_booking)
                        if conflicting_booking
                        else None
                    ),
                }), 409

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
                (id,),
            )

        # ----------------------------------------------------
        # REJECTION
        # ----------------------------------------------------

        elif status == "rejected":

            if old_status == "rejected":
                return jsonify({
                    "success": True,
                    "booking": dict(booking),
                    "message": "Booking is already rejected.",
                    "email_sent": False,
                })

            cursor.execute(
                """
                UPDATE bookings
                SET status = 'rejected'
                WHERE id = %s
                RETURNING *
                """,
                (id,),
            )

        # ----------------------------------------------------
        # RETURN TO PENDING
        # ----------------------------------------------------

        else:

            cursor.execute(
                """
                UPDATE bookings
                SET status = 'pending'
                WHERE id = %s
                RETURNING *
                """,
                (id,),
            )

        updated_booking = cursor.fetchone()

        conn.commit()

        # ----------------------------------------------------
        # CUSTOMER EMAIL
        # ----------------------------------------------------

        email_result = {
            "success": True,
            "skipped": True,
        }

        if status == "confirmed":

            email_result = _send_approval_email(
                updated_booking
            )

        elif status == "rejected":

            email_result = _send_rejection_email(
                updated_booking
            )

        return jsonify({
            "success": True,
            "booking": dict(updated_booking),
            "email_sent": (
                email_result.get("success", False)
            ),
            "email_error": email_result.get("error"),
            "message": (
                "Booking approved successfully."
                if status == "confirmed"
                else
                "Booking rejected successfully."
                if status == "rejected"
                else
                "Booking returned to pending."
            ),
        })

    except Exception as error:

        if conn:
            conn.rollback()

        print(
            "UPDATE BOOKING STATUS ERROR:",
            repr(error),
        )

        return jsonify({
            "success": False,
            "error": (
                "Unable to update the booking. "
                "No database changes were saved."
            ),
        }), 500

    finally:

        if conn:
            conn.close()


# ============================================================
# UPDATE PAYMENT STATUS
# ============================================================

@admin_bp.route(
    "/update-payment/<int:id>",
    methods=["POST"],
)
def update_payment(id):

    if not admin_required():
        return unauthorized()

    data = request.get_json(
        silent=True
    ) or {}

    payment_status = (
        str(
            data.get(
                "payment_status",
                "",
            )
        )
        .strip()
        .lower()
    )

    if payment_status not in {
        "pending",
        "paid",
    }:
        return jsonify({
            "success": False,
            "error": (
                "Payment status must be "
                "'pending' or 'paid'."
            ),
        }), 400

    conn = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        )

        booking = _get_booking(
            cursor,
            id,
        )

        if not booking:
            return jsonify({
                "success": False,
                "error": "Booking not found.",
            }), 404

        if booking["status"] != "confirmed":
            return jsonify({
                "success": False,
                "error": (
                    "Payment status can only be changed "
                    "for a confirmed booking."
                ),
            }), 400

        cursor.execute(
            """
            UPDATE bookings
            SET payment_status = %s
            WHERE id = %s
            RETURNING *
            """,
            (
                payment_status,
                id,
            ),
        )

        updated_booking = cursor.fetchone()

        conn.commit()

        email_result = {
            "success": True,
            "skipped": True,
        }

        if payment_status == "paid":
            email_result = (
                _send_payment_email_if_available(
                    updated_booking
                )
            )

        return jsonify({
            "success": True,
            "booking": dict(updated_booking),
            "email_sent": (
                email_result.get("success", False)
            ),
            "message": (
                "Payment marked as paid."
                if payment_status == "paid"
                else
                "Payment returned to pending."
            ),
        })

    except Exception as error:

        if conn:
            conn.rollback()

        print(
            "UPDATE PAYMENT ERROR:",
            repr(error),
        )

        return jsonify({
            "success": False,
            "error": (
                "Unable to update payment status. "
                "No database changes were saved."
            ),
        }), 500

    finally:

        if conn:
            conn.close()


# ============================================================
# RESEND APPROVAL EMAIL
# ============================================================

@admin_bp.route(
    "/resend-approval/<int:id>",
    methods=["POST"],
)
def resend_approval(id):

    if not admin_required():
        return unauthorized()

    conn = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        )

        booking = _get_booking(
            cursor,
            id,
        )

        if not booking:
            return jsonify({
                "success": False,
                "error": "Booking not found.",
            }), 404

        if booking["status"] != "confirmed":
            return jsonify({
                "success": False,
                "error": (
                    "Approval email can only be resent "
                    "for a confirmed booking."
                ),
            }), 400

        result = _send_approval_email(
            booking
        )

        if not result["success"]:
            return jsonify({
                "success": False,
                "error": (
                    "Booking is confirmed, but the email "
                    "could not be sent."
                ),
                "details": result["error"],
            }), 502

        return jsonify({
            "success": True,
            "message": "Approval email resent successfully.",
        })

    except Exception as error:

        print(
            "RESEND APPROVAL ERROR:",
            repr(error),
        )

        return jsonify({
            "success": False,
            "error": "Unable to resend approval email.",
        }), 500

    finally:

        if conn:
            conn.close()


# ============================================================
# RESEND REJECTION EMAIL
# ============================================================

@admin_bp.route(
    "/resend-rejection/<int:id>",
    methods=["POST"],
)
def resend_rejection(id):

    if not admin_required():
        return unauthorized()

    conn = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        )

        booking = _get_booking(
            cursor,
            id,
        )

        if not booking:
            return jsonify({
                "success": False,
                "error": "Booking not found.",
            }), 404

        if booking["status"] != "rejected":
            return jsonify({
                "success": False,
                "error": (
                    "Rejection email can only be resent "
                    "for a rejected booking."
                ),
            }), 400

        result = _send_rejection_email(
            booking
        )

        if not result["success"]:
            return jsonify({
                "success": False,
                "error": (
                    "Booking is rejected, but the email "
                    "could not be sent."
                ),
                "details": result["error"],
            }), 502

        return jsonify({
            "success": True,
            "message": "Rejection email resent successfully.",
        })

    except Exception as error:

        print(
            "RESEND REJECTION ERROR:",
            repr(error),
        )

        return jsonify({
            "success": False,
            "error": "Unable to resend rejection email.",
        }), 500

    finally:

        if conn:
            conn.close()


# ============================================================
# REJECT / CANCEL BOOKING
# ============================================================

@admin_bp.route(
    "/delete/<int:id>",
    methods=["DELETE"],
)
def delete_booking(id):

    if not admin_required():
        return unauthorized()

    conn = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        )

        booking = _get_booking(
            cursor,
            id,
        )

        if not booking:
            return jsonify({
                "success": False,
                "error": "Booking not found.",
            }), 404

        if booking["status"] == "rejected":
            return jsonify({
                "success": True,
                "message": "Booking is already rejected.",
            })

        cursor.execute(
            """
            UPDATE bookings
            SET status = 'rejected'
            WHERE id = %s
            RETURNING *
            """,
            (id,),
        )

        updated_booking = cursor.fetchone()

        conn.commit()

        email_result = _send_rejection_email(
            updated_booking
        )

        return jsonify({
            "success": True,
            "booking": dict(updated_booking),
            "email_sent": (
                email_result.get("success", False)
            ),
            "email_error": email_result.get("error"),
            "message": (
                "Booking rejected successfully."
            ),
        })

    except Exception as error:

        if conn:
            conn.rollback()

        print(
            "REJECT BOOKING ERROR:",
            repr(error),
        )

        return jsonify({
            "success": False,
            "error": (
                "Unable to reject the booking. "
                "No database changes were saved."
            ),
        }), 500

    finally:

        if conn:
            conn.close()