# CSM Exam Prep App — Design Spec
**Date:** 2026-06-11  
**Exam:** Cisco 820-605 Customer Success Manager Certification  
**Stack:** Streamlit + SQLite + Python  

---

## Overview

A local Streamlit app that guides a single user through the 48-day Cisco 820-605 CSM exam study plan. It provides structured daily study content, instant-feedback practice quizzes, streak-based motivation, automatic weak-spot detection, and a performance dashboard. All data is stored in a local SQLite database. No authentication, no server — runs entirely on the user's machine.

---

## Decisions Made

| Decision | Choice | Rationale |
|---|---|---|
| App structure | Today-First Dashboard (tabs) | Opens on what to do today — no nav overwhelm |
| Quiz feedback | Instant — show answer + explanation immediately | Best for retention |
| Motivation | Light streak + smart weak-spot coaching | Motivating without gimmicky XP/levels |
| Content | Hybrid — built-in for all 48 days, .docx overrides when present | Complete from day 1, accepts richer files |
| Exam date | User-configurable inside the app | Reusable for retakes, not hardcoded |
| Architecture | Modular Streamlit multi-page | Clean separation of UI, DB, content layers |

---

## Folder Structure

```
csm_exam_prep/
├── app.py                          # Entry point — Today dashboard
├── requirements.txt
├── pages/
│   ├── 1_Study.py                  # Study material reader
│   ├── 2_Quiz.py                   # Practice questions + instant feedback
│   ├── 3_Stats.py                  # Progress, topic mastery, performance
│   └── 4_Settings.py               # Exam date, reset, preferences
├── db/
│   ├── schema.py                   # SQLite table definitions + init
│   └── queries.py                  # All read/write functions (no SQL in UI)
├── content/
│   ├── days.py                     # 48-day plan + built-in study notes
│   ├── questions.py                # Practice questions for all 48 days
│   └── loader.py                   # .docx override parser (python-docx)
├── data/
│   └── csm_prep.db                 # Auto-created on first run
└── Day1/                           # Existing .docx files (auto-detected)
    ├── CSM_Day1_Subscription_Model_Study.docx
    └── CSM_100_Practice_Questions-Day 1.docx
```

---

## Database Schema

### `settings` — global app config
```sql
CREATE TABLE settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
-- Rows: exam_date, start_date, user_name
```

### `daily_progress` — one row per study day (1–48)
```sql
CREATE TABLE daily_progress (
    day_number   INTEGER PRIMARY KEY,  -- 1 to 48
    study_done   BOOLEAN DEFAULT 0,
    quiz_done    BOOLEAN DEFAULT 0,
    completed_at DATE,                 -- date when both study_done AND quiz_done (cosmetic only)
    quiz_score   REAL,                 -- 0.0–1.0, most recent attempt
    best_score   REAL                  -- 0.0–1.0, best ever for this day
);
```

### `quiz_attempts` — one row per question answered
```sql
CREATE TABLE quiz_attempts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    day_number   INTEGER NOT NULL,
    question_id  TEXT NOT NULL,        -- e.g. "d1_q3"
    topic        TEXT NOT NULL,        -- e.g. "Subscription Model"
    correct      BOOLEAN NOT NULL,
    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### `topic_mastery` — auto-computed after every quiz
```sql
CREATE TABLE topic_mastery (
    topic          TEXT PRIMARY KEY,
    total_attempts INTEGER DEFAULT 0,
    correct_count  INTEGER DEFAULT 0,
    mastery_pct    REAL DEFAULT 0.0,   -- correct_count / total_attempts * 100
    last_attempted DATE
);
```

### `streak_log` — one row per calendar day studied
```sql
CREATE TABLE streak_log (
    study_date     DATE PRIMARY KEY,
    days_studied   INTEGER,            -- running total
    streak_at_date INTEGER            -- consecutive days at this date
);
```

---

## Content Layer

### `content/days.py`
Each day is a Python dict with this shape:
```python
{
    "day": 11,
    "title": "Stakeholder Management",
    "week": 2,
    "phase": "Core Concepts",
    "topic": "Stakeholder Management",      # must match topic_mastery key
    "estimated_minutes": 45,
    "sections": [
        {
            "heading": "Identifying Stakeholders",
            "body": "...",
            "exam_tip": "The CSM identifies Champion and Executive Sponsor separately..."
        },
        # 3–5 more sections
    ],
    "key_terms": {
        "Champion": "Day-to-day contact who advocates for the solution internally",
        "Executive Sponsor": "Senior stakeholder who owns strategic outcomes"
    },
    "docx_override": "Day11/CSM_Day11_Study.docx"   # checked at runtime; None if not present
}
```

Day 1 uses the existing `.docx` file. Days 2–48 use built-in dict content.

### `content/questions.py`
Each question:
```python
{
    "id": "d11_q3",
    "day": 11,
    "topic": "Stakeholder Management",
    "difficulty": "intermediate",       # basic | intermediate | advanced
    "question": "A key champion has just left...",
    "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
    "answer": "C",
    "explanation": "The FIRST step is internal mapping..."
}
```

- Day 1: 100 questions parsed from the existing `.docx` file via `loader.py`
- Days 2–48: 10 questions each, built into `questions.py`
- Total: ~580 questions across all 48 days

### `content/loader.py`
- On startup, checks each `DayN/` folder for `.docx` files
- If study `.docx` present → parses with `python-docx`, returns structured sections
- If questions `.docx` present → parses Q/A/explanation blocks, returns question list
- Falls back silently to built-in content if no `.docx` found
- Day 1 `.docx` parsing: extracts questions by detecting `Q` / `A` / `Correct Answer` markers

---

## Page Designs

### `app.py` — Today Dashboard
**Layout (top to bottom):**
1. Header — "📘 CSM Exam Prep" + streak badge (🔥 N-day streak)
2. Progress bar — "Day N of 48 · Week X: Phase Name" + days-left counter
3. Today's checklist — Study card + Quiz card. Each card has a direct action button
4. Weak-spot alert panel — appears if any topic < 70% mastery; lists flagged topics with links to revisit
5. Quick-stats row — Quiz avg % · Days done · Best topic · Days left

**First-run behaviour:** If `exam_date` not set in `settings`, show a date picker prompt before the dashboard. Store selection in `settings` and derive `start_date = today`, `day_number = 1`.

**Current day logic:** `day_number = (today - start_date).days + 1`, clamped to 1–48.

---

### `pages/1_Study.py` — Study Material
**Layout:**
1. Day title + week/phase label + estimated time + source badge (built-in vs .docx)
2. Section navigator — previous/next buttons, section N of M indicator
3. Current section: heading + body text + exam tip callout (blue highlight box)
4. Key terms expander at the bottom
5. "Mark as Read" button — sets `study_done = True` in `daily_progress`

---

### `pages/2_Quiz.py` — Practice Quiz
**Layout:**
1. Day selector (default = today; can pick any day from Day 1 up to today)
2. Question progress bar (dot indicators, coloured green/blue/grey)
3. Question text + difficulty badge
4. Four radio options (A/B/C/D)
5. Submit button → instant reveal: correct option highlighted green, chosen wrong option highlighted red, explanation panel shown
6. Next question button
7. End-of-quiz summary: score, correct count, time taken, topic breakdown
8. Updates `quiz_attempts`, `topic_mastery`, `daily_progress` on completion

**Retry logic:** User can retry the same day's quiz; `quiz_score` updates to latest, `best_score` only updates if improved.

---

### `pages/3_Stats.py` — Performance Dashboard
**Layout (two columns):**
- Left: Topic mastery horizontal bar chart (all topics, colour-coded: green ≥ 70%, amber 50–70%, red < 50%)
- Right: Weekly average score bar chart (W1–W7, greyed for future weeks)

**Below:**
- Exam readiness score: `(days_done/48 × 0.4) + (avg_quiz_score × 0.6)` rendered as progress bar with label
- Quiz history table: day, date, score, best score — sortable
- Streak history: calendar heatmap (Streamlit `st.dataframe` with colour formatting)

---

### `pages/4_Settings.py` — Settings
- **Exam date picker** — updates `settings.exam_date`; recalculates all day counters
- **Your name** — stored in `settings.user_name`, shown in dashboard greeting
- **Study start date** — auto-set on first run; can be overridden here
- **Reset progress** — wipes `daily_progress`, `quiz_attempts`, `topic_mastery`, `streak_log` (requires confirmation)
- **App info** — version, study plan reference

---

## Quiz Engine — Weak-Spot Detection

```
After every quiz submission:
  1. Insert one row per question into quiz_attempts
  2. For each topic in this quiz:
       total_attempts = COUNT(*) from quiz_attempts WHERE topic = X
       correct_count  = COUNT(*) from quiz_attempts WHERE topic = X AND correct = 1
       mastery_pct    = correct_count / total_attempts * 100
       UPDATE topic_mastery SET ... WHERE topic = X
  3. On Today dashboard load:
       weak_spots = SELECT topic FROM topic_mastery WHERE mastery_pct < 70 ORDER BY mastery_pct ASC LIMIT 3
       Show weak-spot alert panel if len(weak_spots) > 0
```

**Exam readiness formula:**
```
days_done     = COUNT(*) FROM daily_progress WHERE study_done = 1 OR quiz_done = 1
avg_score     = AVG(quiz_score) FROM daily_progress WHERE quiz_score IS NOT NULL
readiness_pct = (days_done / 48 * 0.4) + (avg_score * 0.6)
```

**Streak logic:**
```
streak = 0
for each calendar day from start_date to today (descending):
    if day in streak_log → streak += 1
    else → break
```
A day is logged to `streak_log` when `study_done = 1` OR `quiz_done = 1` is set. (`completed_at` in `daily_progress` is separate — it records when BOTH are done, used only for display.)

---

## Content Coverage — 48 Days

| Days | Phase | Topics |
|---|---|---|
| 1–2 | Foundation | Subscription Model (ARR, MRR, TCV, NRR, GRR, churn) |
| 3–7 | Foundation | Customer Lifecycle (onboard, adopt, expand, renew, advocate) + Cisco PPDIOO |
| 8–14 | Core Concepts | Cisco CX Cloud, telemetry, use cases, success planning, stakeholder mgmt, health scoring, expansion |
| 15–21 | Advanced Topics | Risk management, renewals, QBR, change management (ADKAR), advocacy, CSM metrics/KPIs |
| 22–28 | Cisco Specializations | CX Partner Spec, LCI, DNA Center, Webex, Zero Trust, scaled CS |
| 29–35 | Integration & Practice | Scenario-based practice per topic, mock exam #2, weak area deep dives |
| 36–48 | Final Preparation + Sprint | Comprehensive reviews, mock exams #3 and #4, cheat sheet, rest days |

**Question counts:**
- Day 1: 100 questions (parsed from existing `.docx`)
- Days 2–48: 10 questions each (built-in)
- Total: ~580 questions

---

## Tech Stack & Dependencies

```
streamlit>=1.35
python-docx>=1.1
pandas>=2.0          # stats tables
altair>=5.0          # charts (via streamlit)
```

All other libraries (sqlite3, datetime, pathlib) are Python stdlib.

---

## Key Constraints

- **Solo use only** — no login, no multi-user. Settings table has one logical row set.
- **Offline** — no external API calls. All content is local.
- **DB path** — `data/csm_prep.db` relative to the project root, auto-created on first run.
- **`.docx` parsing is best-effort** — if a `.docx` is malformed, loader falls back to built-in silently. No crash.
- **Day number is calendar-based** — derived from `(today - start_date).days + 1`. Skipping days advances the counter; the user can still go back and complete any past day.
