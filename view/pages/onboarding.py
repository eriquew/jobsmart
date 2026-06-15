import streamlit as st


def show_onboarding():
    st.title("➕ Add New User")
    st.info("Onboarding page coming soon — upload your resume PDF to create your profile.")

    if st.button("← Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()