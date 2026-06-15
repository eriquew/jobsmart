import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import yaml

# Page config — must be first Streamlit command
st.set_page_config(
    page_title="JobSmart",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

from controller.job_service import JobService
from model.user_repository import UserRepository

# ── Session state defaults ──────────────────────────────────
if "user_id" not in st.session_state:
    st.session_state.user_id = 1

if "selected_job_id" not in st.session_state:
    st.session_state.selected_job_id = None

if "svc" not in st.session_state:
    st.session_state.svc = JobService(user_id=st.session_state.user_id)


def get_service() -> JobService:
    """Returns the active JobService instance."""
    return st.session_state.svc


def switch_user(user_id: int):
    """Switches active user and reloads service."""
    st.session_state.user_id       = user_id
    st.session_state.selected_job_id = None
    st.session_state.svc           = JobService(user_id=user_id)


# ── Import pages ────────────────────────────────────────────
from view.pages.dashboard  import show_dashboard
from view.pages.analytics  import show_analytics
from view.pages.job_detail import show_job_detail
from view.pages.onboarding import show_onboarding


def main():
    user_repo = UserRepository()
    users     = user_repo.get_all_users()

    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/target.png", width=60)
        st.title("JobSmart")
        st.caption("Canadian job search intelligence")
        st.divider()

        # ── User selector ───────────────────────────────────
        st.subheader("👤 Active user")

        user_names = {u["name"]: u["id"] for u in users}
        user_names["➕ Add new user"] = -1

        # Find current user name
        current_user = next(
            (u["name"] for u in users
             if u["id"] == st.session_state.user_id),
            users[0]["name"] if users else "Wilson Erique"
        )

        selected_name = st.selectbox(
            "Select user",
            options=list(user_names.keys()),
            index=list(user_names.keys()).index(current_user)
            if current_user in user_names else 0,
            label_visibility="collapsed"
        )

        selected_id = user_names[selected_name]

        # Switch user if changed
        if selected_id == -1:
            st.session_state.page = "onboarding"
        elif selected_id != st.session_state.user_id:
            switch_user(selected_id)
            st.rerun()

        st.divider()

        # ── Navigation ──────────────────────────────────────
        page = st.radio(
            "Navigation",
            ["🎯 Dashboard", "📊 Analytics"],
            label_visibility="collapsed"
        )

        st.divider()

        # Active user info
        active = user_repo.get_user_by_id(st.session_state.user_id)
        if active:
            st.caption(
                f"**{active['name']}**\n\n"
                f"{active.get('location', 'Canada')}"
            )

    # ── Page routing ────────────────────────────────────────
    current_page = st.session_state.get("page", "dashboard")

    if current_page == "onboarding" or selected_id == -1:
        show_onboarding()
    elif st.session_state.selected_job_id:
        show_job_detail(st.session_state.selected_job_id)
    elif page == "🎯 Dashboard":
        show_dashboard(get_service())
    elif page == "📊 Analytics":
        show_analytics(get_service())


if __name__ == "__main__":
    main()