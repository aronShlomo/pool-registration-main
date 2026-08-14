import psycopg2
import psycopg2.extras
import os
from datetime import datetime, timedelta

# ==========================
# DATABASE CONNECTION
# ==========================

def get_db_connection():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise Exception("DATABASE_URL is missing in environment variables.")
    conn = psycopg2.connect(url, sslmode="require")
    return conn


# ==========================
# REMOVE EXPIRED PENDING BOOKINGS
# ==========================

def remove_expired_pending_bookings():
    conn = get_db_connection()
    cursor = conn.cursor()

    expired_time = (
        datetime.now() - timedelta(minutes=30)
    )

    cursor.execute(
        """
        DELETE FROM bookings
        WHERE status = 'pending'
        AND payment_status = 'pending'
        AND created_at < %s
        """,
        (expired_time,)
    )

    conn.commit()
    conn.close()


# ==========================
# INITIALIZE DATABASE (POSTGRESQL)
# ==========================

def init_database():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL,
            phone VARCHAR(50),
            lesson_type VARCHAR(255) NOT NULL,
            package VARCHAR(255) NOT NULL,
            lesson_date VARCHAR(50) NOT NULL,
            lesson_time VARCHAR(50) NOT NULL,
            price VARCHAR(50),
            payment_method VARCHAR(50) DEFAULT 'none',
            payment_status VARCHAR(50) DEFAULT 'pending',
            stripe_payment_id VARCHAR(255),
            status VARCHAR(50) DEFAULT 'pending',
            reminder_sent BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    conn.close()


# ==========================
# COMPATIBILITY WRAPPER
# ==========================

def init_db():
    """Compatibility wrapper for older code."""
    init_database()
    print("PostgreSQL database initialized.")
