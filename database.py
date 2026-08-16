import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL is missing!")
else:
    print("DATABASE_URL loaded successfully")


def get_db_connection():
    """
    Returns a PostgreSQL connection using psycopg2.
    """
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    return conn


def init_db():
    """
    Creates the bookings table if it does not exist.
    This runs automatically on startup.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

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
            payment_method TEXT DEFAULT 'cash_or_zelle',
            payment_status TEXT DEFAULT 'pending',
            stripe_payment_id TEXT,
            status TEXT DEFAULT 'pending',
            reminder_sent BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """
    )

    conn.commit()
    conn.close()
    print("PostgreSQL bookings table ready.")
