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

# Day selector
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

# Load questions
if "quiz_questions" not in st.session_state:
    all_qs = get_day_questions(day_num)
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

# Progress dots
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

# Complete state
if complete:
    correct_count = sum(1 for i, q in enumerate(questions) if answers.get(i) == q["answer"])
    score = correct_count / len(questions)
    st.balloons()
    st.success(f"## Quiz Complete! You scored {correct_count}/{len(questions)} ({score*100:.0f}%)")

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

# Active quiz
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
