import streamlit as st
import pandas as pd
import subprocess
import sys
import os
from datetime import datetime

from controller.job_service import JobService

svc = JobService()


def run_pipeline(keywords: str, location: str):
    """Triggers pipeline run with custom keywords and location."""
    with st.spinner(f"Fetching jobs — '{keywords}' in '{location}'..."):
        result = subprocess.run(
            [sys.executable, "controller/pipeline.py",
             "--keywords", keywords,
             "--location", location,
             "--max", "25"],
            capture_output=True, text=True, cwd=os.getcwd()
        )

    with st.spinner("Scoring new jobs..."):
        score_result = svc.score_all_jobs()

    if result.returncode == 0:
        st.success(
            f"Pipeline complete — "
            f"{score_result['scored']} new jobs scored"
        )
    else:
        st.warning("Pipeline finished with some errors")
        if result.stderr:
            with st.expander("Error details"):
                st.code(result.stderr[-2000:])

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


def show_dashboard():
    """Main dashboard page."""

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

        # Keywords input
        keywords_input = st.text_area(
            "Job keywords (comma-separated)",
            value="solutions architect, presales engineer, network architect, cloud architect",
            height=100,
            help="Enter keywords separated by commas. Each keyword runs as a separate search term."
        )

        # Location selector
        location_options = {
            "Ontario, Canada (all)":  "Ontario Canada",
            "Toronto, ON":            "Toronto Ontario",
            "Hamilton, ON":           "Hamilton Ontario",
            "Mississauga, ON":        "Mississauga Ontario",
            "Ottawa, ON":             "Ottawa Ontario",
            "Waterloo / Kitchener":   "Waterloo Ontario",
            "Remote (Canada)":        "Remote Canada",
            "Custom...":              "custom"
        }

        selected_location = st.selectbox(
            "Location",
            options=list(location_options.keys()),
            index=0
        )

        # Custom location input
        if selected_location == "Custom...":
            custom_location = st.text_input(
                "Enter location",
                placeholder="e.g. Vancouver British Columbia"
            )
            location_value = custom_location or "Ontario Canada"
        else:
            location_value = location_options[selected_location]

        # Run button
        if st.button(
            "🔄 Run Pipeline Now",
            use_container_width=True,
            type="primary"
        ):
            # Clean up keywords
            keywords_clean = ", ".join([
                kw.strip()
                for kw in keywords_input.split(",")
                if kw.strip()
            ])
            run_pipeline(keywords_clean, location_value)

        st.caption(
            f"Last refresh: {datetime.now().strftime('%H:%M:%S')}"
        )

        st.divider()

        # ── Results filters ─────────────────────────────────
        st.subheader("📋 Filter Results")

        # Keyword search in results
        keyword_filter = st.text_input(
            "🔍 Search in results",
            placeholder="e.g. CCIE, presales, Cisco...",
            help="Filters results by title, company, or matched skills"
        )

        min_score = st.slider(
            "Minimum score %",
            min_value=0,
            max_value=100,
            value=30,
            step=5
        )

        sources = svc.get_sources()
        selected_sources = st.multiselect(
            "Sources",
            options=sources,
            default=sources
        )

        hide_french = st.toggle(
            "Hide French-required roles",
            value=True
        )

        status_filter = st.selectbox(
            "Application status",
            options=["All", "new", "reviewed", "applied",
                     "interview", "rejected"],
            index=0
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
        kw = keyword_filter.lower()
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

    # ── Render table ────────────────────────────────────────
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
        options=list(job_options.keys())
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("View Details →", use_container_width=True):
            st.session_state.selected_job_id = job_options[selected]
            st.rerun()