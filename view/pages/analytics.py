import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from controller.job_service import JobService

svc = JobService()


def show_analytics():
    """Analytics page — market intelligence."""

    st.title("📊 Market Analytics")
    st.caption("Insights from your job search pipeline")
    st.divider()

    data = svc.get_analytics()

    if not data:
        st.warning("No data available. Run the pipeline first.")
        return

    # ── Row 1: Jobs by source + Score distribution ──────────
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Jobs by Source")
        if data.get("by_source"):
            df_source = pd.DataFrame(data["by_source"])
            fig = px.pie(
                df_source,
                values="count",
                names="source",
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig.update_layout(
                height=300,
                margin=dict(t=20, b=20, l=20, r=20)
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Score Distribution")
        if data.get("score_dist"):
            df_score = pd.DataFrame(data["score_dist"])
            colors   = {
                "High (75-100)":   "#2E75B6",
                "Medium (50-74)":  "#F4B942",
                "Low (25-49)":     "#E07B39",
                "Very Low (0-24)": "#D94F3D"
            }
            df_score["color"] = df_score["bucket"].map(colors)
            fig = px.bar(
                df_score,
                x="bucket",
                y="count",
                color="bucket",
                color_discrete_map=colors,
                text="count"
            )
            fig.update_layout(
                height=300,
                showlegend=False,
                margin=dict(t=20, b=20, l=20, r=20),
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── Row 2: Top locations ─────────────────────────────────
    st.subheader("Jobs by Location")
    if data.get("by_location"):
        df_loc = pd.DataFrame(data["by_location"])
        fig = px.bar(
            df_loc,
            x="count",
            y="location",
            orientation="h",
            color="count",
            color_continuous_scale="Blues",
            text="count"
        )
        fig.update_layout(
            height=400,
            margin=dict(t=20, b=20, l=20, r=20),
            plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(autorange="reversed")
        )
        st.plotly_chart(fig, use_container_width=True)