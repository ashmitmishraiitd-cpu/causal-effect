import json
import sqlite3
import time
import os
import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "causal_effect.db")
SESSION_TTL_SECONDS = 3600


def _get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            filepath TEXT NOT NULL,
            created_at REAL NOT NULL,
            config TEXT,
            columns TEXT
        )
    """)
    conn.commit()
    conn.close()
    logger.info(f"SQLite session store initialized at {DB_PATH}")


def save_session(session_id: str, filepath: str, columns: list[str]):
    conn = _get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO sessions (session_id, filepath, created_at, columns) VALUES (?, ?, ?, ?)",
        (session_id, filepath, time.time(), json.dumps(columns)),
    )
    conn.commit()
    conn.close()


def get_session(session_id: str) -> Optional[dict]:
    conn = _get_connection()
    row = conn.execute(
        "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    elapsed = time.time() - row["created_at"]
    if elapsed > SESSION_TTL_SECONDS:
        delete_session(session_id)
        return None
    return {
        "session_id": row["session_id"],
        "filepath": row["filepath"],
        "config": json.loads(row["config"]) if row["config"] else None,
        "columns": json.loads(row["columns"]) if row["columns"] else [],
    }


def update_config(session_id: str, config: dict):
    conn = _get_connection()
    conn.execute(
        "UPDATE sessions SET config = ? WHERE session_id = ?",
        (json.dumps(config), session_id),
    )
    conn.commit()
    conn.close()


def delete_session(session_id: str):
    conn = _get_connection()
    conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()
    logger.info(f"Deleted expired session {session_id}")


def cleanup_expired():
    conn = _get_connection()
    cutoff = time.time() - SESSION_TTL_SECONDS
    deleted = conn.execute("DELETE FROM sessions WHERE created_at < ?", (cutoff,)).rowcount
    conn.commit()
    conn.close()
    if deleted:
        logger.info(f"Cleaned up {deleted} expired sessions")
    return deleted


def session_count() -> int:
    conn = _get_connection()
    count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    conn.close()
    return count


def get_all_sessions() -> list[dict]:
    conn = _get_connection()
    rows = conn.execute("SELECT session_id, created_at, config FROM sessions").fetchall()
    conn.close()
    return [dict(r) for r in rows]
