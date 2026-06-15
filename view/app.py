import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

# Page config — must be first Streamlit command
st.set_page_config(
    page_title="JobSmart",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import pages
from view.pages.dashboard import show_dashboard
from view.pages.analytics import show_analytics
from view.pages.job_detail import show_job_detail

# ── Navigation ─────────────────────────────────────────────
def main():
    # Sidebar navigation
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/target.png", width=60)
        st.title("JobSmart")
        st.caption("Canadian job search intelligence")
        st.divider()

        page = st.radio(
            "Navigation",
            ["🎯 Dashboard", "📊 Analytics"],
            label_visibility="collapsed"
        )

        st.divider()
        st.caption("Wilson Erique · Niagara Falls, ON")

    # Route to page
    if "selected_job_id" in st.session_state and st.session_state.selected_job_id:
        show_job_detail(st.session_state.selected_job_id)
    elif page == "🎯 Dashboard":
        show_dashboard()
    elif page == "📊 Analytics":
        show_analytics()


if __name__ == "__main__":
    main()