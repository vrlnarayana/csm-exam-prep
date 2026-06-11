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

# Load data
mastery   = get_topic_mastery()
all_prog  = get_all_progress()
readiness = get_exam_readiness()
streak    = get_streak()
weak      = get_weak_spots(70.0)

scores    = [p["quiz_score"] for p in all_prog if p["quiz_score"] is not None]
avg_score = (sum(scores) / len(scores) * 100) if scores else 0.0
days_done = sum(1 for p in all_prog if p["study_done"] or p["quiz_done"])

# Summary metrics
m1, m2, m3, m4 = st.columns(4)
m1.metric("🔥 Streak", f"{streak} days")
m2.metric("📅 Days done", f"{days_done}/48")
m3.metric("📈 Avg quiz score", f"{avg_score:.0f}%")
m4.metric("🎯 Exam readiness", f"{readiness*100:.0f}%")

st.markdown("---")

# Topic mastery + weekly trend
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
            df_m.style.map(colour_mastery, subset=["Mastery %"]),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Complete a quiz to see topic mastery data.")

with col_r:
    st.subheader("📅 Weekly Score Trend")
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

# Exam readiness
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

# Quiz history
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
