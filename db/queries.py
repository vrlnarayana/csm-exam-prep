import sqlite3
from datetime import date, timedelta
from db.schema import get_conn, init_db

# ── constants ─────────────────────────────────────────────────────────────────

PLAN_DAYS = 48

# ── settings ──────────────────────────────────────────────────────────────────

def get_setting(key: str):
    init_db()
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

def set_setting(key: str, value: str):
    init_db()
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value)
        )

# ── daily_progress ─────────────────────────────────────────────────────────────

def get_day_progress(day_number: int) -> dict:
    init_db()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM daily_progress WHERE day_number = ?", (day_number,)
        ).fetchone()
    if row:
        return dict(row)
    return {
        "day_number": day_number, "study_done": False, "quiz_done": False,
        "completed_at": None, "quiz_score": None, "best_score": None,
    }

def mark_study_done(day_number: int):
    init_db()
    today = date.today().isoformat()
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO daily_progress (day_number, study_done, quiz_done)
            VALUES (?, 1, 0)
            ON CONFLICT(day_number) DO UPDATE SET study_done = 1
        """, (day_number,))
        row = conn.execute(
            "SELECT quiz_done FROM daily_progress WHERE day_number = ?", (day_number,)
        ).fetchone()
        if row and row["quiz_done"]:
            conn.execute(
                "UPDATE daily_progress SET completed_at = ? WHERE day_number = ?",
                (today, day_number)
            )
    log_streak_day(today)

def mark_quiz_done(day_number: int, score: float):
    init_db()
    today = date.today().isoformat()
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT best_score FROM daily_progress WHERE day_number = ?", (day_number,)
        ).fetchone()
        prev_best = (existing["best_score"] or 0.0) if existing else 0.0
        new_best = max(prev_best, score)
        conn.execute("""
            INSERT INTO daily_progress (day_number, study_done, quiz_done, quiz_score, best_score)
            VALUES (?, 0, 1, ?, ?)
            ON CONFLICT(day_number) DO UPDATE SET
                quiz_done  = 1,
                quiz_score = excluded.quiz_score,
                best_score = excluded.best_score
        """, (day_number, score, new_best))
        row = conn.execute(
            "SELECT study_done FROM daily_progress WHERE day_number = ?", (day_number,)
        ).fetchone()
        if row and row["study_done"]:
            conn.execute(
                "UPDATE daily_progress SET completed_at = ? WHERE day_number = ?",
                (today, day_number)
            )
    log_streak_day(today)

def get_all_progress() -> list:
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM daily_progress ORDER BY day_number"
        ).fetchall()
    return [dict(r) for r in rows]

# ── quiz_attempts ──────────────────────────────────────────────────────────────

def save_quiz_attempts(day_number: int, attempts: list):
    """attempts: list of {question_id, topic, correct}"""
    init_db()
    with get_conn() as conn:
        conn.executemany("""
            INSERT INTO quiz_attempts (day_number, question_id, topic, correct)
            VALUES (?, ?, ?, ?)
        """, [(day_number, a["question_id"], a["topic"], a["correct"]) for a in attempts])

# ── topic_mastery ──────────────────────────────────────────────────────────────

def refresh_topic_mastery(topic: str):
    init_db()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as total, SUM(correct) as correct FROM quiz_attempts WHERE topic = ?",
            (topic,)
        ).fetchone()
        total = row["total"]
        correct = row["correct"] or 0
        mastery = (correct / total * 100) if total > 0 else 0.0
        conn.execute("""
            INSERT INTO topic_mastery (topic, total_attempts, correct_count, mastery_pct, last_attempted)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(topic) DO UPDATE SET
                total_attempts = excluded.total_attempts,
                correct_count  = excluded.correct_count,
                mastery_pct    = excluded.mastery_pct,
                last_attempted = excluded.last_attempted
        """, (topic, total, correct, mastery, date.today().isoformat()))

def get_topic_mastery() -> list:
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM topic_mastery ORDER BY mastery_pct ASC"
        ).fetchall()
    return [dict(r) for r in rows]

def get_weak_spots(threshold: float = 70.0) -> list:
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM topic_mastery WHERE mastery_pct < ? ORDER BY mastery_pct ASC LIMIT 3",
            (threshold,)
        ).fetchall()
    return [dict(r) for r in rows]

# ── streak ─────────────────────────────────────────────────────────────────────

def log_streak_day(today_str: str):
    init_db()
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT study_date FROM streak_log WHERE study_date = ?", (today_str,)
        ).fetchone()
        if existing:
            return  # already logged today
        # Compute streak length ending today
        rows = conn.execute(
            "SELECT study_date FROM streak_log ORDER BY study_date DESC"
        ).fetchall()
        streak = 1
        prev = date.fromisoformat(today_str) - timedelta(days=1)
        for row in rows:
            d = date.fromisoformat(row["study_date"])
            if d == prev:
                streak += 1
                prev = d - timedelta(days=1)
            else:
                break
        conn.execute("""
            INSERT OR IGNORE INTO streak_log (study_date, days_studied, streak_at_date)
            VALUES (?, ?, ?)
        """, (today_str, 0, streak))

def get_streak() -> int:
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT study_date FROM streak_log ORDER BY study_date DESC"
        ).fetchall()
    if not rows:
        return 0
    today = date.today()
    expected = today
    streak = 0
    for row in rows:
        d = date.fromisoformat(row["study_date"])
        if d == expected:
            streak += 1
            expected = d - timedelta(days=1)
        elif streak == 0 and d == today - timedelta(days=1):
            # Missed today but yesterday is fine — still an active streak
            streak += 1
            expected = d - timedelta(days=1)
        else:
            break
    return streak

# ── exam readiness ─────────────────────────────────────────────────────────────

def get_exam_readiness() -> float:
    init_db()
    with get_conn() as conn:
        days_done = conn.execute(
            "SELECT COUNT(*) as c FROM daily_progress WHERE study_done = 1 OR quiz_done = 1"
        ).fetchone()["c"]
        avg_row = conn.execute(
            "SELECT AVG(quiz_score) as a FROM daily_progress WHERE quiz_score IS NOT NULL"
        ).fetchone()
        avg_score = avg_row["a"] if avg_row["a"] is not None else 0.0
    return (days_done / PLAN_DAYS * 0.4) + (avg_score * 0.6)

# ── settings helpers ───────────────────────────────────────────────────────────

def get_current_day_number() -> int:
    start = get_setting("start_date")
    if not start:
        return 1
    delta = (date.today() - date.fromisoformat(start)).days + 1
    return max(1, min(delta, PLAN_DAYS))

def get_days_left() -> int:
    exam = get_setting("exam_date")
    if not exam:
        return 48
    delta = (date.fromisoformat(exam) - date.today()).days
    return max(0, delta)

# ── reset ──────────────────────────────────────────────────────────────────────

def reset_progress():
    init_db()
    with get_conn() as conn:
        conn.execute("DELETE FROM daily_progress")
        conn.execute("DELETE FROM quiz_attempts")
        conn.execute("DELETE FROM topic_mastery")
        conn.execute("DELETE FROM streak_log")
