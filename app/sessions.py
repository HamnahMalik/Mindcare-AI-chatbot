import sqlite3
import json
from datetime import datetime
from pathlib import Path


DB_PATH = Path("/app/data/mindcare.db")


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    return conn


def init_db():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            user_id TEXT NOT NULL,
            session_type TEXT NOT NULL,
            session_data TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (user_id, session_type)
        )
    """)

    conn.commit()
    conn.close()


def save_session(user_id, session_type, session_data):
    conn = get_connection()

    conn.execute("""
        INSERT INTO sessions (
            user_id,
            session_type,
            session_data,
            updated_at
        )
        VALUES (?, ?, ?, ?)

        ON CONFLICT(user_id, session_type)
        DO UPDATE SET
            session_data = excluded.session_data,
            updated_at = excluded.updated_at
    """, (
        str(user_id),
        session_type,
        json.dumps(session_data),
        datetime.utcnow().isoformat()
    ))

    conn.commit()
    conn.close()


def get_session(user_id, session_type):
    conn = get_connection()

    row = conn.execute("""
        SELECT session_data
        FROM sessions
        WHERE user_id = ?
        AND session_type = ?
    """, (
        str(user_id),
        session_type
    )).fetchone()

    conn.close()

    if row is None:
        return None

    return json.loads(row["session_data"])


def delete_session(user_id, session_type):
    conn = get_connection()

    conn.execute("""
        DELETE FROM sessions
        WHERE user_id = ?
        AND session_type = ?
    """, (
        str(user_id),
        session_type
    ))

    conn.commit()
    conn.close()


def session_exists(user_id, session_type):
    return get_session(user_id, session_type) is not None
