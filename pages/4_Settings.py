import streamlit as st
from datetime import date
from db.schema import init_db
from db.queries import get_setting, set_setting, reset_progress

st.set_page_config(page_title="Settings · CSM Prep", page_icon="⚙️", layout="wide")
init_db()

st.title("⚙️ Settings")

# Exam date
st.subheader("📅 Exam Date")
current_exam = get_setting("exam_date")
current_dt   = date.fromisoformat(current_exam) if current_exam else date(2026, 7, 29)
new_exam = st.date_input("Your exam date", value=current_dt, min_value=date.today())
if st.button("Save Exam Date"):
    set_setting("exam_date", new_exam.isoformat())
    st.success(f"Exam date saved: {new_exam.strftime('%B %d, %Y')}")

# Name
st.markdown("---")
st.subheader("👤 Your Name")
current_name = get_setting("user_name") or ""
new_name = st.text_input("Display name (shown on dashboard)", value=current_name)
if st.button("Save Name"):
    set_setting("user_name", new_name)
    st.success("Name saved!")

# Start date
st.markdown("---")
st.subheader("📆 Study Start Date")
st.caption("This controls which day number you're on. Change it if you want to re-align the schedule.")
current_start = get_setting("start_date")
current_start_dt = date.fromisoformat(current_start) if current_start else date.today()
new_start = st.date_input("Study start date", value=current_start_dt)
if st.button("Save Start Date"):
    set_setting("start_date", new_start.isoformat())
    st.success(f"Start date saved: {new_start.strftime('%B %d, %Y')}")

# Reset
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

# App info
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
