"""Streamlit dashboard for the FlowPilot startup growth analytics project."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"

st.set_page_config(page_title="FlowPilot Growth Analytics", page_icon="FP", layout="wide")


@st.cache_data
def load_data() -> dict[str, pd.DataFrame]:
    return {
        "users": pd.read_csv(DATA_DIR / "users.csv", parse_dates=["signup_date", "subscription_date"]),
        "activity": pd.read_csv(DATA_DIR / "activity.csv", parse_dates=["activity_date"]),
        "features": pd.read_csv(DATA_DIR / "feature_usage.csv", parse_dates=["event_date"]),
        "purchases": pd.read_csv(DATA_DIR / "purchases.csv", parse_dates=["purchase_date"]),
        "funnel": pd.read_csv(OUTPUT_DIR / "funnel_metrics.csv"),
        "daily": pd.read_csv(OUTPUT_DIR / "daily_metrics.csv", parse_dates=["activity_date"]),
        "periods": pd.read_csv(OUTPUT_DIR / "weekly_monthly_metrics.csv", parse_dates=["activity_date"]),
        "retention": pd.read_csv(OUTPUT_DIR / "retention_cohorts.csv", parse_dates=["cohort_month"]),
        "segments": pd.read_csv(OUTPUT_DIR / "segment_metrics.csv"),
        "feature_metrics": pd.read_csv(OUTPUT_DIR / "feature_metrics.csv"),
        "revenue": pd.read_csv(OUTPUT_DIR / "revenue_metrics.csv", parse_dates=["purchase_date"]),
    }


data = load_data()
users = data["users"]
activity = data["activity"]
daily = data["daily"]
periods = data["periods"]
funnel = data["funnel"]
retention = data["retention"]
segments = data["segments"]
feature_metrics = data["feature_metrics"]
revenue = data["revenue"]

st.title("FlowPilot Growth Analytics")
st.caption("A Mixpanel-style product analytics case study for a B2B workflow automation startup.")

with st.sidebar:
    st.header("Filters")
    channel_filter = st.multiselect(
        "Acquisition channel",
        sorted(users["acquisition_channel"].unique()),
        default=sorted(users["acquisition_channel"].unique()),
    )
    segment_filter = st.multiselect(
        "Segment",
        sorted(users["segment"].unique()),
        default=sorted(users["segment"].unique()),
    )

filtered_users = users[
    users["acquisition_channel"].isin(channel_filter)
    & users["segment"].isin(segment_filter)
]
filtered_activity = activity[activity["user_id"].isin(filtered_users["user_id"])]

activation_rate = filtered_users["activated"].mean()
paid_conversion = (filtered_users["subscription_status"] == "Paid").mean()
total_revenue = revenue.merge(filtered_users[["user_id"]], on="user_id", how="inner")["revenue"].sum() if "user_id" in revenue.columns else data["purchases"].merge(filtered_users[["user_id"]], on="user_id", how="inner")["amount"].sum()
avg_session = filtered_activity["session_duration_minutes"].mean()
north_star = filtered_activity.groupby(pd.Grouper(key="activity_date", freq="W-MON"))["automations_run"].sum().tail(4).mean()

kpi_cols = st.columns(5)
kpi_cols[0].metric("Users", f"{len(filtered_users):,}")
kpi_cols[1].metric("Activation", f"{activation_rate:.1%}")
kpi_cols[2].metric("Paid Conversion", f"{paid_conversion:.1%}")
kpi_cols[3].metric("Avg Session", f"{avg_session:.1f} min")
kpi_cols[4].metric("Weekly Runs", f"{north_star:,.0f}")

tab_overview, tab_funnel, tab_retention, tab_segments, tab_revenue = st.tabs(
    ["Overview", "Funnel", "Retention", "Segments", "Revenue"]
)

with tab_overview:
    left, right = st.columns([1.4, 1])
    with left:
        fig = px.line(daily, x="activity_date", y="dau", title="Daily Active Users", markers=False)
        fig.update_layout(yaxis_title="DAU", xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        feature_fig = px.bar(
            feature_metrics.sort_values("events", ascending=True),
            x="events",
            y="feature_name",
            title="Feature Usage",
            orientation="h",
        )
        feature_fig.update_layout(xaxis_title="Events", yaxis_title="")
        st.plotly_chart(feature_fig, use_container_width=True)

    monthly = periods.dropna(subset=["mau"])
    fig = px.line(monthly, x="activity_date", y=["wau", "mau"], title="WAU and MAU Trend", markers=True)
    fig.update_layout(xaxis_title="", yaxis_title="Active users", legend_title="")
    st.plotly_chart(fig, use_container_width=True)

with tab_funnel:
    fig = px.funnel(funnel, x="users", y="stage", title="Signup to Subscription Funnel")
    st.plotly_chart(fig, use_container_width=True)
    stage_table = funnel[["stage", "users", "step_conversion", "dropoff_rate"]].copy()
    stage_table["step_conversion"] = stage_table["step_conversion"].map("{:.1%}".format)
    stage_table["dropoff_rate"] = stage_table["dropoff_rate"].map("{:.1%}".format)
    st.dataframe(stage_table, use_container_width=True, hide_index=True)

with tab_retention:
    matrix = retention.pivot(index="cohort_month", columns="months_since_signup", values="retention_rate").fillna(0)
    fig = px.imshow(
        matrix,
        text_auto=".0%",
        aspect="auto",
        color_continuous_scale="Blues",
        title="Monthly Retention Cohorts",
    )
    fig.update_layout(xaxis_title="Months since signup", yaxis_title="Signup cohort")
    st.plotly_chart(fig, use_container_width=True)

with tab_segments:
    fig = px.scatter(
        segments,
        x="activation_rate",
        y="revenue_per_user",
        size="users",
        color="segment",
        hover_data=["acquisition_channel", "paid_conversion_rate", "avg_automations"],
        title="Segment Value vs Activation",
    )
    fig.update_layout(xaxis_tickformat=".0%", yaxis_title="Revenue per user", xaxis_title="Activation rate")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(segments.head(20), use_container_width=True, hide_index=True)

with tab_revenue:
    fig = px.line(revenue, x="purchase_date", y="mrr", title="Rolling 30-Day Revenue")
    fig.update_layout(xaxis_title="", yaxis_title="Revenue")
    st.plotly_chart(fig, use_container_width=True)

    channel_revenue = data["purchases"].merge(users[["user_id", "acquisition_channel", "segment"]], on="user_id", how="left")
    channel_summary = channel_revenue.groupby(["acquisition_channel", "segment"], as_index=False)["amount"].sum()
    fig = px.treemap(
        channel_summary,
        path=["acquisition_channel", "segment"],
        values="amount",
        title="Revenue by Channel and Segment",
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown(
    """
**North Star Metric:** Weekly Automation Runs per Active Account.

This connects directly to the product's promised customer outcome: teams save time when workflows run successfully without manual effort.
"""
)
