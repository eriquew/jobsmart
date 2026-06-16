import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

st.set_page_config(
    page_title="JobSmart",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

from controller.job_service import JobService
from model.user_repository import UserRepository
from model.database.db_connection import DatabaseConnection

# ── Session state defaults ──────────────────────────────────
if "user_id" not in st.session_state:
    st.session_state.user_id = 1

if "selected_job_id" not in st.session_state:
    st.session_state.selected_job_id = None

if "page" not in st.session_state:
    st.session_state.page = "dashboard"

if "confirm_delete" not in st.session_state:
    st.session_state.confirm_delete = False


def get_service() -> JobService:
    """Always creates fresh service — never cached."""
    return JobService(user_id=st.session_state.user_id)


def switch_user(user_id: int):
    """Switches active user — resets DB connection."""
    st.session_state.user_id         = user_id
    st.session_state.selected_job_id = None
    st.session_state.confirm_delete  = False
    DatabaseConnection._instance     = None


# ── Import pages ────────────────────────────────────────────
from view.dashboard  import show_dashboard
from view.analytics  import show_analytics
from view.job_detail import show_job_detail
from view.onboarding import show_onboarding


def main():
    user_repo = UserRepository()
    users     = user_repo.get_all_users()
    svc       = get_service()

    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/target.png", width=60)
        st.title("JobSmart")
        st.caption("Canadian job search intelligence")
        st.divider()

        # ── User selector ───────────────────────────────────
        st.subheader("👤 Active user")

        user_names = {u["name"]: u["id"] for u in users}
        user_names["➕ Add new user"] = -1

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

        if selected_id == -1:
            st.session_state.page = "onboarding"
        elif selected_id != st.session_state.user_id:
            switch_user(selected_id)
            st.rerun()

        # ── Delete user button ──────────────────────────────
        if st.session_state.user_id != 1:
            if st.button(
                "🗑️ Delete this user",
                use_container_width=True,
                type="secondary"
            ):
                if st.session_state.confirm_delete:
                    user_repo.delete_user(st.session_state.user_id)
                    switch_user(1)
                    st.session_state.page = "dashboard"
                    st.rerun()
                else:
                    st.session_state.confirm_delete = True
                    st.rerun()

            if st.session_state.confirm_delete:
                st.warning("⚠️ Click again to confirm deletion")

        st.divider()

        # ── Navigation ──────────────────────────────────────
        page = st.radio(
            "Navigation",
            ["🎯 Dashboard", "📊 Analytics"],
            label_visibility="collapsed"
        )

        st.divider()

        # ── Active user info ────────────────────────────────
        active = user_repo.get_user_by_id(st.session_state.user_id)
        if active:
            st.caption(
                f"**{active['name']}**\n\n"
                f"{active.get('location', 'Canada')}"
            )

            # Resume download button
            if user_repo.has_resume(st.session_state.user_id):
                resume = user_repo.get_resume_pdf(st.session_state.user_id)
                if resume:
                    st.download_button(
                        label=f"📄 {resume['filename']}",
                        data=resume["pdf_bytes"],
                        file_name=resume["filename"],
                        mime="application/pdf",
                        use_container_width=True
                    )
            else:
                st.caption("No resume on file")

    # ── Page routing ────────────────────────────────────────
    current_page = st.session_state.get("page", "dashboard")

    if current_page == "onboarding" or selected_id == -1:
        show_onboarding()
    elif st.session_state.selected_job_id:
        show_job_detail(st.session_state.selected_job_id)
    elif page == "🎯 Dashboard":
        show_dashboard(svc)
    elif page == "📊 Analytics":
        show_analytics(svc)


if __name__ == "__main__":
    main()