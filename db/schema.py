import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "csm_prep.db"

def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
            CREATE TABLE IF NOT EXISTS daily_progress (
                day_number   INTEGER PRIMARY KEY,
                study_done   BOOLEAN DEFAULT 0,
                quiz_done    BOOLEAN DEFAULT 0,
                completed_at DATE,
                quiz_score   REAL,
                best_score   REAL
            );
            CREATE TABLE IF NOT EXISTS quiz_attempts (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                day_number   INTEGER NOT NULL,
                question_id  TEXT NOT NULL,
                topic        TEXT NOT NULL,
                correct      BOOLEAN NOT NULL,
                attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS topic_mastery (
                topic          TEXT PRIMARY KEY,
                total_attempts INTEGER DEFAULT 0,
                correct_count  INTEGER DEFAULT 0,
                mastery_pct    REAL DEFAULT 0.0,
                last_attempted DATE
            );
            CREATE TABLE IF NOT EXISTS streak_log (
                study_date     DATE PRIMARY KEY,
                days_studied   INTEGER,
                streak_at_date INTEGER
            );
        """)
