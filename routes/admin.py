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
    Check whether the administrator is logged in.
    """

    return session.get(
        "admin_logged_in",
        False
    )


# ============================================================
# LOGIN
# ============================================================

@admin_bp.route(
    "/login",
    methods=["GET", "POST"]
)
def admin_login():

    # --------------------------------------------------------
    # ALREADY LOGGED IN
    # --------------------------------------------------------

    if session.get("admin_logged_in"):

        return redirect(
            url_for(
                "admin.admin_dashboard"
            )
        )


    # --------------------------------------------------------
    # LOGIN FORM
    # --------------------------------------------------------

    if request.method == "POST":

        username = (
            request.form
            .get("username", "")
            .strip()
        )

        password = (
            request.form
            .get("password", "")
        )


        # ----------------------------------------------------
        # CHECK CREDENTIALS
        # ----------------------------------------------------

        if (
            username == Config.ADMIN_USERNAME
            and password == Config.ADMIN_PASSWORD
        ):

            session.clear()

            session["admin_logged_in"] = True

            return redirect(
                url_for(
                    "admin.admin_dashboard"
                )
            )


        return render_template(
            "login.html",
            error="Invalid username or password."
        )


    return render_template(
        "login.html"
    )


# ============================================================
# LOGOUT
# ============================================================

@admin_bp.route(
    "/logout"
)
def admin_logout():

    session.clear()

    return redirect(
        url_for(
            "admin.admin_login"
        )
    )


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


    data = request.get_json(
        silent=True
    ) or {}


    status = (
        data.get("status", "")
        .strip()
        .lower()
    )


    # ========================================================
    # ALLOWED STATUS VALUES
    # ========================================================

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
        # PREVENT INVALID CHANGES
        # ----------------------------------------------------

        if (
            old_status == "rejected"
            and status == "confirmed"
        ):

            return jsonify({
                "success": False,
                "error": (
                    "A rejected booking cannot be "
                    "approved from the dashboard."
                )
            }), 400


        # ----------------------------------------------------
        # APPROVE
        # ----------------------------------------------------

        if status == "confirmed":

            cursor.execute(
                """
                UPDATE bookings
                SET
                    status = 'confirmed',
                    payment_status = 'pending'
                WHERE id = %s
                RETURNING *
                """,
                (id,)
            )

        # ----------------------------------------------------
        # REJECT
        # ----------------------------------------------------

        elif status == "rejected":

            cursor.execute(
                """
                UPDATE bookings
                SET
                    status = 'rejected'
                WHERE id = %s
                RETURNING *
                """,
                (id,)
            )

        # ----------------------------------------------------
        # PENDING
        # ----------------------------------------------------

        else:

            cursor.execute(
                """
                UPDATE bookings
                SET
                    status = 'pending'
                WHERE id = %s
                RETURNING *
                """,
                (id,)
            )


        booking = cursor.fetchone()

        conn.commit()


        # ====================================================
        # SEND APPROPRIATE EMAIL
        # ====================================================

        if status == "confirmed":

            try:

                from email_service import (
                    send_user_approved_email
                )

                send_user_approved_email(
                    booking
                )

            except Exception as email_error:

                print(
                    "APPROVAL EMAIL ERROR:",
                    repr(email_error)
                )


        elif status == "rejected":

            try:

                from email_service import (
                    send_user_rejected_email
                )

                send_user_rejected_email(
                    booking
                )

            except Exception as email_error:

                print(
                    "REJECTION EMAIL ERROR:",
                    repr(email_error)
                )


        return jsonify({

            "success": True,

            "booking": dict(booking),

            "message": (
                "Booking updated successfully."
            )
        })


    except Exception as error:

        if conn:

            conn.rollback()


        print(
            "UPDATE BOOKING STATUS ERROR:",
            repr(error)
        )


        return jsonify({
            "success": False,
            "error": (
                "Unable to update the booking."
            )
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


        # ----------------------------------------------------
        # CUSTOMER NOTIFICATION
        # ----------------------------------------------------

        try:

            from email_service import (
                send_user_rejected_email
            )

            send_user_rejected_email(
                booking
            )

        except Exception as email_error:

            print(
                "REJECTION EMAIL ERROR:",
                repr(email_error)
            )


        return jsonify({

            "success": True,

            "message": (
                "Booking rejected successfully."
            )
        })


    except Exception as error:

        if conn:

            conn.rollback()


        print(
            "REJECT BOOKING ERROR:",
            repr(error)
        )


        return jsonify({
            "success": False,
            "error": (
                "Unable to reject booking."
            )
        }), 500


    finally:

        if conn:

            conn.close()