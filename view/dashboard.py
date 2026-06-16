import streamlit as st
import pandas as pd
import subprocess
import sys
import os
from datetime import datetime

from controller.job_service import JobService
def run_pipeline(svc: JobService, keywords: str, location: str):
    """Triggers pipeline run with custom keywords and location."""

    with st.spinner(f"Fetching and scoring jobs — '{keywords}' in '{location}'..."):
        result = subprocess.run(
            [sys.executable, "controller/pipeline.py",
             "--keywords", keywords,
             "--location", location,
             "--max", "25",
             "--user_id", str(svc.user_id)],
            capture_output=True, text=True, cwd=os.getcwd()
        )

    if result.returncode == 0:
        st.success("Pipeline complete — refresh to see new jobs")
    else:
        st.warning("Pipeline finished with some errors")
        if result.stderr:
            with st.expander("Error details"):
                st.code(result.stderr[-2000:])

    # Force session state reload
    st.session_state.svc = JobService(user_id=svc.user_id)

    import time
    time.sleep(1)
    st.rerun()
    
def score_badge(score: float) -> str:
    """Returns colored score badge."""
    if score >= 75:
        return f"🟢 {score}%"
    elif score >= 50:
        return f"🟡 {score}%"
    elif score >= 30:
        return f"🟠 {score}%"
    else:
        return f"🔴 {score}%"


def show_dashboard(svc: JobService = None):
    """Main dashboard page."""
    if svc is None:
        svc = JobService(user_id=1)

    # ── Header metrics ──────────────────────────────────────
    counts = svc.get_counts()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Jobs", counts.get("total", 0))
    col2.metric("New Today",  counts.get("today", 0))
    col3.metric("Applied",    counts.get("applied", 0))
    col4.metric("Unreviewed", counts.get("new_jobs", 0))

    st.divider()

    # ── Sidebar ─────────────────────────────────────────────
    with st.sidebar:

        # ── Search configuration ────────────────────────────
        st.subheader("🔎 Search Configuration")

        # Load keywords from active user profile
        profile    = svc.user_repo.get_profile(svc.user_id)
        default_kw = "solutions architect, presales engineer"

        if profile:
            titles     = profile.get("target_titles", {})
            high       = titles.get("high_priority", [])
            mid        = titles.get("medium_priority", [])
            all_titles = high[:3] + mid[:2]
            if all_titles:
                default_kw = ", ".join(all_titles)

        # Per-user session key — resets when user switches
        user_kw_key = f"keywords_user_{svc.user_id}"
        if user_kw_key not in st.session_state:
            st.session_state[user_kw_key] = default_kw

        keywords_input = st.text_area(
            "Job keywords (comma-separated)",
            value=st.session_state[user_kw_key],
            height=100,
            help="Pre-populated from your profile. Edit freely and click Run Pipeline.",
            key=f"kw_input_{svc.user_id}"
        )

        st.session_state[user_kw_key] = keywords_input

        # Location selector
        location_options = {
            "Ontario, Canada (all)": "Ontario Canada",
            "Toronto, ON":           "Toronto Ontario",
            "Hamilton, ON":          "Hamilton Ontario",
            "Mississauga, ON":       "Mississauga Ontario",
            "Ottawa, ON":            "Ottawa Ontario",
            "Waterloo / Kitchener":  "Waterloo Ontario",
            "Remote (Canada)":       "Remote Canada",
            "Custom...":             "custom"
        }

        selected_location = st.selectbox(
            "Location",
            options=list(location_options.keys()),
            index=0,
            key=f"loc_{svc.user_id}"
        )

        if selected_location == "Custom...":
            custom_location = st.text_input(
                "Enter location",
                placeholder="e.g. Vancouver British Columbia",
                key=f"custom_loc_{svc.user_id}"
            )
            location_value = custom_location or "Ontario Canada"
        else:
            location_value = location_options[selected_location]

        if st.button(
            "🔄 Run Pipeline Now",
            use_container_width=True,
            type="primary",
            key=f"run_pipeline_{svc.user_id}"
        ):
            keywords_clean = ", ".join([
                kw.strip()
                for kw in keywords_input.split(",")
                if kw.strip()
            ])
            run_pipeline(svc, keywords_clean, location_value)

        st.caption(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}")
        st.divider()

        # ── Results filters ─────────────────────────────────
        st.subheader("📋 Filter Results")

        keyword_filter = st.text_input(
            "🔍 Search in results",
            placeholder="e.g. CCIE, presales, Cisco...",
            help="Filters results by title, company, or matched skills",
            key=f"kw_filter_{svc.user_id}"
        )

        min_score = st.slider(
            "Minimum score %",
            min_value=0,
            max_value=100,
            value=30,
            step=5,
            key=f"min_score_{svc.user_id}"
        )

        sources = svc.get_sources()
        selected_sources = st.multiselect(
            "Sources",
            options=sources,
            default=sources,
            key=f"sources_{svc.user_id}"
        )

        hide_french = st.toggle(
            "Hide French-required roles",
            value=True,
            key=f"hide_french_{svc.user_id}"
        )

        status_filter = st.selectbox(
            "Application status",
            options=["All", "new", "reviewed", "applied",
                     "interview", "rejected"],
            index=0,
            key=f"status_{svc.user_id}"
        )

    # ── Fetch jobs ──────────────────────────────────────────
    status = None if status_filter == "All" else status_filter

    jobs = svc.get_ranked_jobs(
        min_score=min_score,
        sources=selected_sources if selected_sources else None,
        status=status,
        hide_french=hide_french,
        limit=200
    )

    # Apply keyword filter client-side
    if keyword_filter:
        kw   = keyword_filter.lower()
        jobs = [
            j for j in jobs
            if kw in (j.get("title") or "").lower()
            or kw in (j.get("company") or "").lower()
            or kw in (j.get("extracted_skills") or "").lower()
            or kw in (j.get("description") or "").lower()
        ]

    if not jobs:
        st.info(
            "No jobs match your filters. "
            "Try lowering the minimum score or running the pipeline."
        )
        return

    st.subheader(f"Ranked Jobs — {len(jobs)} results")

    # ── Build display dataframe ─────────────────────────────
    rows = []
    for j in jobs:
        salary = ""
        if j.get("salary_min") and j.get("salary_max"):
            salary = f"${j['salary_min']:,}–${j['salary_max']:,}"
        elif j.get("salary_min"):
            salary = f"${j['salary_min']:,}+"

        rows.append({
            "id":       j["id"],
            "Score":    score_badge(j["score_total"]),
            "Title":    j["title"],
            "Company":  j["company"],
            "Location": j["location"],
            "Salary":   salary,
            "Source":   j["source"],
            "Posted":   str(j["date_posted"]) if j["date_posted"] else "",
            "Status":   j["status"],
            "🇫🇷":      "🇫🇷" if j["flag_french_required"] else "",
            "🔗 Apply": j.get("url", "")
        })

    df = pd.DataFrame(rows)

    st.dataframe(
        df.drop(columns=["id"]),
        use_container_width=True,
        hide_index=True,
        height=500,
        column_config={
            "🔗 Apply": st.column_config.LinkColumn(
                "🔗 Apply",
                display_text="Apply →"
            )
        }
    )

    # ── Job detail selector ─────────────────────────────────
    st.divider()
    st.subheader("View Job Detail")

    job_options = {
        f"{j['score_total']}% — {j['title']} @ {j['company']}": j["id"]
        for j in jobs
    }

    selected = st.selectbox(
        "Select a job to view full details",
        options=list(job_options.keys()),
        key=f"job_select_{svc.user_id}"
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button(
            "View Details →",
            use_container_width=True,
            key=f"view_detail_{svc.user_id}"
        ):
            st.session_state.selected_job_id = job_options[selected]
            st.rerun()