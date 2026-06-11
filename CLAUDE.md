# CLAUDE.md — CSM Exam Prep

## What This Is

A local Streamlit + SQLite app for studying the **Cisco 820-605 Customer Success Manager** certification exam. Single-user, offline, no authentication. Users work through a 48-day study plan with built-in notes, practice quizzes, streak tracking, and weak-spot detection.

## Repo

`https://github.com/vrlnarayana/csm-exam-prep`

## Tech Stack

| Layer | Tech |
|-------|------|
| UI | Streamlit 1.35+ (multi-page) |
| Database | SQLite via stdlib `sqlite3` |
| Content parsing | python-docx 1.1+ |
| Data tables/charts | pandas 3.x, Streamlit built-in charts |
| Tests | pytest 7+ |
| Python | 3.11+ |

## File Map

| File | Responsibility |
|------|----------------|
| `app.py` | Entry point — Today dashboard, first-run setup |
| `pages/1_Study.py` | Section navigator, exam tips, mark-as-read |
| `pages/2_Quiz.py` | Quiz engine — 10 questions, instant feedback, DB writes |
| `pages/3_Stats.py` | Topic mastery, weekly trend, exam readiness |
| `pages/4_Settings.py` | Exam date, name, start date, reset progress |
| `db/schema.py` | `get_conn()`, `init_db()` — 5-table SQLite schema |
| `db/queries.py` | All read/write functions — no SQL anywhere else |
| `content/days.py` | `DAYS` list — 48 day dicts with study notes |
| `content/questions.py` | `QUESTIONS` list — 10 questions × days 2–48 |
| `content/loader.py` | `get_day_content()`, `get_day_questions()` — .docx override or built-in fallback |
| `tests/conftest.py` | `tmp_db` fixture — redirects `DB_PATH` per test |
| `tests/test_db.py` | 25 tests for schema + all query functions |
| `tests/test_content.py` | 15 tests for data shape, loader, .docx parsing |

## Database Schema

5 tables in `data/csm_prep.db`:

```
settings          — key/value store (exam_date, start_date, user_name)
daily_progress    — one row per day (study_done, quiz_done, quiz_score, best_score)
quiz_attempts     — one row per question answered (day, question_id, topic, correct)
topic_mastery     — auto-computed after each quiz (mastery_pct = correct/total × 100)
streak_log        — one row per calendar day studied
```

The `.db` file is checked into the repo so Streamlit Cloud has data on first deploy.

## Key Business Logic

**Day number:** `(today - start_date).days + 1`, clamped 1–48. Set when user clicks "Start Studying" on first run.

**Exam readiness:** `(days_done/48 × 0.4) + (avg_quiz_score × 0.6)`. Target 75%+.

**Weak spots:** Topics with `mastery_pct < 70%` in `topic_mastery`, top 3 shown on dashboard.

**Streak:** Consecutive calendar days where `study_done = 1 OR quiz_done = 1`. Yesterday counts if today not yet logged.

**Scoring constant:** `PLAN_DAYS = 48` in `db/queries.py` — use this everywhere, not the literal 48.

## Content Structure

**`content/days.py`** — each entry:
```python
{
    "day": 1,
    "title": "...",
    "week": 1,           # 1-7
    "phase": "Foundation",
    "topic": "Subscription Model",   # must match topic_mastery keys
    "estimated_minutes": 60,
    "sections": [{"heading": "...", "body": "...", "exam_tip": "..."}],
    "key_terms": {"Term": "Definition"},
    "docx_override": "Day1/CSM_Day1_Subscription_Model_Study.docx",  # or None
}
```

**`content/questions.py`** — each entry:
```python
{
    "id": "d2_q1",
    "day": 2,
    "topic": "Subscription Model",   # must match days.py topic for same day
    "difficulty": "intermediate",    # basic | intermediate | advanced
    "question": "...",
    "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
    "answer": "B",
    "explanation": "...",            # 50+ words
}
```

**Canonical topic strings** — shared between `days.py`, `questions.py`, and `topic_mastery`:
`"Subscription Model"`, `"Customer Lifecycle"`, `"Adoption Fundamentals"`, `"Cisco Lifecycle Framework"`, `"Mixed Review"`, `"Cisco CX Cloud"`, `"Use Cases & Business Outcomes"`, `"Success Planning"`, `"Stakeholder Management"`, `"Customer Health Scoring"`, `"Expansion Strategies"`, `"Risk Management"`, `"Renewal Management"`, `"QBR & Executive Engagement"`, `"Change Management"`, `"Advocacy & NPS"`, `"CSM Metrics & KPIs"`, `"Cisco CX Specialization"`, `"Cisco Technology Portfolio"`, `"DNA Center & Network Automation"`, `"Collaboration & Webex"`, `"Security & Zero Trust"`, `"Customer Segmentation"`

## Local Dev

```bash
# Create venv (Python 3.11+)
python3.11 -m venv venv
source venv/bin/activate

# Install
pip install -r requirements.txt

# Run app
venv/bin/streamlit run app.py

# Run tests
venv/bin/python -m pytest tests/ -v
```

Expected: **40 tests passing**

## Adding Content for a New Day

1. Add an entry to `DAYS` in `content/days.py` — follow the existing shape exactly
2. Add 10 questions to `QUESTIONS` in `content/questions.py` — `topic` must match `days.py`
3. Run `venv/bin/python -m pytest tests/test_content.py -v` to verify

## Adding a .docx Override for a Day

1. Place the `.docx` in a `DayN/` folder at the project root
2. Set `"docx_override": "DayN/filename.docx"` in the day's entry in `days.py`
3. The loader will parse it automatically; falls back to built-in on any error

## Known Issues / Watch-outs

- **pandas Styler** — use `.map()` not `.applymap()` (removed in pandas 3.x). Already fixed in `3_Stats.py`.
- **`init_db()` in every query function** — intentional for Streamlit's multi-process model; each worker may start fresh.
- **Day 1 questions** — parsed from `Day1/CSM_100_Practice_Questions-Day 1.docx` (100 questions). If the file is missing, falls back to built-in (currently empty for day 1 — add to `questions.py` if needed).
- **`.db` in repo** — intentional; do NOT add `*.db` to `.gitignore`. See `.gitignore` comment.
