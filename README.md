# CSM Exam Prep — Cisco 820-605

A local Streamlit app that guides you through a 48-day study plan for the **Cisco 820-605 Customer Success Manager** certification exam.

## Features

- **Today Dashboard** — daily checklist, streak tracker, weak-spot alerts, exam readiness score
- **Study Page** — section-by-section reader with exam tips and key terms glossary
- **Quiz Page** — instant-feedback practice questions with explanations
- **Stats Page** — topic mastery chart, weekly score trend, full quiz history
- **Settings** — exam date, name, start date, progress reset

## Content

| Source | Count |
|--------|-------|
| Study days | 48 (built-in notes + Day 1 `.docx` override) |
| Practice questions | ~570 (100 from Day 1 `.docx` + 470 built-in for days 2–48) |
| Topics covered | Subscription Model, Customer Lifecycle, Adoption, Cisco CX Cloud, Health Scoring, Risk Management, Renewals, QBR, Change Management (ADKAR), Advocacy/NPS, CSM Metrics, Cisco Technology Portfolio, and more |

## Quick Start (local)

```bash
# Clone
git clone https://github.com/vrlnarayana/csm-exam-prep.git
cd csm-exam-prep

# Create virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run
streamlit run app.py
```

Open **http://localhost:8501**, enter your exam date on the setup screen, and start studying.

## Project Structure

```
csm-exam-prep/
├── app.py                    # Today dashboard (entry point)
├── requirements.txt
├── pages/
│   ├── 1_Study.py            # Study material reader
│   ├── 2_Quiz.py             # Quiz engine
│   ├── 3_Stats.py            # Performance dashboard
│   └── 4_Settings.py         # Settings
├── db/
│   ├── schema.py             # SQLite schema + init
│   └── queries.py            # All DB read/write functions
├── content/
│   ├── days.py               # 48-day study notes
│   ├── questions.py          # Practice questions (days 2–48)
│   └── loader.py             # .docx parser + built-in fallback
├── data/
│   └── csm_prep.db           # SQLite database (pre-seeded for Streamlit Cloud)
├── Day1/
│   ├── CSM_Day1_Subscription_Model_Study.docx
│   └── CSM_100_Practice_Questions-Day 1.docx
└── tests/
    ├── conftest.py
    ├── test_db.py
    └── test_content.py
```

## Tech Stack

| Layer | Tech |
|-------|------|
| UI | Streamlit 1.35+ |
| Database | SQLite (stdlib) |
| Content parsing | python-docx |
| Data tables | pandas 2.0+ |
| Tests | pytest |
| Python | 3.11+ |

## Exam Readiness Formula

```
readiness = (days_done / 48 × 0.4) + (avg_quiz_score × 0.6)
```

Quiz score is weighted higher (60%) because it's a stronger predictor of actual exam performance than coverage alone. Target: **75%+** before exam day.

## Deploying to Streamlit Cloud

1. Fork or connect this repo at [share.streamlit.io](https://share.streamlit.io)
2. Set **Main file path** to `app.py`
3. Deploy — no secrets or env vars required
4. The `data/csm_prep.db` file is included so the app has data on first run

## Running Tests

```bash
venv/bin/python -m pytest tests/ -v
```

Expected: **40 tests passing**
