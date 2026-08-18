import os
import psycopg2
import psycopg2.extras


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

DATABASE_URL = os.getenv("DATABASE_URL")


def get_db_connection():
    """
    Create and return a PostgreSQL database connection.

    Render provides DATABASE_URL through the environment.
    """

    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not configured. "
            "Please add DATABASE_URL to your Render environment variables."
        )

    return psycopg2.connect(
        DATABASE_URL,
        sslmode="require"
    )


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():
    """
    Create the bookings table if it does not already exist.

    PostgreSQL is used for both local production-style testing
    and Render deployment.
    """

    conn = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor()

        # ----------------------------------------------------
        # BOOKINGS TABLE
        # ----------------------------------------------------

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (

                id SERIAL PRIMARY KEY,

                name TEXT NOT NULL,

                email TEXT NOT NULL,

                phone TEXT NOT NULL,

                lesson_type TEXT NOT NULL,

                package TEXT NOT NULL,

                price TEXT NOT NULL,

                lesson_date TEXT NOT NULL,

                lesson_time TEXT NOT NULL,

                payment_method TEXT
                    DEFAULT 'not_selected',

                payment_status TEXT
                    NOT NULL
                    DEFAULT 'pending',

                stripe_payment_id TEXT,

                status TEXT
                    NOT NULL
                    DEFAULT 'pending',

                reminder_sent BOOLEAN
                    NOT NULL
                    DEFAULT FALSE,

                approval_token TEXT,

                created_at TIMESTAMP
                    NOT NULL
                    DEFAULT NOW()
            );
            """
        )

        conn.commit()

        # ----------------------------------------------------
        # ADD MISSING COLUMNS
        # ----------------------------------------------------
        #
        # This is important for an existing Render database.
        #
        # CREATE TABLE IF NOT EXISTS does NOT add new columns
        # to a table that already exists.
        #
        # These ALTER TABLE statements safely add columns
        # introduced by newer versions of the application.
        # ----------------------------------------------------

        columns_to_add = [

            (
                "payment_method",
                """
                ALTER TABLE bookings
                ADD COLUMN payment_method TEXT
                DEFAULT 'not_selected'
                """
            ),

            (
                "payment_status",
                """
                ALTER TABLE bookings
                ADD COLUMN payment_status TEXT
                NOT NULL
                DEFAULT 'pending'
                """
            ),

            (
                "stripe_payment_id",
                """
                ALTER TABLE bookings
                ADD COLUMN stripe_payment_id TEXT
                """
            ),

            (
                "status",
                """
                ALTER TABLE bookings
                ADD COLUMN status TEXT
                NOT NULL
                DEFAULT 'pending'
                """
            ),

            (
                "reminder_sent",
                """
                ALTER TABLE bookings
                ADD COLUMN reminder_sent BOOLEAN
                NOT NULL
                DEFAULT FALSE
                """
            ),

            (
                "approval_token",
                """
                ALTER TABLE bookings
                ADD COLUMN approval_token TEXT
                """
            ),

            (
                "created_at",
                """
                ALTER TABLE bookings
                ADD COLUMN created_at TIMESTAMP
                NOT NULL
                DEFAULT NOW()
                """
            ),
        ]

        for column_name, sql in columns_to_add:

            try:

                cursor.execute(sql)

                conn.commit()

                print(
                    f"Database column added: {column_name}"
                )

            except psycopg2.errors.DuplicateColumn:

                conn.rollback()

            except Exception as error:

                conn.rollback()

                print(
                    f"Could not add column "
                    f"{column_name}: {error}"
                )


        # ----------------------------------------------------
        # INDEXES
        # ----------------------------------------------------

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_bookings_date_time
            ON bookings (lesson_date, lesson_time);
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_bookings_status
            ON bookings (status);
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_bookings_payment_status
            ON bookings (payment_status);
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_bookings_approval_token
            ON bookings (approval_token);
            """
        )

        conn.commit()

        print(
            "PostgreSQL database initialized successfully."
        )

    except Exception as error:

        if conn:
            conn.rollback()

        print(
            "DATABASE INITIALIZATION ERROR:",
            repr(error)
        )

        raise

    finally:

        if conn:

            conn.close()


# ============================================================
# BOOKING HELPERS
# ============================================================

def get_booking_by_id(booking_id):
    """
    Return one booking as a dictionary.
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
            """,
            (booking_id,)
        )

        return cursor.fetchone()

    finally:

        if conn:

            conn.close()


# ============================================================
# BOOKING AVAILABILITY
# ============================================================

def booking_slot_is_available(
    lesson_date,
    lesson_time
):
    """
    Check whether a lesson time is available.

    Pending and confirmed bookings block a time slot.
    Rejected bookings do not.
    """

    conn = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor()

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

        return cursor.fetchone() is None

    finally:

        if conn:

            conn.close()


# ============================================================
# EXPIRED PENDING BOOKINGS
# ============================================================

def remove_expired_pending_bookings(
    hold_minutes=30
):
    """
    Remove old pending bookings.

    This releases lesson times when a customer started a
    registration but never completed the process.

    Confirmed bookings are never removed here.
    """

    conn = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM bookings
            WHERE status = 'pending'
              AND created_at <
                  NOW() - (%s * INTERVAL '1 minute')
            """,
            (hold_minutes,)
        )

        deleted_count = cursor.rowcount

        conn.commit()

        print(
            f"Expired pending bookings removed: "
            f"{deleted_count}"
        )

        return deleted_count

    except Exception as error:

        if conn:

            conn.rollback()

        print(
            "ERROR REMOVING EXPIRED BOOKINGS:",
            repr(error)
        )

        return 0

    finally:

        if conn:

            conn.close()