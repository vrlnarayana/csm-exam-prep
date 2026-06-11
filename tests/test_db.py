import sqlite3
import pytest
from db.schema import init_db, get_conn
from db.queries import (
    get_setting, set_setting, get_day_progress, mark_study_done,
    mark_quiz_done, save_quiz_attempts, refresh_topic_mastery,
    get_topic_mastery, get_weak_spots, get_streak, get_all_progress,
    get_exam_readiness, reset_progress, get_current_day_number, log_streak_day,
    get_days_left
)
from datetime import date, timedelta

def test_init_db_creates_all_tables():
    init_db()
    with get_conn() as conn:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()}
    assert tables == {"settings", "daily_progress", "quiz_attempts", "topic_mastery", "streak_log"}

def test_init_db_is_idempotent():
    init_db()
    init_db()  # should not raise
    with get_conn() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchone()[0]
    assert count == 5

def test_get_conn_creates_data_dir(tmp_path, monkeypatch):
    nested = tmp_path / "nested" / "dir" / "test.db"
    monkeypatch.setattr("db.schema.DB_PATH", nested)
    with get_conn() as conn:
        assert conn is not None
    assert nested.exists()

# ── settings ──────────────────────────────────────────────────────────────────

def test_set_and_get_setting():
    init_db()
    set_setting("exam_date", "2026-07-29")
    assert get_setting("exam_date") == "2026-07-29"

def test_get_setting_missing_returns_none():
    init_db()
    assert get_setting("nonexistent") is None

def test_set_setting_upserts():
    init_db()
    set_setting("exam_date", "2026-07-01")
    set_setting("exam_date", "2026-07-29")
    assert get_setting("exam_date") == "2026-07-29"

# ── daily_progress ─────────────────────────────────────────────────────────────

def test_get_day_progress_default():
    init_db()
    p = get_day_progress(1)
    assert p["day_number"] == 1
    assert not p["study_done"]
    assert not p["quiz_done"]
    assert p["quiz_score"] is None

def test_mark_study_done():
    init_db()
    mark_study_done(1)
    p = get_day_progress(1)
    assert p["study_done"]

def test_mark_quiz_done_updates_score():
    init_db()
    mark_quiz_done(1, 0.8)
    p = get_day_progress(1)
    assert p["quiz_done"]
    assert abs(p["quiz_score"] - 0.8) < 0.001
    assert abs(p["best_score"] - 0.8) < 0.001

def test_mark_quiz_done_keeps_best_score():
    init_db()
    mark_quiz_done(1, 0.8)
    mark_quiz_done(1, 0.6)
    p = get_day_progress(1)
    assert abs(p["best_score"] - 0.8) < 0.001
    assert abs(p["quiz_score"] - 0.6) < 0.001

# ── quiz_attempts & topic_mastery ─────────────────────────────────────────────

def test_save_quiz_attempts_and_refresh_mastery():
    init_db()
    attempts = [
        {"question_id": "d1_q1", "topic": "Subscription Model", "correct": True},
        {"question_id": "d1_q2", "topic": "Subscription Model", "correct": False},
        {"question_id": "d1_q3", "topic": "Subscription Model", "correct": True},
    ]
    save_quiz_attempts(1, attempts)
    refresh_topic_mastery("Subscription Model")
    mastery = get_topic_mastery()
    assert len(mastery) == 1
    assert mastery[0]["topic"] == "Subscription Model"
    assert mastery[0]["total_attempts"] == 3
    assert mastery[0]["correct_count"] == 2
    assert abs(mastery[0]["mastery_pct"] - 66.67) < 0.1

def test_get_weak_spots_below_threshold():
    init_db()
    save_quiz_attempts(1, [{"question_id": "d1_q1", "topic": "Weak Topic", "correct": False}])
    refresh_topic_mastery("Weak Topic")
    save_quiz_attempts(2, [{"question_id": "d2_q1", "topic": "Strong Topic", "correct": True}])
    refresh_topic_mastery("Strong Topic")
    weak = get_weak_spots(threshold=70.0)
    assert any(w["topic"] == "Weak Topic" for w in weak)
    assert not any(w["topic"] == "Strong Topic" for w in weak)

# ── streak ─────────────────────────────────────────────────────────────────────

def test_streak_zero_with_no_log():
    init_db()
    assert get_streak() == 0

def test_streak_counts_today():
    init_db()
    today = date.today().isoformat()
    log_streak_day(today)
    assert get_streak() == 1

def test_streak_counts_consecutive():
    init_db()
    today = date.today()
    for i in range(3):
        log_streak_day((today - timedelta(days=i)).isoformat())
    assert get_streak() == 3

def test_streak_resets_on_gap():
    init_db()
    today = date.today()
    log_streak_day(today.isoformat())
    log_streak_day((today - timedelta(days=2)).isoformat())  # gap on day -1
    assert get_streak() == 1

# ── exam readiness ─────────────────────────────────────────────────────────────

def test_exam_readiness_zero_with_no_data():
    init_db()
    assert get_exam_readiness() == 0.0

def test_exam_readiness_formula():
    init_db()
    for i in range(1, 13):
        mark_study_done(i)
        mark_quiz_done(i, 0.75)
    r = get_exam_readiness()
    expected = (12 / 48 * 0.4) + (0.75 * 0.6)
    assert abs(r - expected) < 0.01

# ── get_all_progress ──────────────────────────────────────────────────────────

def test_get_all_progress_returns_ordered_list():
    init_db()
    mark_study_done(3)
    mark_study_done(1)
    mark_study_done(2)
    rows = get_all_progress()
    assert len(rows) == 3
    assert [r["day_number"] for r in rows] == [1, 2, 3]

def test_get_all_progress_empty_when_no_data():
    init_db()
    assert get_all_progress() == []

# ── get_current_day_number ────────────────────────────────────────────────────

def test_get_current_day_number_defaults_to_1_when_no_start():
    init_db()
    assert get_current_day_number() == 1

def test_get_current_day_number_uses_start_date():
    init_db()
    start = (date.today() - timedelta(days=4)).isoformat()
    set_setting("start_date", start)
    # day 1 is start, so 4 days later is day 5
    assert get_current_day_number() == 5

# ── reset ──────────────────────────────────────────────────────────────────────

def test_reset_progress_clears_all():
    init_db()
    mark_study_done(1)
    mark_quiz_done(1, 0.9)
    save_quiz_attempts(1, [{"question_id": "d1_q1", "topic": "T", "correct": True}])
    refresh_topic_mastery("T")
    log_streak_day(date.today().isoformat())
    reset_progress()
    assert not get_day_progress(1)["study_done"]
    assert get_topic_mastery() == []
    assert get_streak() == 0

# ── get_days_left ─────────────────────────────────────────────────────────────

def test_get_days_left_defaults_to_48():
    init_db()
    assert get_days_left() == 48

def test_get_days_left_uses_exam_date():
    init_db()
    exam = (date.today() + timedelta(days=10)).isoformat()
    set_setting("exam_date", exam)
    assert get_days_left() == 10
