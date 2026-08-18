from datetime import datetime, timedelta

from database import get_db_connection
from email_service import send_lesson_reminder


# ============================================================
# SEND LESSON REMINDERS
# ============================================================

def send_lesson_reminders():
    """
    Send reminder emails for confirmed lessons scheduled
    for tomorrow.

    Rules:
        - Booking must be confirmed.
        - Reminder must not have already been sent.
        - Rejected/pending bookings are ignored.
        - Paid or Pay Later bookings can receive reminders.
    """

    conn = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor()

        # ====================================================
        # TOMORROW'S DATE
        # ====================================================

        tomorrow = (
            datetime.now() +
            timedelta(days=1)
        ).strftime("%Y-%m-%d")


        # ====================================================
        # FIND LESSONS NEEDING REMINDERS
        # ====================================================

        cursor.execute(
            """
            SELECT *
            FROM bookings
            WHERE lesson_date = %s
              AND status = 'confirmed'
              AND reminder_sent = FALSE
            ORDER BY lesson_time
            """,
            (tomorrow,)
        )

        bookings = cursor.fetchall()


        print(
            f"REMINDER JOB: "
            f"{len(bookings)} lesson(s) found "
            f"for {tomorrow}."
        )


        # ====================================================
        # CONVERT COLUMN NAMES
        # ====================================================

        column_names = [
            description[0]
            for description in cursor.description
        ]


        # ====================================================
        # SEND REMINDERS
        # ====================================================

        for booking in bookings:

            booking_dict = dict(
                zip(
                    column_names,
                    booking
                )
            )

            booking_id = booking_dict.get(
                "id",
                "unknown"
            )


            try:

                # =================================================
                # GET BOOKING INFORMATION
                # =================================================

                customer_email = (
                    booking_dict.get("email")
                    or ""
                )

                student_name = (
                    booking_dict.get("name")
                    or booking_dict.get("student_name")
                    or "Customer"
                )

                lesson_date = (
                    booking_dict.get("lesson_date")
                    or ""
                )

                lesson_time = (
                    booking_dict.get("lesson_time")
                    or ""
                )

                lesson_type = (
                    booking_dict.get("lesson_type")
                    or ""
                )

                package = (
                    booking_dict.get("package")
                    or ""
                )


                # =================================================
                # VALIDATE EMAIL
                # =================================================

                if not customer_email:

                    print(
                        f"REMINDER SKIPPED: "
                        f"Booking #{booking_id} has no email address."
                    )

                    continue


                # =================================================
                # SEND REMINDER
                # =================================================

                send_lesson_reminder(
                    recipient=customer_email,
                    student_name=student_name,
                    lesson_date=lesson_date,
                    lesson_time=lesson_time,
                    lesson_type=lesson_type,
                    package=package
                )


                # =================================================
                # MARK REMINDER AS SENT
                # =================================================

                cursor.execute(
                    """
                    UPDATE bookings
                    SET reminder_sent = TRUE
                    WHERE id = %s
                    """,
                    (booking_id,)
                )


                conn.commit()


                print(
                    f"REMINDER SENT: "
                    f"Booking #{booking_id} "
                    f"-> {customer_email}"
                )


            except Exception as reminder_error:

                conn.rollback()

                print(
                    f"REMINDER ERROR "
                    f"FOR BOOKING #{booking_id}: "
                    f"{repr(reminder_error)}"
                )


    except Exception as error:

        if conn:
            conn.rollback()


        print(
            "REMINDER JOB ERROR:",
            repr(error)
        )


    finally:

        if conn:
            conn.close()