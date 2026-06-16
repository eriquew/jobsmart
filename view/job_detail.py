import streamlit as st
import plotly.graph_objects as go
from mysql.connector import Error

from model.database.db_connection import get_db
from controller.job_service import JobService

svc = JobService()


def get_job_by_id(job_id: int) -> dict:
    """Fetches full job record including scores from job_scores."""
    sql = """
        SELECT
            j.*,
            COALESCE(s.score_total, 0)          AS score_total,
            COALESCE(s.score_technical, 0)      AS score_technical,
            COALESCE(s.score_seniority, 0)      AS score_seniority,
            COALESCE(s.score_industry, 0)       AS score_industry,
            COALESCE(s.score_location, 0)       AS score_location,
            COALESCE(s.flag_french_required, 0) AS flag_french_required,
            COALESCE(s.extracted_skills, '')    AS extracted_skills,
            COALESCE(t.status, 'new')           AS status,
            t.notes
        FROM jobs j
        LEFT JOIN job_scores s
            ON j.id = s.job_id AND s.user_id = %s
        LEFT JOIN job_tracking t
            ON j.id = t.job_id AND t.user_id = %s
        WHERE j.id = %s
    """
    try:
        conn   = get_db()
        cursor = conn.cursor(dictionary=True, buffered=True)
        cursor.execute(sql, (
            st.session_state.get("user_id", 1),
            st.session_state.get("user_id", 1),
            job_id
        ))
        result = cursor.fetchone()
        cursor.close()
        return result or {}
    except Error as e:
        return {}


def score_chart(job: dict):
    """Renders score breakdown bar chart."""
    dimensions = ["Technical", "Seniority", "Industry", "Location"]
    scores     = [
        job.get("score_technical", 0),
        job.get("score_seniority", 0),
        job.get("score_industry",  0),
        job.get("score_location",  0)
    ]
    colors = [
        "#2E75B6" if s >= 75 else
        "#F4B942" if s >= 50 else
        "#E07B39" if s >= 25 else "#D94F3D"
        for s in scores
    ]

    fig = go.Figure(go.Bar(
        x=dimensions,
        y=scores,
        marker_color=colors,
        text=[f"{s}%" for s in scores],
        textposition="auto"
    ))
    fig.update_layout(
        yaxis_range=[0, 100],
        height=250,
        margin=dict(t=20, b=20, l=20, r=20),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig, use_container_width=True)


def show_job_detail(job_id: int):
    """Renders full job detail page."""

    if st.button("← Back to Dashboard"):
        st.session_state.selected_job_id = None
        st.rerun()

    job = get_job_by_id(job_id)
    if not job:
        st.error("Job not found.")
        return

    # ── Header ──────────────────────────────────────────────
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(job.get("title", ""))
        st.subheader(f"{job.get('company', '')} · {job.get('location', '')}")
    with col2:
        score = job.get("score_total", 0)
        color = "green" if score >= 75 else "orange" if score >= 50 else "red"
        st.markdown(
            f"<h1 style='color:{color};text-align:center'>{score}%</h1>"
            f"<p style='text-align:center'>Fitness Score</p>",
            unsafe_allow_html=True
        )

    st.divider()

    # ── Score breakdown ─────────────────────────────────────
    st.subheader("Score Breakdown")
    score_chart(job)

    # ── Skills matched ──────────────────────────────────────
    if job.get("extracted_skills"):
        st.subheader("Skills Matched")
        skills = job["extracted_skills"].split(", ")
        cols   = st.columns(min(len(skills), 6))
        for i, skill in enumerate(skills):
            cols[i % 6].success(skill)

    # ── Flags ───────────────────────────────────────────────
    if job.get("flag_french_required"):
        st.warning("🇫🇷 This role requires French language proficiency")

    st.divider()

    # ── Job metadata ─────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    col1.metric("Source", job.get("source", "").upper())
    col2.metric("Posted", str(job.get("date_posted", "N/A")))

    salary = "Not specified"
    if job.get("salary_min") and job.get("salary_max"):
        salary = f"${job['salary_min']:,} – ${job['salary_max']:,} {job.get('currency','CAD')}"
    col3.metric("Salary", salary)

    st.divider()

    # ── Actions ─────────────────────────────────────────────
    st.subheader("Actions")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("✅ Mark Applied", use_container_width=True):
            svc.update_status(job_id, "applied")
            st.success("Marked as Applied")
            st.rerun()
    with col2:
        if st.button("👁 Mark Reviewed", use_container_width=True):
            svc.update_status(job_id, "reviewed")
            st.success("Marked as Reviewed")
            st.rerun()
    with col3:
        if st.button("❌ Reject", use_container_width=True):
            svc.update_status(job_id, "rejected")
            st.success("Marked as Rejected")
            st.rerun()
    with col4:
        url = job.get("url", "")
        if url and str(url) != "None" and str(url).startswith("http"):
            st.link_button(
                "🔗 Apply Now",
                str(url),
                use_container_width=True
            )
        else:
            st.button(
                "🔗 URL not available",
                disabled=True,
                use_container_width=True
            )
    st.divider()

    # ── Full description ─────────────────────────────────────
    st.subheader("Full Job Description")
    with st.expander("Show description", expanded=True):
        st.write(job.get("description", "No description available."))