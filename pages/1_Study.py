import streamlit as st
from db.schema import init_db
from db.queries import get_current_day_number, get_day_progress, mark_study_done, log_streak_day
from content.loader import get_day_content
from content.days import DAYS
from datetime import date

st.set_page_config(page_title="Study · CSM Prep", page_icon="📖", layout="wide")
init_db()

# Day selector
current = get_current_day_number()
day_options = {f"Day {d['day']}: {d['title']}": d["day"] for d in DAYS}
default_key = f"Day {current}: {next(d['title'] for d in DAYS if d['day'] == current)}"

selected_label = st.sidebar.selectbox(
    "Select day",
    options=list(day_options.keys()),
    index=list(day_options.keys()).index(default_key),
)
day_num = day_options[selected_label]

# Load content
content = get_day_content(day_num)
progress = get_day_progress(day_num)
sections = content.get("sections", [])
key_terms = content.get("key_terms", {})
source_label = "📄 From your .docx file" if content.get("docx_override") else "📦 Built-in content"

# Header
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

# Section navigator
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

# Key terms
if key_terms:
    st.markdown("---")
    with st.expander("📚 Key Terms Glossary"):
        for term, defn in key_terms.items():
            st.markdown(f"**{term}** — {defn}")
