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

# First-run: collect exam date
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

# Load state
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

# Header
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

# Progress bar
st.markdown("---")
pct = int(days_done / 48 * 100)
st.markdown(f"**Day {day_num} of 48 · Week {day_meta['week']}: {day_meta['phase']}**")
st.progress(pct / 100)
st.caption(f"{pct}% complete · {days_left} days until exam · {day_meta['title']}")

# Today's checklist
st.markdown("---")
st.subheader(f"📋 Today — {day_meta['title']}")

c1, c2 = st.columns(2)
with c1:
    study_icon = "✅" if progress["study_done"] else "📖"
    study_label = "Study complete" if progress["study_done"] else "Read today's material"
    bg = "#064e3b" if progress["study_done"] else "#1e3a5f"
    st.markdown(
        f"<div style='background:{bg};padding:12px;border-radius:8px;color:#ffffff;'>"
        f"<strong>{study_icon} {study_label}</strong></div>",
        unsafe_allow_html=True,
    )
    if not progress["study_done"]:
        st.page_link("pages/1_Study.py", label="Open Study →", icon="📖")

with c2:
    quiz_icon = "✅" if progress["quiz_done"] else "✏️"
    quiz_score_str = f" · {progress['quiz_score']*100:.0f}%" if progress.get("quiz_score") else ""
    quiz_label = f"Quiz complete{quiz_score_str}" if progress["quiz_done"] else "Take today's quiz"
    bg2 = "#064e3b" if progress["quiz_done"] else "#1e293b"
    st.markdown(
        f"<div style='background:{bg2};padding:12px;border-radius:8px;color:#ffffff;'>"
        f"<strong>{quiz_icon} {quiz_label}</strong></div>",
        unsafe_allow_html=True,
    )
    if not progress["quiz_done"]:
        st.page_link("pages/2_Quiz.py", label="Start Quiz →", icon="✏️")

# Weak-spot alert
if weak:
    st.markdown("---")
    st.warning("⚠️ **Weak Spots — review recommended before your exam**")
    for w in weak:
        day_for_topic = next((d["day"] for d in DAYS if d["topic"] == w["topic"]), None)
        st.markdown(
            f"**{w['topic']}** — {w['mastery_pct']:.0f}% mastery "
            f"({w['correct_count']}/{w['total_attempts']} correct)"
            + (f" · [Revisit Day {day_for_topic}](pages/1_Study.py)" if day_for_topic else "")
        )

# Quick stats
st.markdown("---")
s1, s2, s3, s4 = st.columns(4)
s1.metric("Quiz avg", f"{avg_score:.0f}%", help="Average quiz score across all completed days")
s2.metric("Days done", f"{days_done}", help="Days with at least one activity completed")
s3.metric("Best topic", f"{best_pct:.0f}%" if best_topics else "–", help="Your highest-mastery topic")
s4.metric("Days left", f"{days_left}", help="Calendar days until your exam")

# Exam readiness
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
