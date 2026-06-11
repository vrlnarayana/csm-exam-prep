# CSM Exam Prep App — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Streamlit + SQLite app that guides a single user through the 48-day Cisco 820-605 CSM exam study plan with daily study content, instant-feedback quizzes, streak tracking, and weak-spot detection.

**Architecture:** Modular multi-page Streamlit app. `db/` layer owns all SQLite interactions. `content/` layer owns study notes and questions. `pages/` owns UI only — no SQL or business logic in page files. `app.py` is the Today dashboard entry point.

**Tech Stack:** Python 3.7+, Streamlit 1.35+, SQLite3 (stdlib), python-docx 1.1+, pandas 2.0+, altair 5.0+, pytest

---

## File Map

| File | Responsibility |
|---|---|
| `app.py` | Today dashboard — streak, progress bar, daily checklist, weak-spot alert, quick stats |
| `pages/1_Study.py` | Study material reader — section navigator, exam tips, mark-as-read |
| `pages/2_Quiz.py` | Quiz engine — question display, instant feedback, session state, DB writes |
| `pages/3_Stats.py` | Performance dashboard — topic mastery bars, weekly chart, exam readiness |
| `pages/4_Settings.py` | Exam date, name, start date, reset progress |
| `db/schema.py` | `get_conn()`, `init_db()` — creates 5 tables if not exist |
| `db/queries.py` | All read/write functions — no SQL anywhere else |
| `content/days.py` | `DAYS` list — 48 day dicts with study notes, exam tips, key terms |
| `content/questions.py` | `QUESTIONS` list — 10 questions × days 2–48 |
| `content/loader.py` | `get_day_content(day)`, `get_day_questions(day)` — .docx override or built-in fallback |
| `tests/conftest.py` | Pytest fixture: temp SQLite DB, monkeypatches `DB_PATH` |
| `tests/test_db.py` | Tests for schema init and all query functions |
| `tests/test_content.py` | Tests for data shape, loader fallback, docx parsing |

---

## Task 1: Project Scaffold + DB Schema

**Files:**
- Create: `requirements.txt`
- Create: `db/__init__.py`
- Create: `db/schema.py`
- Create: `content/__init__.py`
- Create: `pages/.gitkeep`
- Create: `data/.gitkeep`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Create requirements.txt**

```
streamlit>=1.35
python-docx>=1.1
pandas>=2.0
altair>=5.0
pytest>=7.0
```

- [ ] **Step 2: Create db/__init__.py and content/__init__.py** (empty files)

```bash
touch /Users/vrln/csm_exam_prep/db/__init__.py
touch /Users/vrln/csm_exam_prep/content/__init__.py
touch /Users/vrln/csm_exam_prep/tests/__init__.py
mkdir -p /Users/vrln/csm_exam_prep/data
mkdir -p /Users/vrln/csm_exam_prep/pages
```

- [ ] **Step 3: Write the failing test**

Create `tests/conftest.py`:
```python
import pytest
import tempfile
import os
from pathlib import Path

@pytest.fixture(autouse=True)
def tmp_db(monkeypatch, tmp_path):
    """Redirect DB_PATH to a temp file for every test."""
    db_file = tmp_path / "test.db"
    monkeypatch.setattr("db.schema.DB_PATH", db_file)
    yield db_file
```

Create `tests/test_db.py`:
```python
import sqlite3
import pytest
from db.schema import init_db, get_conn, DB_PATH

def test_init_db_creates_all_tables():
    init_db()
    with get_conn() as conn:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
    assert tables == {"settings", "daily_progress", "quiz_attempts", "topic_mastery", "streak_log"}

def test_init_db_is_idempotent():
    init_db()
    init_db()  # should not raise
    with get_conn() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
    assert count == 5

def test_get_conn_creates_data_dir(tmp_path, monkeypatch):
    nested = tmp_path / "nested" / "dir" / "test.db"
    monkeypatch.setattr("db.schema.DB_PATH", nested)
    with get_conn() as conn:
        assert conn is not None
    assert nested.exists()
```

- [ ] **Step 4: Run tests to verify they fail**

```bash
cd /Users/vrln/csm_exam_prep && python3 -m pytest tests/test_db.py -v 2>&1 | head -20
```
Expected: `ModuleNotFoundError: No module named 'db'`

- [ ] **Step 5: Write db/schema.py**

```python
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
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd /Users/vrln/csm_exam_prep && python3 -m pytest tests/test_db.py -v
```
Expected: 3 passed

- [ ] **Step 7: Commit**

```bash
cd /Users/vrln/csm_exam_prep && git add requirements.txt db/ content/__init__.py tests/ data/.gitkeep pages/ && git commit -m "feat: scaffold project structure and DB schema"
```

---

## Task 2: DB Queries Layer

**Files:**
- Create: `db/queries.py`
- Modify: `tests/test_db.py` (add query tests)

- [ ] **Step 1: Add query tests to tests/test_db.py**

Append to existing `tests/test_db.py`:
```python
from db.queries import (
    get_setting, set_setting, get_day_progress, mark_study_done,
    mark_quiz_done, save_quiz_attempts, refresh_topic_mastery,
    get_topic_mastery, get_weak_spots, get_streak, get_all_progress,
    get_exam_readiness, reset_progress, get_current_day_number, log_streak_day
)
from datetime import date, timedelta

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
    assert p["study_done"] == 0 or p["study_done"] is False
    assert p["quiz_done"] == 0 or p["quiz_done"] is False
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
    # 12 days done, avg quiz score 0.75
    for i in range(1, 13):
        mark_study_done(i)
        mark_quiz_done(i, 0.75)
    r = get_exam_readiness()
    expected = (12 / 48 * 0.4) + (0.75 * 0.6)
    assert abs(r - expected) < 0.01

# ── reset ──────────────────────────────────────────────────────────────────────

def test_reset_progress_clears_all():
    init_db()
    mark_study_done(1)
    mark_quiz_done(1, 0.9)
    save_quiz_attempts(1, [{"question_id": "d1_q1", "topic": "T", "correct": True}])
    refresh_topic_mastery("T")
    log_streak_day(date.today().isoformat())
    reset_progress()
    assert get_day_progress(1)["study_done"] in (0, False)
    assert get_topic_mastery() == []
    assert get_streak() == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/vrln/csm_exam_prep && python3 -m pytest tests/test_db.py -v 2>&1 | tail -10
```
Expected: `ImportError: cannot import name 'get_setting' from 'db.queries'`

- [ ] **Step 3: Write db/queries.py**

```python
import sqlite3
from datetime import date, timedelta
from db.schema import get_conn, init_db

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
        total = conn.execute(
            "SELECT COUNT(*) as c FROM quiz_attempts WHERE topic = ?", (topic,)
        ).fetchone()["c"]
        correct = conn.execute(
            "SELECT COUNT(*) as c FROM quiz_attempts WHERE topic = ? AND correct = 1", (topic,)
        ).fetchone()["c"]
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
        total = conn.execute("SELECT COUNT(*) as c FROM streak_log").fetchone()["c"] + 1
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
        """, (today_str, total, streak))

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
            # Missed today, but yesterday is fine
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
    return (days_done / 48 * 0.4) + (avg_score * 0.6)

# ── settings helpers ───────────────────────────────────────────────────────────

def get_current_day_number() -> int:
    start = get_setting("start_date")
    if not start:
        return 1
    delta = (date.today() - date.fromisoformat(start)).days + 1
    return max(1, min(delta, 48))

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
        conn.executescript("""
            DELETE FROM daily_progress;
            DELETE FROM quiz_attempts;
            DELETE FROM topic_mastery;
            DELETE FROM streak_log;
        """)
```

- [ ] **Step 4: Run all tests**

```bash
cd /Users/vrln/csm_exam_prep && python3 -m pytest tests/test_db.py -v
```
Expected: all 20 tests pass

- [ ] **Step 5: Commit**

```bash
cd /Users/vrln/csm_exam_prep && git add db/queries.py tests/test_db.py && git commit -m "feat: DB queries layer with full test coverage"
```

---

## Task 3: Content — days.py (48-day study notes)

**Files:**
- Create: `content/days.py`
- Create: `tests/test_content.py`

- [ ] **Step 1: Write failing shape test**

Create `tests/test_content.py`:
```python
from content.days import DAYS

def test_days_has_48_entries():
    assert len(DAYS) == 48

def test_each_day_has_required_keys():
    required = {"day", "title", "week", "phase", "topic", "estimated_minutes", "sections", "key_terms"}
    for d in DAYS:
        missing = required - d.keys()
        assert not missing, f"Day {d.get('day')} missing: {missing}"

def test_day_numbers_are_sequential():
    numbers = [d["day"] for d in DAYS]
    assert numbers == list(range(1, 49))

def test_each_day_has_at_least_one_section():
    for d in DAYS:
        assert len(d["sections"]) >= 1, f"Day {d['day']} has no sections"

def test_each_section_has_required_keys():
    for d in DAYS:
        for s in d["sections"]:
            assert "heading" in s, f"Day {d['day']} section missing 'heading'"
            assert "body" in s, f"Day {d['day']} section missing 'body'"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/vrln/csm_exam_prep && python3 -m pytest tests/test_content.py::test_days_has_48_entries -v
```
Expected: `ModuleNotFoundError: No module named 'content.days'`

- [ ] **Step 3: Write content/days.py with all 48 days**

Each entry follows this exact structure:
```python
{
    "day": N,
    "title": "...",
    "week": 1-7,
    "phase": "Foundation|Core Concepts|Advanced Topics|Cisco Specializations|Integration & Practice|Final Preparation|Final Sprint",
    "topic": "...",          # must be consistent — same string used in questions.py and topic_mastery
    "estimated_minutes": 45,
    "sections": [
        {
            "heading": "...",
            "body": "...",   # 150–300 words of study content
            "exam_tip": "..." # optional — include when relevant
        }
    ],
    "key_terms": {"Term": "Definition"},
    "docx_override": None    # or "DayN/filename.docx" if file is present
}
```

Create `content/days.py` with the `DAYS` list. Full content for all 48 days is required — no placeholders. Use the study plan document (`CSM_820-605_Study_Plan.docx`) as the source of truth for each day's topic and activities. The topics in `DAYS` must match exactly the topics used in `content/questions.py` and stored in `topic_mastery`.

**Canonical topic strings** (use these exactly — shared with questions.py):
```python
TOPICS = {
    1:  "Subscription Model",
    2:  "Subscription Model",
    3:  "Customer Lifecycle",
    4:  "Customer Lifecycle",
    5:  "Adoption Fundamentals",
    6:  "Cisco Lifecycle Framework",
    7:  "Mixed Review",
    8:  "Cisco CX Cloud",
    9:  "Use Cases & Business Outcomes",
    10: "Success Planning",
    11: "Stakeholder Management",
    12: "Customer Health Scoring",
    13: "Expansion Strategies",
    14: "Mixed Review",
    15: "Risk Management",
    16: "Renewal Management",
    17: "QBR & Executive Engagement",
    18: "Change Management",
    19: "Advocacy & NPS",
    20: "CSM Metrics & KPIs",
    21: "Mixed Review",
    22: "Cisco CX Specialization",
    23: "Cisco Technology Portfolio",
    24: "DNA Center & Network Automation",
    25: "Collaboration & Webex",
    26: "Security & Zero Trust",
    27: "Customer Segmentation",
    28: "Mixed Review",
    # Days 29–48: scenario practice, reviews, mock exams
    29: "Adoption Fundamentals",
    30: "Customer Lifecycle",
    31: "Risk Management",
    32: "Expansion Strategies",
    33: "Mixed Review",
    34: "Mixed Review",
    35: "Mixed Review",
    36: "Subscription Model",
    37: "Cisco Lifecycle Framework",
    38: "Adoption Fundamentals",
    39: "Mixed Review",
    40: "CSM Metrics & KPIs",
    41: "Mixed Review",
    42: "Mixed Review",
    43: "Mixed Review",
    44: "Subscription Model",
    45: "Cisco CX Cloud",
    46: "Mixed Review",
    47: "Mixed Review",
    48: "Mixed Review",
}
```

**Day 1 example (full, including docx_override):**
```python
{
    "day": 1,
    "title": "Subscription Model Fundamentals",
    "week": 1,
    "phase": "Foundation",
    "topic": "Subscription Model",
    "estimated_minutes": 60,
    "sections": [
        {
            "heading": "Subscription vs. Perpetual Licensing",
            "body": (
                "A perpetual license is a one-time purchase giving the customer the right to use "
                "software indefinitely. The vendor recognises revenue immediately at point of sale. "
                "The customer owns that specific version forever but pays separately for updates and "
                "support (typically 15–22% of license cost annually).\n\n"
                "A subscription license grants access for a defined period in exchange for recurring "
                "payments. The customer never owns the software — access stops when payments stop. "
                "Most modern SaaS and cloud solutions use this model. Vendors manage infrastructure, "
                "security, and updates as part of the fee.\n\n"
                "Key difference for the exam: in perpetual models the CSM role barely exists because "
                "there is no recurring revenue at stake. In subscription models, the CSM is essential "
                "because renewal depends entirely on the customer realising value."
            ),
            "exam_tip": (
                "Watch for 'when is revenue recognised?' questions. Perpetual = at point of sale. "
                "Subscription = spread over the contract term (ARR/MRR). This distinction appears "
                "in ~3 questions on most practice exams."
            ),
        },
        {
            "heading": "ARR, MRR, and TCV",
            "body": (
                "Annual Recurring Revenue (ARR) = the annualised value of all active subscription "
                "contracts. Formula: ARR = MRR × 12. ARR is the primary health metric for "
                "subscription businesses.\n\n"
                "Monthly Recurring Revenue (MRR) = the normalised monthly value of active "
                "subscriptions. For annual contracts: MRR = contract value ÷ 12.\n\n"
                "Total Contract Value (TCV) = the total value of a contract including all recurring "
                "and one-time fees over the full contract term. TCV ≥ ARR because it may include "
                "professional services, onboarding fees, or multi-year totals.\n\n"
                "Example: A 3-year contract worth $360,000 total. TCV = $360,000. "
                "ARR = $120,000. MRR = $10,000."
            ),
            "exam_tip": (
                "Know the formulas cold: ARR = MRR × 12; MRR = annual contract ÷ 12; "
                "TCV = total contract including one-time fees. Calculation questions appear."
            ),
        },
        {
            "heading": "Churn Rate, NRR, and GRR",
            "body": (
                "Churn Rate = percentage of ARR lost in a period from cancellations and downgrades. "
                "Formula: Churn Rate = ARR lost ÷ ARR at start of period × 100.\n\n"
                "Gross Revenue Retention (GRR) = percentage of recurring revenue retained excluding "
                "expansions. GRR can never exceed 100%. Formula: GRR = (Starting ARR − Churn − "
                "Downgrades) ÷ Starting ARR × 100.\n\n"
                "Net Revenue Retention (NRR) = percentage of recurring revenue retained including "
                "expansions and upsells. NRR can exceed 100% (meaning customers are spending more). "
                "Formula: NRR = (Starting ARR − Churn − Downgrades + Expansions) ÷ Starting ARR × 100.\n\n"
                "Example: Start with $1M ARR. Lose $50K to churn. Expand $150K. "
                "GRR = 95%. NRR = 110%."
            ),
            "exam_tip": (
                "NRR > 100% is possible and desirable — it means expansion revenue exceeds churn. "
                "GRR can never exceed 100%. Know which excludes expansions (GRR) vs. includes them (NRR)."
            ),
        },
    ],
    "key_terms": {
        "ARR": "Annual Recurring Revenue — annualised value of all active subscriptions",
        "MRR": "Monthly Recurring Revenue — normalised monthly subscription value",
        "TCV": "Total Contract Value — full contract value including one-time fees",
        "Churn Rate": "Percentage of ARR lost in a period from cancellations/downgrades",
        "GRR": "Gross Revenue Retention — retention excluding expansions (max 100%)",
        "NRR": "Net Revenue Retention — retention including expansions (can exceed 100%)",
        "Perpetual License": "One-time purchase; vendor revenue recognised immediately at sale",
        "Subscription License": "Recurring payments; access stops when payments stop",
    },
    "docx_override": "Day1/CSM_Day1_Subscription_Model_Study.docx",
},
```

Write all 48 entries with equivalent depth. For review days (7, 14, 21, 28) and final sprint days (42, 47, 48), sections should summarise the week's topics and provide exam strategy tips. For mock exam days (33, 39, 43), sections explain exam simulation strategy.

- [ ] **Step 4: Run content tests**

```bash
cd /Users/vrln/csm_exam_prep && python3 -m pytest tests/test_content.py -v
```
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
cd /Users/vrln/csm_exam_prep && git add content/days.py tests/test_content.py && git commit -m "feat: 48-day study content in days.py"
```

---

## Task 4: Content — questions.py

**Files:**
- Create: `content/questions.py`
- Modify: `tests/test_content.py`

- [ ] **Step 1: Add question tests**

Append to `tests/test_content.py`:
```python
from content.questions import QUESTIONS

def test_questions_covers_days_2_to_48():
    days_covered = {q["day"] for q in QUESTIONS}
    # Days 2–48 must all be present (Day 1 comes from .docx)
    for d in range(2, 49):
        assert d in days_covered, f"Day {d} has no questions in questions.py"

def test_each_question_has_required_keys():
    required = {"id", "day", "topic", "difficulty", "question", "options", "answer", "explanation"}
    for q in QUESTIONS:
        missing = required - q.keys()
        assert not missing, f"Question {q.get('id')} missing: {missing}"

def test_each_question_has_four_options():
    for q in QUESTIONS:
        assert set(q["options"].keys()) == {"A", "B", "C", "D"}, f"{q['id']} bad options"

def test_answer_is_valid_option():
    for q in QUESTIONS:
        assert q["answer"] in {"A", "B", "C", "D"}, f"{q['id']} invalid answer: {q['answer']}"

def test_difficulty_values():
    valid = {"basic", "intermediate", "advanced"}
    for q in QUESTIONS:
        assert q["difficulty"] in valid, f"{q['id']} bad difficulty: {q['difficulty']}"

def test_topic_matches_days_topic():
    from content.days import DAYS
    day_topics = {d["day"]: d["topic"] for d in DAYS}
    for q in QUESTIONS:
        expected = day_topics.get(q["day"])
        assert q["topic"] == expected, (
            f"Question {q['id']} topic '{q['topic']}' != day {q['day']} topic '{expected}'"
        )
```

- [ ] **Step 2: Run to verify failure**

```bash
cd /Users/vrln/csm_exam_prep && python3 -m pytest tests/test_content.py::test_questions_covers_days_2_to_48 -v
```
Expected: `ModuleNotFoundError: No module named 'content.questions'`

- [ ] **Step 3: Write content/questions.py**

Structure each question exactly as:
```python
{
    "id": "d2_q1",
    "day": 2,
    "topic": "Subscription Model",   # must match days.py entry for day 2
    "difficulty": "intermediate",
    "question": "A SaaS company starts the quarter with $2M ARR, gains $300K in new subscriptions, loses $100K to churn, and $50K to downgrades. What is the NRR?",
    "options": {
        "A": "92.5%",
        "B": "95%",
        "C": "107.5%",
        "D": "115%",
    },
    "answer": "C",
    "explanation": (
        "NRR = (Starting ARR − Churn − Downgrades + Expansions) ÷ Starting ARR × 100. "
        "Here: ($2M − $100K − $50K + $300K) ÷ $2M × 100 = $2.15M ÷ $2M × 100 = 107.5%. "
        "NRR above 100% means expansion revenue more than offsets losses."
    ),
},
```

Write 10 questions per day for days 2–48 (470 questions total). Mix difficulty: ~3 basic, 5 intermediate, 2 advanced per day. Ensure questions directly test the content covered in that day's `days.py` entry. For review days, draw questions from all topics covered in that week.

**Day 2 sample set (write all 10):**
```python
# Day 2 — Subscription Model Deep Dive — 10 questions
{"id": "d2_q1", "day": 2, "topic": "Subscription Model", "difficulty": "basic",
 "question": "What does CLV (Customer Lifetime Value) measure?",
 "options": {
     "A": "The total revenue a customer generates in their first year",
     "B": "The total net profit a business expects from a customer over the entire relationship",
     "C": "The cost to acquire a new customer",
     "D": "The annual contract value of a subscription",
 },
 "answer": "B",
 "explanation": "CLV measures the total net profit expected from a customer over the entire relationship. It's used to justify CS investment — the higher the CLV, the more worth spending on retention and expansion."},

{"id": "d2_q2", "day": 2, "topic": "Subscription Model", "difficulty": "basic",
 "question": "Which strategy describes selling additional products to existing customers that complement their current purchase?",
 "options": {
     "A": "Upsell",
     "B": "Cross-sell",
     "C": "Land and expand",
     "D": "Churn prevention",
 },
 "answer": "B",
 "explanation": "Cross-sell is selling complementary products (e.g., adding Cisco Umbrella to a customer who has Webex). Upsell is upgrading to a higher tier of the same product. Both are expansion motions."},

{"id": "d2_q3", "day": 2, "topic": "Subscription Model", "difficulty": "intermediate",
 "question": "A customer's NRR is 115% and GRR is 88%. What does this tell you?",
 "options": {
     "A": "The company is losing customers but growing revenue through upsells",
     "B": "The company has no churn and strong expansion",
     "C": "GRR cannot be lower than NRR",
     "D": "The company's total revenue is declining",
 },
 "answer": "A",
 "explanation": "GRR of 88% means 12% of ARR was lost to churn/downgrades. NRR of 115% means expansion revenue more than offset those losses — net result is revenue growth. This is a healthy pattern: some churn, but strong expansion from remaining customers."},

{"id": "d2_q4", "day": 2, "topic": "Subscription Model", "difficulty": "intermediate",
 "question": "How is MRR calculated for a customer on an annual $120,000 contract?",
 "options": {
     "A": "$120,000",
     "B": "$12,000",
     "C": "$10,000",
     "D": "$1,000",
 },
 "answer": "C",
 "explanation": "MRR normalises annual contracts to monthly: $120,000 ÷ 12 = $10,000 MRR. This allows comparison across customers on different billing cycles."},

{"id": "d2_q5", "day": 2, "topic": "Subscription Model", "difficulty": "intermediate",
 "question": "In SaaS revenue recognition, when is subscription revenue typically recognised?",
 "options": {
     "A": "Entirely at contract signing",
     "B": "Entirely when cash is received",
     "C": "Ratably over the subscription period as the service is delivered",
     "D": "At the end of the fiscal year",
 },
 "answer": "C",
 "explanation": "Under ASC 606 / IFRS 15, subscription revenue is recognised ratably (evenly) over the service period as the performance obligation is satisfied — not at signing or cash receipt. This is why subscription revenue is 'deferred' on the balance sheet until earned."},

{"id": "d2_q6", "day": 2, "topic": "Subscription Model", "difficulty": "intermediate",
 "question": "Which metric BEST indicates whether a SaaS company can grow without acquiring new customers?",
 "options": {
     "A": "Churn rate",
     "B": "GRR",
     "C": "NRR",
     "D": "TCV",
 },
 "answer": "C",
 "explanation": "NRR above 100% means the company's existing customer base is growing — expansion revenue exceeds losses. A company with NRR > 100% can theoretically grow revenue even with zero new customers, purely through upsell and cross-sell."},

{"id": "d2_q7", "day": 2, "topic": "Subscription Model", "difficulty": "intermediate",
 "question": "A company starts Q1 with $5M ARR. They add $500K new ARR, lose $200K to churn, and $100K to downgrades. Calculate GRR.",
 "options": {
     "A": "94%",
     "B": "96%",
     "C": "104%",
     "D": "110%",
 },
 "answer": "A",
 "explanation": "GRR = (Starting ARR − Churn − Downgrades) ÷ Starting ARR = ($5M − $200K − $100K) ÷ $5M = $4.7M ÷ $5M = 94%. GRR excludes expansions — it only shows how well you retained existing revenue."},

{"id": "d2_q8", "day": 2, "topic": "Subscription Model", "difficulty": "advanced",
 "question": "A CSM's portfolio has 20 accounts with average ARR of $50,000. The company's CLV:CAC ratio target is 3:1 and CAC is $15,000 per customer. If average churn is 15% annually, what is the approximate CLV?",
 "options": {
     "A": "$25,000",
     "B": "$45,000",
     "C": "$50,000",
     "D": "$333,333",
 },
 "answer": "D",
 "explanation": "CLV = ARR ÷ Churn Rate = $50,000 ÷ 0.15 = $333,333. This represents the expected lifetime revenue from one customer assuming constant churn. The CLV:CAC ratio of $333K:$15K = 22:1, well above the 3:1 target — indicating very efficient acquisition."},

{"id": "d2_q9", "day": 2, "topic": "Subscription Model", "difficulty": "advanced",
 "question": "Which combination of metrics BEST indicates a healthy subscription business?",
 "options": {
     "A": "High churn rate, high NRR, low GRR",
     "B": "Low churn rate, NRR > 100%, GRR > 90%",
     "C": "NRR = 100%, GRR = 100%, zero expansion",
     "D": "High TCV, low MRR, high CAC",
 },
 "answer": "B",
 "explanation": "A healthy subscription business shows: low churn (retained base), GRR > 90% (strong retention excluding expansion), and NRR > 100% (expansion outpaces losses). Option A is contradictory — you can't have high churn and high NRR simultaneously without extreme expansion. Option C is neutral, not healthy growth."},

{"id": "d2_q10", "day": 2, "topic": "Subscription Model", "difficulty": "basic",
 "question": "What is the 'land and expand' strategy in subscription sales?",
 "options": {
     "A": "Acquiring new customers in new geographic markets",
     "B": "Starting with a small initial sale and growing the account over time through adoption-driven expansion",
     "C": "Offering deep discounts to win large initial contracts",
     "D": "Expanding the product line before selling to a customer",
 },
 "answer": "B",
 "explanation": "'Land and expand' means closing a smaller initial deal to get a customer started, then growing the account as they realise value and adopt more of the product. The CSM's role is central — adoption drives expansion. Cisco uses this heavily with Webex, SecureX, and DNA Center."},
```

Continue this pattern for days 3–48. Each set of 10 questions must:
- Cover the exact content in that day's `days.py` sections
- Mix difficulty: ~3 basic, 5 intermediate, 2 advanced
- Use scenario-style questions for intermediate/advanced (match real exam style)
- Have explanations that teach, not just confirm

- [ ] **Step 4: Run all content tests**

```bash
cd /Users/vrln/csm_exam_prep && python3 -m pytest tests/test_content.py -v
```
Expected: all 11 tests pass

- [ ] **Step 5: Commit**

```bash
cd /Users/vrln/csm_exam_prep && git add content/questions.py && git commit -m "feat: practice questions for all 48 days"
```

---

## Task 5: Content Loader (.docx parser + fallback)

**Files:**
- Create: `content/loader.py`
- Modify: `tests/test_content.py`

- [ ] **Step 1: Add loader tests**

Append to `tests/test_content.py`:
```python
from content.loader import get_day_content, get_day_questions
from content.days import DAYS

def test_get_day_content_returns_dict_for_all_days():
    for day_num in range(1, 49):
        content = get_day_content(day_num)
        assert isinstance(content, dict), f"Day {day_num} content not a dict"
        assert "sections" in content

def test_get_day_questions_returns_list_for_all_days():
    for day_num in range(1, 49):
        qs = get_day_questions(day_num)
        assert isinstance(qs, list), f"Day {day_num} questions not a list"
        assert len(qs) > 0, f"Day {day_num} has no questions"

def test_get_day_content_day1_uses_docx_when_present():
    content = get_day_content(1)
    # Day 1 has a .docx override — sections should be populated
    assert len(content["sections"]) > 0

def test_get_day_questions_day1_returns_questions():
    qs = get_day_questions(1)
    assert len(qs) >= 10
    for q in qs:
        assert "question" in q
        assert "answer" in q
        assert "options" in q
```

- [ ] **Step 2: Run to verify failure**

```bash
cd /Users/vrln/csm_exam_prep && python3 -m pytest tests/test_content.py::test_get_day_content_returns_dict_for_all_days -v
```
Expected: `ModuleNotFoundError: No module named 'content.loader'`

- [ ] **Step 3: Write content/loader.py**

```python
from pathlib import Path
import re

ROOT = Path(__file__).parent.parent

def get_day_content(day_number: int) -> dict:
    """Return study content for day_number. Uses .docx override if present, else built-in."""
    from content.days import DAYS
    day = next((d for d in DAYS if d["day"] == day_number), None)
    if day is None:
        return {"sections": [], "key_terms": {}, "title": f"Day {day_number}"}

    override_path = day.get("docx_override")
    if override_path:
        full_path = ROOT / override_path
        if full_path.exists():
            try:
                return _parse_study_docx(full_path, day)
            except Exception:
                pass  # fall through to built-in

    return day

def get_day_questions(day_number: int) -> list:
    """Return questions for day_number. Day 1 parsed from .docx; days 2-48 from questions.py."""
    if day_number == 1:
        docx_path = ROOT / "Day1" / "CSM_100_Practice_Questions-Day 1.docx"
        if docx_path.exists():
            try:
                return _parse_questions_docx(docx_path)
            except Exception:
                pass
        # Fall back to built-in Day 1 questions if docx parse fails
    return _get_builtin_questions(day_number)

def _get_builtin_questions(day_number: int) -> list:
    from content.questions import QUESTIONS
    return [q for q in QUESTIONS if q["day"] == day_number]

def _parse_study_docx(path: Path, day_meta: dict) -> dict:
    """Parse a study .docx into the same shape as a days.py entry."""
    from docx import Document
    doc = Document(str(path))
    sections = []
    current_section = None

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        style = para.style.name.lower()
        # Detect section headings by style or numbering pattern (e.g. "1.1 What is...")
        if "heading" in style or re.match(r"^\d+\.\d+\s", text) or re.match(r"^0[1-9]\s", text):
            if current_section and current_section["body"]:
                sections.append(current_section)
            current_section = {"heading": text, "body": "", "exam_tip": ""}
        elif current_section is not None:
            # Detect exam tip blocks
            if "EXAM TIP" in text.upper():
                continue  # skip the label line
            if current_section.get("_in_tip"):
                current_section["exam_tip"] += " " + text
            elif "exam tip" in text.lower() or text.upper().startswith("EXAM"):
                current_section["_in_tip"] = True
            else:
                current_section["body"] += (" " if current_section["body"] else "") + text

    if current_section and current_section["body"]:
        sections.append(current_section)

    # Clean up internal marker key
    for s in sections:
        s.pop("_in_tip", None)

    if not sections:
        # If parsing yielded nothing, fall back to built-in
        return day_meta

    result = dict(day_meta)
    result["sections"] = sections if sections else day_meta.get("sections", [])
    return result

def _parse_questions_docx(path: Path) -> list:
    """
    Parse the Day 1 questions .docx into a list of question dicts.

    The .docx contains table rows in this repeating pattern:
      Row 1 (merged cell): "Q1 | Category · Difficulty"
      Row 2: Q | question text with options A. B. C. D.
      Row 3: A | "Correct Answer: X\n\nexplanation text"
    """
    from docx import Document
    doc = Document(str(path))
    questions = []

    for table in doc.tables:
        rows = table.rows
        i = 0
        while i < len(rows):
            cells = [c.text.strip() for c in rows[i].cells]
            full_text = " ".join(cells)

            # Detect header row: starts with Q\d (like "Q1", "Q2")
            q_match = re.match(r"Q(\d+)", full_text)
            if q_match and i + 2 < len(rows):
                q_num = int(q_match.group(1))

                # Extract difficulty from header row
                difficulty = "basic"
                if "Intermediate" in full_text:
                    difficulty = "intermediate"
                elif "Advanced" in full_text:
                    difficulty = "advanced"

                # Row i+1 is the question row
                q_row_text = " ".join(c.text.strip() for c in rows[i + 1].cells)
                # Remove leading "Q " prefix
                q_row_text = re.sub(r"^Q\s+", "", q_row_text).strip()

                # Extract options A-D from question text
                options = {}
                q_text = q_row_text
                for letter in ["A", "B", "C", "D"]:
                    pattern = rf"{letter}\.\s+(.*?)(?=(?:[A-D]\.|$))"
                    m = re.search(pattern, q_row_text, re.DOTALL)
                    if m:
                        options[letter] = m.group(1).strip()

                # Clean question text (remove options)
                q_clean = re.split(r"\s+A\.", q_text)[0].strip()

                # Row i+2 is the answer row
                a_row_text = " ".join(c.text.strip() for c in rows[i + 2].cells)
                a_row_text = re.sub(r"^A\s+", "", a_row_text).strip()

                answer_match = re.search(r"Correct Answer:\s*([A-D])", a_row_text)
                answer = answer_match.group(1) if answer_match else "A"
                explanation = re.sub(r"Correct Answer:\s*[A-D]\s*", "", a_row_text).strip()

                if q_clean and len(options) == 4:
                    questions.append({
                        "id": f"d1_q{q_num}",
                        "day": 1,
                        "topic": "Subscription Model",
                        "difficulty": difficulty,
                        "question": q_clean,
                        "options": options,
                        "answer": answer,
                        "explanation": explanation,
                    })
                i += 3
            else:
                i += 1

    return questions
```

- [ ] **Step 4: Run all content tests**

```bash
cd /Users/vrln/csm_exam_prep && python3 -m pytest tests/test_content.py -v
```
Expected: all 15 tests pass

- [ ] **Step 5: Commit**

```bash
cd /Users/vrln/csm_exam_prep && git add content/loader.py && git commit -m "feat: content loader with .docx parser and built-in fallback"
```

---

## Task 6: app.py — Today Dashboard

**Files:**
- Create: `app.py`

- [ ] **Step 1: Write app.py**

```python
import streamlit as st
from datetime import date
from db.schema import init_db
from db.queries import (
    get_setting, set_setting, get_current_day_number, get_days_left,
    get_streak, get_day_progress, get_weak_spots, get_all_progress,
    get_exam_readiness, get_topic_mastery,
)
from content.days import DAYS

st.set_page_config(
    page_title="CSM Exam Prep",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

# ── First-run: collect exam date ───────────────────────────────────────────────
if not get_setting("exam_date"):
    st.title("📘 CSM Exam Prep — Setup")
    st.markdown("**Welcome!** Let's get you set up before your first study session.")
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Your name (optional)", placeholder="e.g. Alex")
    with col2:
        exam_dt = st.date_input(
            "Your exam date",
            value=date(2026, 7, 29),
            min_value=date.today(),
        )
    if st.button("Start Studying →", type="primary"):
        set_setting("exam_date", exam_dt.isoformat())
        set_setting("start_date", date.today().isoformat())
        if name:
            set_setting("user_name", name)
        st.rerun()
    st.stop()

# ── Load state ─────────────────────────────────────────────────────────────────
day_num   = get_current_day_number()
days_left = get_days_left()
streak    = get_streak()
progress  = get_day_progress(day_num)
weak      = get_weak_spots(threshold=70.0)
readiness = get_exam_readiness()
all_prog  = get_all_progress()
name      = get_setting("user_name") or ""
day_meta  = next((d for d in DAYS if d["day"] == day_num), DAYS[0])

days_done = sum(1 for p in all_prog if p["study_done"] or p["quiz_done"])
scores    = [p["quiz_score"] for p in all_prog if p["quiz_score"] is not None]
avg_score = (sum(scores) / len(scores) * 100) if scores else 0.0
best_topics = sorted(get_topic_mastery(), key=lambda x: x["mastery_pct"], reverse=True)
best_pct  = best_topics[0]["mastery_pct"] if best_topics else 0.0

# ── Header ─────────────────────────────────────────────────────────────────────
col_title, col_streak = st.columns([3, 1])
with col_title:
    greeting = f"Good to see you, {name}! " if name else ""
    st.title(f"📘 {greeting}CSM Exam Prep")
    st.caption("Cisco 820-605 · Customer Success Manager")
with col_streak:
    if streak > 0:
        st.metric("🔥 Streak", f"{streak} days", help="Consecutive days with study or quiz activity")
    else:
        st.metric("🔥 Streak", "Start today!", help="Complete study or quiz to start your streak")

# ── Progress bar ───────────────────────────────────────────────────────────────
st.markdown("---")
pct = int(days_done / 48 * 100)
st.markdown(f"**Day {day_num} of 48 · Week {day_meta['week']}: {day_meta['phase']}**")
st.progress(pct / 100)
st.caption(f"{pct}% complete · {days_left} days until exam · {day_meta['title']}")

# ── Today's checklist ──────────────────────────────────────────────────────────
st.markdown("---")
st.subheader(f"📋 Today — {day_meta['title']}")

c1, c2 = st.columns(2)
with c1:
    study_icon = "✅" if progress["study_done"] else "📖"
    study_label = "Study complete" if progress["study_done"] else "Read today's material"
    st.markdown(
        f"{'<div style=\"background:#064e3b;padding:12px;border-radius:8px;\">' if progress['study_done'] else '<div style=\"background:#1e3a5f;padding:12px;border-radius:8px;\">'}"
        f"<strong>{study_icon} {study_label}</strong>"
        f"</div>",
        unsafe_allow_html=True,
    )
    if not progress["study_done"]:
        st.page_link("pages/1_Study.py", label="Open Study →", icon="📖")

with c2:
    quiz_icon = "✅" if progress["quiz_done"] else "✏️"
    quiz_score_str = f" · {progress['quiz_score']*100:.0f}%" if progress.get("quiz_score") else ""
    quiz_label = f"Quiz complete{quiz_score_str}" if progress["quiz_done"] else "Take today's quiz"
    st.markdown(
        f"{'<div style=\"background:#064e3b;padding:12px;border-radius:8px;\">' if progress['quiz_done'] else '<div style=\"background:#1e293b;padding:12px;border-radius:8px;\">'}"
        f"<strong>{quiz_icon} {quiz_label}</strong>"
        f"</div>",
        unsafe_allow_html=True,
    )
    if not progress["quiz_done"]:
        st.page_link("pages/2_Quiz.py", label="Start Quiz →", icon="✏️")

# ── Weak-spot alert ─────────────────────────────────────────────────────────────
if weak:
    st.markdown("---")
    st.warning("⚠️ **Weak Spots — review recommended before your exam**")
    for w in weak:
        day_for_topic = next(
            (d["day"] for d in DAYS if d["topic"] == w["topic"]), None
        )
        st.markdown(
            f"**{w['topic']}** — {w['mastery_pct']:.0f}% mastery "
            f"({w['correct_count']}/{w['total_attempts']} correct)"
            + (f" · [Revisit Day {day_for_topic}](pages/1_Study.py)" if day_for_topic else "")
        )

# ── Quick stats ─────────────────────────────────────────────────────────────────
st.markdown("---")
s1, s2, s3, s4 = st.columns(4)
s1.metric("Quiz avg", f"{avg_score:.0f}%", help="Average quiz score across all completed days")
s2.metric("Days done", f"{days_done}", help="Days with at least one activity completed")
s3.metric("Best topic", f"{best_pct:.0f}%" if best_topics else "–", help="Your highest-mastery topic")
s4.metric("Days left", f"{days_left}", help="Calendar days until your exam")

# ── Exam readiness ──────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("🎯 Exam Readiness")
st.progress(min(readiness, 1.0))
pct_r = readiness * 100
colour = "green" if pct_r >= 75 else "orange" if pct_r >= 50 else "red"
st.markdown(
    f"<span style='color:{colour};font-size:1.2rem;font-weight:bold;'>{pct_r:.0f}% ready</span>"
    " · Target: 75%+ before exam day",
    unsafe_allow_html=True,
)
st.caption("Formula: (days done × 40%) + (avg quiz score × 60%)")
```

- [ ] **Step 2: Manual test — launch the app**

```bash
cd /Users/vrln/csm_exam_prep && streamlit run app.py
```

Verify:
- First-run setup screen shows with name + date picker
- After setup, Today dashboard loads
- Progress bar shows Day 1 of 48
- Study and Quiz cards visible
- No errors in terminal

- [ ] **Step 3: Commit**

```bash
cd /Users/vrln/csm_exam_prep && git add app.py && git commit -m "feat: Today dashboard with first-run setup, checklist, weak-spot alert"
```

---

## Task 7: Study Page

**Files:**
- Create: `pages/1_Study.py`

- [ ] **Step 1: Write pages/1_Study.py**

```python
import streamlit as st
from db.schema import init_db
from db.queries import get_current_day_number, get_day_progress, mark_study_done, log_streak_day
from content.loader import get_day_content
from content.days import DAYS
from datetime import date

st.set_page_config(page_title="Study · CSM Prep", page_icon="📖", layout="wide")
init_db()

# ── Day selector ───────────────────────────────────────────────────────────────
current = get_current_day_number()
day_options = {f"Day {d['day']}: {d['title']}": d["day"] for d in DAYS}
default_key = f"Day {current}: {next(d['title'] for d in DAYS if d['day'] == current)}"

selected_label = st.sidebar.selectbox(
    "Select day",
    options=list(day_options.keys()),
    index=list(day_options.keys()).index(default_key),
)
day_num = day_options[selected_label]

# ── Load content ───────────────────────────────────────────────────────────────
content = get_day_content(day_num)
progress = get_day_progress(day_num)
sections = content.get("sections", [])
key_terms = content.get("key_terms", {})
is_docx = bool(content.get("docx_override")) and not content.get("sections") == content.get("sections")
source_label = "📄 From your .docx file" if content.get("docx_override") else "📦 Built-in content"

# ── Header ─────────────────────────────────────────────────────────────────────
st.title(f"📖 Day {day_num} — {content['title']}")
col_meta, col_src = st.columns([3, 1])
with col_meta:
    meta = next((d for d in DAYS if d["day"] == day_num), {})
    st.caption(
        f"Week {meta.get('week', '?')} · {meta.get('phase', '')} · "
        f"~{meta.get('estimated_minutes', 45)} min · Topic: {meta.get('topic', '')}"
    )
with col_src:
    st.caption(source_label)

if progress["study_done"]:
    st.success("✅ You have marked this day as studied.")

st.markdown("---")

# ── Section navigator via session state ────────────────────────────────────────
state_key = f"study_section_{day_num}"
if state_key not in st.session_state:
    st.session_state[state_key] = 0

idx = st.session_state[state_key]
idx = max(0, min(idx, len(sections) - 1))

if not sections:
    st.info("No study content available for this day yet.")
else:
    section = sections[idx]
    st.markdown(f"### {section['heading']}")
    st.markdown(section["body"])

    if section.get("exam_tip"):
        st.info(f"💡 **Exam Tip:** {section['exam_tip']}")

    st.markdown("---")
    nav_left, nav_mid, nav_right = st.columns([1, 2, 1])
    with nav_left:
        if st.button("← Previous", disabled=(idx == 0)):
            st.session_state[state_key] = idx - 1
            st.rerun()
    with nav_mid:
        st.caption(f"Section {idx + 1} of {len(sections)}")
    with nav_right:
        if idx < len(sections) - 1:
            if st.button("Next →"):
                st.session_state[state_key] = idx + 1
                st.rerun()
        else:
            if not progress["study_done"]:
                if st.button("✅ Mark as Read", type="primary"):
                    mark_study_done(day_num)
                    log_streak_day(date.today().isoformat())
                    st.success("Day marked as studied!")
                    st.rerun()
            else:
                st.success("All sections read ✓")

# ── Key terms ──────────────────────────────────────────────────────────────────
if key_terms:
    st.markdown("---")
    with st.expander("📚 Key Terms Glossary"):
        for term, defn in key_terms.items():
            st.markdown(f"**{term}** — {defn}")
```

- [ ] **Step 2: Manual test**

```bash
cd /Users/vrln/csm_exam_prep && streamlit run app.py
```
Navigate to Study in sidebar. Verify:
- Day 1 loads sections from the .docx file (source badge says "From your .docx file")
- Section prev/next buttons work
- Exam tip callouts appear
- "Mark as Read" button sets study_done and shows success message
- Switching days in sidebar changes content

- [ ] **Step 3: Commit**

```bash
cd /Users/vrln/csm_exam_prep && git add pages/1_Study.py && git commit -m "feat: Study page with section navigator, exam tips, mark-as-read"
```

---

## Task 8: Quiz Page

**Files:**
- Create: `pages/2_Quiz.py`

- [ ] **Step 1: Write pages/2_Quiz.py**

```python
import streamlit as st
from datetime import date
from db.schema import init_db
from db.queries import (
    get_current_day_number, mark_quiz_done, save_quiz_attempts,
    refresh_topic_mastery, log_streak_day,
)
from content.loader import get_day_questions
from content.days import DAYS

st.set_page_config(page_title="Quiz · CSM Prep", page_icon="✏️", layout="wide")
init_db()

# ── Day selector ───────────────────────────────────────────────────────────────
current = get_current_day_number()
day_labels = [f"Day {d['day']}: {d['title']}" for d in DAYS]
day_nums   = [d["day"] for d in DAYS]
default_idx = current - 1

sel_idx = st.sidebar.selectbox(
    "Quiz for day",
    options=range(len(day_labels)),
    format_func=lambda i: day_labels[i],
    index=default_idx,
)
day_num   = day_nums[sel_idx]
day_title = DAYS[day_nums.index(day_num)]["title"]

# Reset quiz state when day changes
if st.session_state.get("quiz_day") != day_num:
    for key in ["quiz_questions", "quiz_idx", "quiz_answers", "quiz_submitted", "quiz_complete"]:
        st.session_state.pop(key, None)
    st.session_state["quiz_day"] = day_num

# ── Load questions ─────────────────────────────────────────────────────────────
if "quiz_questions" not in st.session_state:
    all_qs = get_day_questions(day_num)
    # Cap at 10 for days with >10 questions (Day 1 has 100)
    st.session_state["quiz_questions"] = all_qs[:10]
    st.session_state["quiz_idx"]       = 0
    st.session_state["quiz_answers"]   = {}
    st.session_state["quiz_submitted"] = {}
    st.session_state["quiz_complete"]  = False

questions  = st.session_state["quiz_questions"]
idx        = st.session_state["quiz_idx"]
answers    = st.session_state["quiz_answers"]
submitted  = st.session_state["quiz_submitted"]
complete   = st.session_state["quiz_complete"]

st.title(f"✏️ Day {day_num} Quiz — {day_title}")

# ── Progress dots ──────────────────────────────────────────────────────────────
if questions:
    dot_html = ""
    for i, q in enumerate(questions):
        if i in submitted:
            colour = "#22c55e" if answers.get(i) == q["answer"] else "#ef4444"
        elif i == idx:
            colour = "#3b82f6"
        else:
            colour = "#334155"
        dot_html += f"<span style='display:inline-block;width:18px;height:8px;border-radius:4px;background:{colour};margin:2px;'></span>"
    st.markdown(dot_html, unsafe_allow_html=True)
    st.caption(f"Question {idx + 1} of {len(questions)}")

st.markdown("---")

# ── Complete state ─────────────────────────────────────────────────────────────
if complete:
    correct_count = sum(1 for i, q in enumerate(questions) if answers.get(i) == q["answer"])
    score = correct_count / len(questions)
    st.balloons()
    st.success(f"## Quiz Complete! You scored {correct_count}/{len(questions)} ({score*100:.0f}%)")

    # Save to DB
    attempts = [
        {"question_id": q["id"], "topic": q["topic"], "correct": answers.get(i) == q["answer"]}
        for i, q in enumerate(questions)
    ]
    save_quiz_attempts(day_num, attempts)
    topics = {q["topic"] for q in questions}
    for topic in topics:
        refresh_topic_mastery(topic)
    mark_quiz_done(day_num, score)
    log_streak_day(date.today().isoformat())

    # Topic breakdown
    topic_results: dict = {}
    for i, q in enumerate(questions):
        t = q["topic"]
        topic_results.setdefault(t, {"correct": 0, "total": 0})
        topic_results[t]["total"] += 1
        if answers.get(i) == q["answer"]:
            topic_results[t]["correct"] += 1

    st.markdown("### Topic Breakdown")
    for topic, res in topic_results.items():
        pct = res["correct"] / res["total"] * 100
        st.markdown(f"**{topic}**: {res['correct']}/{res['total']} ({pct:.0f}%)")

    if st.button("🔄 Retry This Quiz"):
        for key in ["quiz_questions", "quiz_idx", "quiz_answers", "quiz_submitted", "quiz_complete"]:
            st.session_state.pop(key, None)
        st.rerun()
    st.stop()

# ── Active quiz ────────────────────────────────────────────────────────────────
if not questions:
    st.info("No questions available for this day yet.")
    st.stop()

q = questions[idx]
diff_colour = {"basic": "🟢", "intermediate": "🟡", "advanced": "🔴"}.get(q["difficulty"], "⚪")
st.markdown(f"**{diff_colour} {q['difficulty'].capitalize()}** · {q['topic']}")
st.markdown(f"### {q['question']}")

option_labels = [f"{k}. {v}" for k, v in sorted(q["options"].items())]
option_keys   = sorted(q["options"].keys())

already_submitted = idx in submitted

if already_submitted:
    user_answer = answers.get(idx)
    correct     = q["answer"]
    for label, key in zip(option_labels, option_keys):
        if key == correct:
            st.success(f"✅ {label}")
        elif key == user_answer and user_answer != correct:
            st.error(f"❌ {label} ← your answer")
        else:
            st.markdown(f"&nbsp;&nbsp;&nbsp;{label}")
    st.info(f"📖 **Explanation:** {q['explanation']}")

    st.markdown("---")
    if idx < len(questions) - 1:
        if st.button("Next Question →", type="primary"):
            st.session_state["quiz_idx"] = idx + 1
            st.rerun()
    else:
        if st.button("See Results →", type="primary"):
            st.session_state["quiz_complete"] = True
            st.rerun()
else:
    choice = st.radio(
        "Select your answer:",
        options=option_labels,
        index=None,
        key=f"choice_{day_num}_{idx}",
    )
    if st.button("Submit Answer", type="primary", disabled=(choice is None)):
        chosen_key = option_keys[option_labels.index(choice)] if choice else None
        st.session_state["quiz_answers"][idx]   = chosen_key
        st.session_state["quiz_submitted"][idx] = True
        st.rerun()
```

- [ ] **Step 2: Manual test**

```bash
cd /Users/vrln/csm_exam_prep && streamlit run app.py
```
Navigate to Quiz. Verify:
- Day 1 loads 10 questions (capped from 100)
- Progress dots update colour after answering
- Wrong answer shows red, correct shows green, explanation appears
- Next button advances questions
- After Q10, "See Results" appears
- Score is displayed with balloons
- DB is updated (go back to Today dashboard — quiz_done shows ✅)

- [ ] **Step 3: Commit**

```bash
cd /Users/vrln/csm_exam_prep && git add pages/2_Quiz.py && git commit -m "feat: Quiz page with instant feedback, session state, DB writes"
```

---

## Task 9: Stats Page

**Files:**
- Create: `pages/3_Stats.py`

- [ ] **Step 1: Write pages/3_Stats.py**

```python
import streamlit as st
import pandas as pd
from db.schema import init_db
from db.queries import (
    get_topic_mastery, get_weak_spots, get_all_progress,
    get_exam_readiness, get_streak,
)
from content.days import DAYS

st.set_page_config(page_title="Stats · CSM Prep", page_icon="📊", layout="wide")
init_db()

st.title("📊 Performance Dashboard")

# ── Load data ──────────────────────────────────────────────────────────────────
mastery   = get_topic_mastery()
all_prog  = get_all_progress()
readiness = get_exam_readiness()
streak    = get_streak()
weak      = get_weak_spots(70.0)

scores    = [p["quiz_score"] for p in all_prog if p["quiz_score"] is not None]
avg_score = (sum(scores) / len(scores) * 100) if scores else 0.0
days_done = sum(1 for p in all_prog if p["study_done"] or p["quiz_done"])

# ── Summary metrics ────────────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
m1.metric("🔥 Streak", f"{streak} days")
m2.metric("📅 Days done", f"{days_done}/48")
m3.metric("📈 Avg quiz score", f"{avg_score:.0f}%")
m4.metric("🎯 Exam readiness", f"{readiness*100:.0f}%")

st.markdown("---")

# ── Topic mastery ──────────────────────────────────────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("🏆 Topic Mastery")
    if mastery:
        df_m = pd.DataFrame(mastery)[["topic", "mastery_pct", "total_attempts", "correct_count"]]
        df_m.columns = ["Topic", "Mastery %", "Attempts", "Correct"]
        df_m["Mastery %"] = df_m["Mastery %"].round(1)

        def colour_mastery(val):
            if val >= 70:
                return "color: #22c55e"
            elif val >= 50:
                return "color: #f59e0b"
            return "color: #ef4444"

        st.dataframe(
            df_m.style.applymap(colour_mastery, subset=["Mastery %"]),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Complete a quiz to see topic mastery data.")

with col_r:
    st.subheader("📅 Weekly Score Trend")
    # Compute weekly averages
    week_scores: dict = {}
    for p in all_prog:
        if p["quiz_score"] is None:
            continue
        day_meta = next((d for d in DAYS if d["day"] == p["day_number"]), None)
        if day_meta:
            w = day_meta["week"]
            week_scores.setdefault(w, []).append(p["quiz_score"] * 100)

    if week_scores:
        df_w = pd.DataFrame([
            {"Week": f"W{w}", "Avg Score %": sum(s)/len(s)}
            for w, s in sorted(week_scores.items())
        ])
        st.bar_chart(df_w.set_index("Week"), y="Avg Score %", color="#3b82f6")
    else:
        st.info("Complete quizzes to see your weekly score trend.")

# ── Exam readiness ─────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("🎯 Exam Readiness")
st.progress(min(readiness, 1.0))
pct_r = readiness * 100
colour = "green" if pct_r >= 75 else "orange" if pct_r >= 50 else "red"
st.markdown(
    f"<span style='color:{colour};font-size:1.3rem;font-weight:bold;'>{pct_r:.0f}% ready</span>"
    " &nbsp;·&nbsp; Target: 75%+ before exam day",
    unsafe_allow_html=True,
)
if weak:
    st.markdown("**Weakest topics to focus on:**")
    for w in weak:
        st.markdown(f"- ⚠️ **{w['topic']}** — {w['mastery_pct']:.0f}% mastery")

# ── Quiz history ───────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📋 Quiz History")
if all_prog:
    history = []
    for p in all_prog:
        if p["quiz_done"]:
            day_meta = next((d for d in DAYS if d["day"] == p["day_number"]), {})
            history.append({
                "Day": p["day_number"],
                "Title": day_meta.get("title", ""),
                "Last Score": f"{p['quiz_score']*100:.0f}%" if p["quiz_score"] else "–",
                "Best Score": f"{p['best_score']*100:.0f}%" if p["best_score"] else "–",
                "Completed": "✅" if p["completed_at"] else "–",
            })
    if history:
        st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)
    else:
        st.info("No quizzes completed yet.")
else:
    st.info("No activity yet. Start studying to see your history here.")
```

- [ ] **Step 2: Manual test**

```bash
cd /Users/vrln/csm_exam_prep && streamlit run app.py
```
Navigate to Stats. Verify:
- Summary metrics show correct values
- After completing Day 1 quiz, topic mastery table shows Subscription Model entry
- Exam readiness bar matches formula
- Quiz history table shows completed days

- [ ] **Step 3: Commit**

```bash
cd /Users/vrln/csm_exam_prep && git add pages/3_Stats.py && git commit -m "feat: Stats page with topic mastery, weekly trend, exam readiness"
```

---

## Task 10: Settings Page

**Files:**
- Create: `pages/4_Settings.py`

- [ ] **Step 1: Write pages/4_Settings.py**

```python
import streamlit as st
from datetime import date
from db.schema import init_db
from db.queries import get_setting, set_setting, reset_progress

st.set_page_config(page_title="Settings · CSM Prep", page_icon="⚙️", layout="wide")
init_db()

st.title("⚙️ Settings")

# ── Exam date ──────────────────────────────────────────────────────────────────
st.subheader("📅 Exam Date")
current_exam = get_setting("exam_date")
current_dt   = date.fromisoformat(current_exam) if current_exam else date(2026, 7, 29)
new_exam = st.date_input("Your exam date", value=current_dt, min_value=date.today())
if st.button("Save Exam Date"):
    set_setting("exam_date", new_exam.isoformat())
    st.success(f"Exam date saved: {new_exam.strftime('%B %d, %Y')}")

# ── Name ───────────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("👤 Your Name")
current_name = get_setting("user_name") or ""
new_name = st.text_input("Display name (shown on dashboard)", value=current_name)
if st.button("Save Name"):
    set_setting("user_name", new_name)
    st.success("Name saved!")

# ── Start date ─────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📆 Study Start Date")
st.caption(
    "This controls which day number you're on. "
    "Change it if you want to re-align the schedule."
)
current_start = get_setting("start_date")
current_start_dt = date.fromisoformat(current_start) if current_start else date.today()
new_start = st.date_input("Study start date", value=current_start_dt)
if st.button("Save Start Date"):
    set_setting("start_date", new_start.isoformat())
    st.success(f"Start date saved: {new_start.strftime('%B %d, %Y')}")

# ── Reset ──────────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("🗑️ Reset Progress")
st.warning(
    "This will permanently delete all quiz results, study progress, topic mastery, "
    "and streak data. Your exam date and name will be kept."
)
confirm = st.checkbox("I understand this cannot be undone")
if st.button("Reset All Progress", type="primary", disabled=not confirm):
    reset_progress()
    st.success("Progress reset. Start fresh from Day 1!")

# ── App info ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("ℹ️ App Info")
st.markdown("""
| | |
|---|---|
| **App** | CSM Exam Prep |
| **Exam** | Cisco 820-605 Customer Success Manager |
| **Study plan** | 48-day plan · 7 phases |
| **Questions** | ~580 practice questions |
| **Version** | 1.0.0 |
""")
```

- [ ] **Step 2: Manual test**

```bash
cd /Users/vrln/csm_exam_prep && streamlit run app.py
```
Navigate to Settings. Verify:
- Changing exam date updates "days left" on Today dashboard
- Name change reflects in dashboard greeting
- Reset with unchecked confirm box is disabled
- Reset with confirm checked clears all progress (check Today dashboard)

- [ ] **Step 3: Final full test suite**

```bash
cd /Users/vrln/csm_exam_prep && python3 -m pytest tests/ -v --tb=short
```
Expected: all tests pass

- [ ] **Step 4: Final commit**

```bash
cd /Users/vrln/csm_exam_prep && git add pages/4_Settings.py && git commit -m "feat: Settings page — exam date, name, start date, reset progress"
```

---

## Self-Review Checklist

| Spec requirement | Task |
|---|---|
| Today dashboard — streak, progress, checklist, weak-spot | Task 6 |
| Study page — sections, exam tips, mark-as-read | Task 7 |
| Quiz — instant feedback, explanation | Task 8 |
| Stats — topic mastery, weekly trend, exam readiness | Task 9 |
| Settings — exam date, name, start date, reset | Task 10 |
| 5-table SQLite schema | Task 1 |
| All DB queries through queries.py | Task 2 |
| 48-day study notes | Task 3 |
| 10 questions × days 2–48 | Task 4 |
| .docx override parser, fallback | Task 5 |
| First-run exam date setup | Task 6 |
| Day number = calendar-based (start_date) | Task 2 (get_current_day_number) |
| Weak-spot threshold = 70%, max 3 shown | Task 2 (get_weak_spots) |
| Exam readiness = (days/48 × 0.4) + (avg_score × 0.6) | Task 2 (get_exam_readiness) |
| Streak resets if yesterday missed | Task 2 (get_streak) |
| Day 1 questions from .docx (100 Qs, capped to 10 in quiz) | Task 5 + Task 8 |
| best_score only updates if improved | Task 2 (mark_quiz_done) |
| Reset keeps exam_date and user_name | Task 10 |
