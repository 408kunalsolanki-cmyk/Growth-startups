"""Analyze FlowPilot startup growth metrics and export charts/reports."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib"))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"
CHART_DIR = OUTPUT_DIR / "charts"
REPORT_DIR = ROOT / "reports"

sns.set_theme(style="whitegrid", palette="Set2")


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    users = pd.read_csv(DATA_DIR / "users.csv", parse_dates=["signup_date", "subscription_date"])
    activity = pd.read_csv(DATA_DIR / "activity.csv", parse_dates=["activity_date"])
    feature_usage = pd.read_csv(DATA_DIR / "feature_usage.csv", parse_dates=["event_date"])
    purchases = pd.read_csv(DATA_DIR / "purchases.csv", parse_dates=["purchase_date"])
    funnel_events = pd.read_csv(DATA_DIR / "funnel_events.csv", parse_dates=["event_date"])
    return users, activity, feature_usage, purchases, funnel_events


def active_user_metrics(activity: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    daily = activity.groupby("activity_date").agg(
        dau=("user_id", "nunique"),
        sessions=("sessions", "sum"),
        avg_session_minutes=("session_duration_minutes", "mean"),
        workflows_created=("workflows_created", "sum"),
        automations_run=("automations_run", "sum"),
    )
    daily = daily.asfreq("D", fill_value=0).reset_index()

    weekly = activity.set_index("activity_date").groupby(pd.Grouper(freq="W-MON"))["user_id"].nunique().reset_index(name="wau")
    monthly = activity.set_index("activity_date").groupby(pd.Grouper(freq="MS"))["user_id"].nunique().reset_index(name="mau")
    monthly["stickiness_dau_mau"] = daily.set_index("activity_date")["dau"].resample("MS").mean().values / monthly["mau"].replace(0, np.nan)
    monthly["stickiness_dau_mau"] = monthly["stickiness_dau_mau"].fillna(0)

    periods = weekly.merge(monthly, left_on="activity_date", right_on="activity_date", how="outer").sort_values("activity_date")
    return daily, periods


def funnel_metrics(funnel_events: pd.DataFrame, users: pd.DataFrame) -> pd.DataFrame:
    stage_order = [
        "Visit Landing Page",
        "Sign Up",
        "Verify Email",
        "Complete Onboarding",
        "Create First Workflow",
        "Invite Teammate",
        "Start Trial",
        "Subscribe",
    ]
    counts = funnel_events.groupby("stage")["user_id"].nunique().reindex(stage_order).fillna(0).astype(int)
    funnel = counts.reset_index(name="users")
    funnel["stage_order"] = range(1, len(funnel) + 1)
    funnel["conversion_from_signup"] = funnel["users"] / len(users)
    funnel["step_conversion"] = funnel["users"] / funnel["users"].shift(1)
    funnel.loc[0, "step_conversion"] = 1.0
    funnel["dropoff_rate"] = 1 - funnel["step_conversion"]
    return funnel


def retention_cohorts(users: pd.DataFrame, activity: pd.DataFrame) -> pd.DataFrame:
    user_cohorts = users[["user_id", "signup_date"]].copy()
    user_cohorts["cohort_month"] = user_cohorts["signup_date"].dt.to_period("M").dt.to_timestamp()
    activity_months = activity[["user_id", "activity_date"]].copy()
    activity_months["activity_month"] = activity_months["activity_date"].dt.to_period("M").dt.to_timestamp()

    cohort_activity = user_cohorts.merge(activity_months, on="user_id", how="inner")
    cohort_activity["months_since_signup"] = (
        (cohort_activity["activity_month"].dt.year - cohort_activity["cohort_month"].dt.year) * 12
        + cohort_activity["activity_month"].dt.month
        - cohort_activity["cohort_month"].dt.month
    )
    cohort_counts = (
        cohort_activity.groupby(["cohort_month", "months_since_signup"])["user_id"]
        .nunique()
        .reset_index(name="active_users")
    )
    cohort_sizes = user_cohorts.groupby("cohort_month")["user_id"].nunique().reset_index(name="cohort_size")
    retention = cohort_counts.merge(cohort_sizes, on="cohort_month")
    retention["retention_rate"] = retention["active_users"] / retention["cohort_size"]
    return retention


def revenue_metrics(users: pd.DataFrame, purchases: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    revenue = purchases.groupby("purchase_date").agg(revenue=("amount", "sum"), paying_users=("user_id", "nunique")).reset_index()
    revenue["mrr"] = revenue.set_index("purchase_date")["revenue"].rolling("30D").sum().values

    paid_users = users[users["subscription_status"] == "Paid"].copy()
    channel_rev = purchases.merge(users[["user_id", "acquisition_channel", "segment", "acquisition_cost"]], on="user_id", how="left")
    ltv = channel_rev.groupby(["acquisition_channel", "segment"]).agg(
        users=("user_id", "nunique"),
        revenue=("amount", "sum"),
        avg_cac=("acquisition_cost", "mean"),
    ).reset_index()
    ltv["arppu"] = ltv["revenue"] / ltv["users"].replace(0, np.nan)
    ltv["ltv_cac_ratio"] = ltv["arppu"] / ltv["avg_cac"].replace(0, np.nan)
    ltv = ltv.sort_values("revenue", ascending=False)

    paid_users.to_csv(OUTPUT_DIR / "paid_users_snapshot.csv", index=False)
    return revenue, ltv


def segment_metrics(users: pd.DataFrame, activity: pd.DataFrame, purchases: pd.DataFrame) -> pd.DataFrame:
    activity_by_user = activity.groupby("user_id").agg(
        active_days=("activity_date", "nunique"),
        total_sessions=("sessions", "sum"),
        avg_session_minutes=("session_duration_minutes", "mean"),
        workflows_created=("workflows_created", "sum"),
        automations_run=("automations_run", "sum"),
    ).reset_index()
    revenue_by_user = purchases.groupby("user_id")["amount"].sum().reset_index(name="revenue")
    enriched = users.merge(activity_by_user, on="user_id", how="left").merge(revenue_by_user, on="user_id", how="left")
    enriched = enriched.fillna({"active_days": 0, "total_sessions": 0, "avg_session_minutes": 0, "workflows_created": 0, "automations_run": 0, "revenue": 0})

    segment = enriched.groupby(["segment", "acquisition_channel"]).agg(
        users=("user_id", "nunique"),
        activation_rate=("activated", "mean"),
        paid_conversion_rate=("subscription_status", lambda s: (s == "Paid").mean()),
        avg_active_days=("active_days", "mean"),
        avg_automations=("automations_run", "mean"),
        revenue=("revenue", "sum"),
        avg_cac=("acquisition_cost", "mean"),
    ).reset_index()
    segment["revenue_per_user"] = segment["revenue"] / segment["users"]
    return segment.sort_values("revenue", ascending=False)


def feature_metrics(feature_usage: pd.DataFrame, users: pd.DataFrame) -> pd.DataFrame:
    feature = feature_usage.merge(users[["user_id", "segment", "subscription_status"]], on="user_id", how="left")
    summary = feature.groupby("feature_name").agg(
        users=("user_id", "nunique"),
        events=("event_count", "sum"),
        paid_user_share=("subscription_status", lambda s: (s == "Paid").mean()),
    ).reset_index()
    return summary.sort_values("events", ascending=False)


def save_charts(
    daily: pd.DataFrame,
    periods: pd.DataFrame,
    funnel: pd.DataFrame,
    retention: pd.DataFrame,
    revenue: pd.DataFrame,
    features: pd.DataFrame,
    segment: pd.DataFrame,
) -> None:
    CHART_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(11, 5))
    sns.lineplot(data=daily, x="activity_date", y="dau", ax=ax, color="#2563eb")
    ax.set_title("Daily Active Users")
    ax.set_xlabel("")
    ax.set_ylabel("DAU")
    fig.tight_layout()
    fig.savefig(CHART_DIR / "dau_trend.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 5))
    monthly = periods.dropna(subset=["mau"])
    sns.lineplot(data=monthly, x="activity_date", y="mau", marker="o", ax=ax, color="#059669")
    ax.set_title("Monthly Active Users")
    ax.set_xlabel("")
    ax.set_ylabel("MAU")
    fig.tight_layout()
    fig.savefig(CHART_DIR / "mau_trend.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 5))
    sns.barplot(data=funnel, x="stage", y="users", ax=ax, color="#7c3aed")
    ax.set_title("Funnel Users by Stage")
    ax.set_xlabel("")
    ax.set_ylabel("Users")
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    fig.savefig(CHART_DIR / "funnel_dropoff.png", dpi=160)
    plt.close(fig)

    matrix = retention.pivot(index="cohort_month", columns="months_since_signup", values="retention_rate").fillna(0)
    fig, ax = plt.subplots(figsize=(11, 6))
    sns.heatmap(matrix, annot=True, fmt=".0%", cmap="YlGnBu", cbar=False, ax=ax)
    ax.set_title("Monthly Retention Cohorts")
    ax.set_xlabel("Months Since Signup")
    ax.set_ylabel("Signup Cohort")
    fig.tight_layout()
    fig.savefig(CHART_DIR / "retention_cohort_heatmap.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 5))
    sns.lineplot(data=revenue, x="purchase_date", y="mrr", ax=ax, color="#dc2626")
    ax.set_title("Rolling 30-Day Revenue")
    ax.set_xlabel("")
    ax.set_ylabel("Revenue")
    fig.tight_layout()
    fig.savefig(CHART_DIR / "mrr_trend.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=features.head(8), y="feature_name", x="events", ax=ax, color="#0891b2")
    ax.set_title("Feature Usage")
    ax.set_xlabel("Events")
    ax.set_ylabel("")
    fig.tight_layout()
    fig.savefig(CHART_DIR / "feature_usage.png", dpi=160)
    plt.close(fig)

    top_segment = segment.head(12)
    fig, ax = plt.subplots(figsize=(11, 6))
    sns.scatterplot(
        data=top_segment,
        x="activation_rate",
        y="revenue_per_user",
        size="users",
        hue="segment",
        sizes=(80, 800),
        ax=ax,
    )
    ax.set_title("Segment Value vs Activation")
    ax.set_xlabel("Activation Rate")
    ax.set_ylabel("Revenue per User")
    fig.tight_layout()
    fig.savefig(CHART_DIR / "segment_value.png", dpi=160)
    plt.close(fig)


def write_report(
    users: pd.DataFrame,
    daily: pd.DataFrame,
    periods: pd.DataFrame,
    funnel: pd.DataFrame,
    retention: pd.DataFrame,
    revenue: pd.DataFrame,
    features: pd.DataFrame,
    segment: pd.DataFrame,
) -> None:
    REPORT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    latest_month = periods.dropna(subset=["mau"]).sort_values("activity_date").tail(1).iloc[0]
    latest_dau = int(daily.sort_values("activity_date").tail(7)["dau"].mean())
    activation_rate = users["activated"].mean()
    paid_conversion = (users["subscription_status"] == "Paid").mean()
    avg_session = daily["avg_session_minutes"].replace(0, np.nan).mean()
    total_revenue = revenue["revenue"].sum()
    worst_funnel = funnel.iloc[1:].sort_values("dropoff_rate", ascending=False).iloc[0]
    month_1_retention = retention[retention["months_since_signup"] == 1]["retention_rate"].mean()
    month_3_retention = retention[retention["months_since_signup"] == 3]["retention_rate"].mean()
    top_feature = features.iloc[0]
    top_segment = segment.iloc[0]
    weak_channel = (
        users.groupby("acquisition_channel")
        .agg(activation_rate=("activated", "mean"), paid_conversion=("subscription_status", lambda s: (s == "Paid").mean()), users=("user_id", "count"))
        .query("users > 200")
        .sort_values(["activation_rate", "paid_conversion"])
        .head(1)
        .reset_index()
        .iloc[0]
    )

    north_star = "Weekly Automation Runs per Active Account"
    report = f"""# FlowPilot Growth Analytics Insights Report

## Executive Summary

FlowPilot generated {len(users):,} simulated signups and ${total_revenue:,.0f} in subscription revenue across 2025. The product has meaningful demand, but growth slows because paid acquisition quality is weaker than referral/content traffic and too many users fail to reach the first value moment: creating an automated workflow.

Recommended North Star Metric: **{north_star}**. This metric captures repeated customer value better than raw logins because the product promise is workflow automation, not passive visits.

## KPI Snapshot

| Metric | Value |
|---|---:|
| Latest 7-day average DAU | {latest_dau:,} |
| Latest MAU | {int(latest_month['mau']):,} |
| DAU/MAU stickiness | {latest_month['stickiness_dau_mau']:.1%} |
| Activation rate | {activation_rate:.1%} |
| Paid conversion rate | {paid_conversion:.1%} |
| Average session time | {avg_session:.1f} minutes |
| Month 1 retention | {month_1_retention:.1%} |
| Month 3 retention | {month_3_retention:.1%} |

## Main Findings

1. **Largest funnel leak:** {worst_funnel['stage']} has a {worst_funnel['dropoff_rate']:.1%} step drop-off. Users are interested enough to sign up, but too many do not reach a collaborative or monetizable workflow moment.
2. **Retention declines after onboarding:** average month 1 retention is {month_1_retention:.1%}, falling to {month_3_retention:.1%} by month 3. This suggests the product creates initial curiosity but does not consistently form a weekly operating habit.
3. **Weakest acquisition channel:** {weak_channel['acquisition_channel']} has only {weak_channel['activation_rate']:.1%} activation and {weak_channel['paid_conversion']:.1%} paid conversion among scaled channels.
4. **Highest-value segment:** {top_segment['segment']} from {top_segment['acquisition_channel']} produces ${top_segment['revenue_per_user']:.2f} revenue per user with {top_segment['activation_rate']:.1%} activation.
5. **Most-used feature:** {top_feature['feature_name']} drives {int(top_feature['events']):,} events and should be connected more clearly to activation and team collaboration.

## Actionable Recommendations

- Move "Create First Workflow" earlier in onboarding with prefilled templates, sample data, and a guided checklist.
- Reduce spend on low-activation paid/social cohorts until landing pages and audience targeting improve.
- Build lifecycle nudges around the North Star Metric: trigger emails or in-app prompts when active accounts run fewer than three automations in a week.
- Promote collaboration after activation, not before it. Invite prompts should appear once the first workflow succeeds.
- Create segment-specific onboarding for Ops Managers and Founders, the strongest commercial personas in the simulation.
- Add dashboards for activation by channel, retention by signup cohort, and weekly automation runs by segment.

## Files Produced

- `data/users.csv`
- `data/activity.csv`
- `data/feature_usage.csv`
- `data/purchases.csv`
- `data/funnel_events.csv`
- `outputs/charts/`
- `dashboard/app.py`
"""
    (REPORT_DIR / "business_insights_report.md").write_text(report, encoding="utf-8")

    daily.to_csv(OUTPUT_DIR / "daily_metrics.csv", index=False)
    periods.to_csv(OUTPUT_DIR / "weekly_monthly_metrics.csv", index=False)
    funnel.to_csv(OUTPUT_DIR / "funnel_metrics.csv", index=False)
    retention.to_csv(OUTPUT_DIR / "retention_cohorts.csv", index=False)
    revenue.to_csv(OUTPUT_DIR / "revenue_metrics.csv", index=False)
    features.to_csv(OUTPUT_DIR / "feature_metrics.csv", index=False)
    segment.to_csv(OUTPUT_DIR / "segment_metrics.csv", index=False)


def main() -> None:
    users, activity, feature_usage, purchases, funnel_events = load_data()
    OUTPUT_DIR.mkdir(exist_ok=True)
    CHART_DIR.mkdir(parents=True, exist_ok=True)

    daily, periods = active_user_metrics(activity)
    funnel = funnel_metrics(funnel_events, users)
    retention = retention_cohorts(users, activity)
    revenue, ltv = revenue_metrics(users, purchases)
    segment = segment_metrics(users, activity, purchases)
    features = feature_metrics(feature_usage, users)

    ltv.to_csv(OUTPUT_DIR / "ltv_by_channel_segment.csv", index=False)
    save_charts(daily, periods, funnel, retention, revenue, features, segment)
    write_report(users, daily, periods, funnel, retention, revenue, features, segment)

    print("Growth analysis complete.")
    print(f"Charts: {CHART_DIR}")
    print(f"Report: {REPORT_DIR / 'business_insights_report.md'}")


if __name__ == "__main__":
    main()
