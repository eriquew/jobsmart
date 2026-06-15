import streamlit as st
import yaml
from dotenv import load_dotenv

load_dotenv()

from controller.resume_parser import ResumeParser
from model.user_repository import UserRepository


def show_onboarding():
    """
    Onboarding page — new user uploads resume PDF
    and system generates their profile automatically.
    """

    if st.button("← Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()

    st.title("➕ Add New User")
    st.caption("Upload a resume PDF to automatically generate a job matching profile")
    st.divider()

    # ── Step 1: Basic info ──────────────────────────────────
    st.subheader("Step 1 — Basic information")

    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input(
            "Full name",
            placeholder="e.g. Maria Garcia"
        )
        email = st.text_input(
            "Email (optional)",
            placeholder="e.g. maria@gmail.com"
        )
    with col2:
        location = st.text_input(
            "Location",
            placeholder="e.g. Toronto, ON",
            value="Ontario, Canada"
        )
        target_location = st.multiselect(
            "Target work locations",
            options=[
                "toronto", "hamilton", "mississauga", "ottawa",
                "waterloo", "niagara", "burlington", "remote",
                "ontario", "vancouver", "montreal"
            ],
            default=["ontario", "toronto", "remote"]
        )

    st.divider()

    # ── Step 2: Resume upload ───────────────────────────────
    st.subheader("Step 2 — Upload resume PDF")

    uploaded_file = st.file_uploader(
        "Choose your resume PDF",
        type=["pdf"],
        help="Your resume will be analyzed by AI to extract skills, experience, and target roles"
    )

    if uploaded_file:
        st.success(f"✅ File uploaded: {uploaded_file.name} ({uploaded_file.size:,} bytes)")

    st.divider()

    # ── Step 3: Generate profile ────────────────────────────
    st.subheader("Step 3 — Generate profile")

    if not name:
        st.warning("Please enter a name before generating the profile.")
        return

    if not uploaded_file:
        st.warning("Please upload a resume PDF before generating the profile.")
        return

    if st.button(
        "🤖 Generate Profile with AI",
        type="primary",
        use_container_width=True
    ):
        with st.spinner("Reading PDF..."):
            pdf_bytes = uploaded_file.read()

        with st.spinner(f"Analyzing resume with Claude AI — this takes 10-20 seconds..."):
            parser  = ResumeParser()
            profile = parser.parse(
                pdf_bytes=pdf_bytes,
                user_name=name,
                user_location=location
            )

        if not profile:
            st.error(
                "Could not generate profile from this PDF. "
                "Make sure the PDF contains readable text (not a scanned image)."
            )
            return

        # Override target locations with user selection
        if target_location:
            profile.setdefault("personal", {})
            profile["personal"]["target_locations"] = target_location
            profile["personal"]["name"]     = name
            profile["personal"]["location"] = location

        # Store in session state for preview
        st.session_state.generated_profile = profile
        st.session_state.new_user_name     = name
        st.session_state.new_user_email    = email
        st.session_state.new_user_location = location
        st.rerun()

    # ── Step 4: Preview and confirm ─────────────────────────
    if "generated_profile" in st.session_state and st.session_state.generated_profile:
        profile = st.session_state.generated_profile

        st.divider()
        st.subheader("Step 4 — Review and confirm profile")
        st.success("Profile generated successfully. Review before saving.")

        # Show key extracted info
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Target titles (high priority):**")
            titles = profile.get("target_titles", {}).get("high_priority", [])
            for t in titles:
                st.markdown(f"- {t}")

            st.markdown("**Expert skills:**")
            expert = profile.get("skills", {}).get("expert", [])
            st.markdown(", ".join(expert) if expert else "None detected")

        with col2:
            st.markdown("**Proficient skills:**")
            proficient = profile.get("skills", {}).get("proficient", [])
            st.markdown(", ".join(proficient) if proficient else "None detected")

            st.markdown("**Industries:**")
            strong = profile.get("industries", {}).get("strong", [])
            st.markdown(", ".join(strong) if strong else "None detected")

        # Show full YAML for transparency
        with st.expander("View full profile YAML"):
            st.code(
                yaml.dump(profile, allow_unicode=True,
                          default_flow_style=False),
                language="yaml"
            )

        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            if st.button(
                "✅ Save Profile & Create User",
                type="primary",
                use_container_width=True
            ):
                repo    = UserRepository()
                user_id = repo.create_user(
                    name=st.session_state.new_user_name,
                    email=st.session_state.new_user_email or None,
                    location=st.session_state.new_user_location,
                    profile_yaml=profile
                )

                if user_id:
                    st.success(
                        f"User '{st.session_state.new_user_name}' "
                        f"created successfully!"
                    )

                    # Switch to new user and score jobs
                    from controller.job_service import JobService
                    new_svc = JobService(user_id=user_id)

                    with st.spinner("Scoring all jobs for new user..."):
                        result = new_svc.score_all_jobs()

                    st.success(
                        f"{result['scored']} jobs scored for "
                        f"{st.session_state.new_user_name}"
                    )

                    # Clear session and switch user
                    del st.session_state.generated_profile
                    st.session_state.user_id = user_id
                    st.session_state.svc     = new_svc
                    st.session_state.page    = "dashboard"
                    st.rerun()

                else:
                    st.error(
                        "Error creating user. "
                        "A user with this name may already exist."
                    )

        with col2:
            if st.button(
                "🔄 Regenerate Profile",
                use_container_width=True
            ):
                del st.session_state.generated_profile
                st.rerun()