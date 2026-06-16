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

    # ── Exclusions ──────────────────────────────────────────
    st.subheader("Exclusions (optional)")

    col1, col2 = st.columns(2)
    with col1:
        hard_exclude = st.multiselect(
            "Hard exclude — score = 0% if found",
            options=[
                "french required",
                "bilingual french",
                "français exigé",
                "security clearance required",
                "top secret clearance",
                "relocation required"
            ],
            default=[],
            help="Jobs containing these terms will score 0%"
        )
    with col2:
        soft_exclude = st.multiselect(
            "Soft exclude — score reduced by 15%",
            options=[
                "relocation required",
                "must relocate",
                "on-site only",
                "no remote"
            ],
            default=[],
            help="Jobs containing these terms lose 15 points"
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
        st.success(
            f"✅ File uploaded: {uploaded_file.name} "
            f"({uploaded_file.size:,} bytes)"
        )

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
            # Store PDF in session state for saving later
            st.session_state.pdf_bytes    = pdf_bytes
            st.session_state.pdf_filename = uploaded_file.name

        with st.spinner("Analyzing resume with AI — this takes 10-20 seconds..."):
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

        # Override target locations and exclusions with user selection
        profile.setdefault("personal", {})
        profile["personal"]["target_locations"] = target_location
        profile["personal"]["name"]             = name
        profile["personal"]["location"]         = location
        profile["exclusions"] = {
            "hard_exclude": hard_exclude,
            "soft_exclude": soft_exclude
        }

        # Store in session state for preview
        st.session_state.generated_profile = profile
        st.session_state.new_user_name     = name
        st.session_state.new_user_email    = email
        st.session_state.new_user_location = location
        st.session_state.hard_exclude      = hard_exclude
        st.session_state.soft_exclude      = soft_exclude
        st.rerun()

    # ── Step 4: Preview and confirm ─────────────────────────
    if "generated_profile" in st.session_state and \
       st.session_state.generated_profile:

        profile = st.session_state.generated_profile

        st.divider()
        st.subheader("Step 4 — Review and confirm profile")
        st.success("Profile generated successfully. Review before saving.")

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

            st.markdown("**Exclusions:**")
            hard = profile.get("exclusions", {}).get("hard_exclude", [])
            soft = profile.get("exclusions", {}).get("soft_exclude", [])
            if hard:
                st.markdown(f"Hard: {', '.join(hard)}")
            if soft:
                st.markdown(f"Soft: {', '.join(soft)}")
            if not hard and not soft:
                st.markdown("None — all jobs will be considered")

        st.divider()

        # ── YAML Editor ─────────────────────────────────────
        st.subheader("✏️ Edit profile YAML (optional)")
        st.caption(
            "You can edit the YAML directly before saving. "
            "Fix titles, add or remove skills, adjust industries. "
            "Click 'Apply changes' to update the preview."
        )

        yaml_text = yaml.dump(
            profile,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=True
        )

        edited_yaml = st.text_area(
            "Profile YAML",
            value=yaml_text,
            height=500,
            label_visibility="collapsed"
        )

        col_apply, col_reset = st.columns([1, 3])
        with col_apply:
            if st.button("✅ Apply changes", use_container_width=True):
                try:
                    updated = yaml.safe_load(edited_yaml)
                    if isinstance(updated, dict):
                        st.session_state.generated_profile = updated
                        st.success("Profile updated")
                        st.rerun()
                    else:
                        st.error("Invalid YAML structure")
                except yaml.YAMLError as e:
                    st.error(f"YAML error: {e}")

        with col_reset:
            st.caption(
                "💡 Tips: Fix inverted titles like 'Network Architect Senior' "
                "→ 'Senior Network Architect'. "
                "Remove skills that are not searchable. "
                "Add missing skills from your resume."
            )

        st.divider()

        # ── Save or regenerate ───────────────────────────────
        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "💾 Save Profile & Create User",
                type="primary",
                use_container_width=True
            ):
                # Use the current session state profile
                # (may have been updated by editor)
                final_profile = st.session_state.generated_profile

                repo    = UserRepository()
                user_id = repo.create_user(
                    name=st.session_state.new_user_name,
                    email=st.session_state.new_user_email or None,
                    location=st.session_state.new_user_location,
                    profile_yaml=final_profile
                )

                if user_id:
                    # Save PDF to DB
                    if st.session_state.get("pdf_bytes"):
                        repo.save_resume_pdf(
                            user_id=user_id,
                            pdf_bytes=st.session_state.pdf_bytes,
                            filename=st.session_state.get(
                                "pdf_filename", "resume.pdf"
                            )
                        )
                        del st.session_state.pdf_bytes

                    st.success(
                        f"User '{st.session_state.new_user_name}' "
                        f"created with resume on file!"
                    )

                    from controller.job_service import JobService
                    new_svc = JobService(user_id=user_id)

                    with st.spinner("Scoring all jobs for new user..."):
                        result = new_svc.score_all_jobs()

                    st.success(
                        f"{result['scored']} jobs scored for "
                        f"{st.session_state.new_user_name}"
                    )

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
                if "pdf_bytes" in st.session_state:
                    del st.session_state.pdf_bytes
                st.rerun()