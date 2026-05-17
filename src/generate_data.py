"""Generate a realistic synthetic SaaS product analytics dataset.

The simulated product is "FlowPilot", a B2B workflow automation startup.
The data intentionally includes slowing acquisition, onboarding friction, and
retention decay so the downstream analysis has real business texture.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


RNG = np.random.default_rng(42)
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
START_DATE = pd.Timestamp("2025-01-01")
END_DATE = pd.Timestamp("2025-12-31")

CHANNELS = {
    "Organic Search": {"weight": 0.30, "quality": 1.05, "trial": 0.17},
    "Paid Search": {"weight": 0.24, "quality": 0.82, "trial": 0.13},
    "Referral": {"weight": 0.17, "quality": 1.32, "trial": 0.24},
    "Social": {"weight": 0.14, "quality": 0.74, "trial": 0.10},
    "Content": {"weight": 0.10, "quality": 1.12, "trial": 0.18},
    "Partnership": {"weight": 0.05, "quality": 1.22, "trial": 0.21},
}

SEGMENTS = {
    "Founder": {"weight": 0.28, "quality": 1.14},
    "Ops Manager": {"weight": 0.27, "quality": 1.24},
    "Sales Team": {"weight": 0.20, "quality": 0.96},
    "Marketing Team": {"weight": 0.16, "quality": 0.88},
    "Student / Hobby": {"weight": 0.09, "quality": 0.52},
}

FEATURES = [
    "Dashboard Viewed",
    "Template Used",
    "Workflow Created",
    "Integration Connected",
    "Report Exported",
    "Team Invite Sent",
    "Automation Run",
    "AI Recommendation Used",
]

PLANS = {
    "Free": 0,
    "Starter": 19,
    "Growth": 59,
    "Scale": 149,
}

FUNNEL_STAGES = [
    "Visit Landing Page",
    "Sign Up",
    "Verify Email",
    "Complete Onboarding",
    "Create First Workflow",
    "Invite Teammate",
    "Start Trial",
    "Subscribe",
]


def sigmoid(x: float) -> float:
    return 1 / (1 + np.exp(-x))


def choose_from_config(config: dict[str, dict[str, float]], key: str = "weight") -> str:
    names = list(config)
    weights = np.array([config[name][key] for name in names], dtype=float)
    weights = weights / weights.sum()
    return str(RNG.choice(names, p=weights))


def create_users(n_users: int = 8500) -> pd.DataFrame:
    """Create user-level acquisition, segment, subscription, and value fields."""
    days = pd.date_range(START_DATE, END_DATE, freq="D")

    # More signups arrive in the first half of the year; acquisition efficiency
    # drops after summer, reflecting a common startup growth slowdown.
    day_index = np.arange(len(days))
    growth_curve = np.exp(-day_index / 270)
    seasonality = 1 + 0.18 * np.sin(2 * np.pi * day_index / 365)
    probs = growth_curve * seasonality
    probs = probs / probs.sum()
    signup_dates = RNG.choice(days, size=n_users, p=probs)

    rows = []
    for user_id, signup_date in enumerate(pd.to_datetime(signup_dates), start=100001):
        channel = choose_from_config(CHANNELS)
        segment = choose_from_config(SEGMENTS)
        channel_quality = CHANNELS[channel]["quality"]
        segment_quality = SEGMENTS[segment]["quality"]
        quality_score = float(np.clip(RNG.normal(channel_quality * segment_quality, 0.22), 0.25, 2.15))
        device = str(RNG.choice(["Desktop", "Mobile", "Tablet"], p=[0.68, 0.26, 0.06]))
        region = str(RNG.choice(["North America", "Europe", "APAC", "LATAM", "MEA"], p=[0.45, 0.25, 0.18, 0.08, 0.04]))
        company_size = str(RNG.choice(["1-10", "11-50", "51-200", "201-1000", "1000+"], p=[0.39, 0.30, 0.18, 0.09, 0.04]))
        acquisition_cost = round(float(RNG.gamma(2.4, 8.5) / quality_score), 2)

        rows.append(
            {
                "user_id": f"U{user_id}",
                "signup_date": signup_date.date(),
                "acquisition_channel": channel,
                "segment": segment,
                "device": device,
                "region": region,
                "company_size": company_size,
                "quality_score": round(quality_score, 3),
                "acquisition_cost": acquisition_cost,
            }
        )

    users = pd.DataFrame(rows).sort_values("signup_date").reset_index(drop=True)
    return users


def simulate_funnel(users: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Simulate funnel progression and return event-level funnel records."""
    stage_records = []
    user_updates = []

    for row in users.itertuples(index=False):
        quality = row.quality_score
        mobile_penalty = -0.23 if row.device == "Mobile" else 0
        social_penalty = -0.18 if row.acquisition_channel == "Social" else 0

        probabilities = {
            "Visit Landing Page": 1.0,
            "Sign Up": 1.0,
            "Verify Email": sigmoid(1.65 * quality + mobile_penalty - 0.28),
            "Complete Onboarding": sigmoid(1.32 * quality + mobile_penalty + social_penalty - 0.58),
            "Create First Workflow": sigmoid(1.42 * quality + mobile_penalty - 0.72),
            "Invite Teammate": sigmoid(1.12 * quality - 1.02),
            "Start Trial": sigmoid(1.26 * quality + CHANNELS[row.acquisition_channel]["trial"] * 3 - 1.35),
            "Subscribe": sigmoid(1.12 * quality - 1.48),
        }

        stage_dates = {}
        reached_all = True
        for stage_index, stage in enumerate(FUNNEL_STAGES):
            if reached_all and RNG.random() <= probabilities[stage]:
                stage_date = pd.Timestamp(row.signup_date) + pd.Timedelta(days=int(RNG.integers(0, min(12, stage_index + 2))))
                stage_dates[stage] = stage_date
                stage_records.append({"user_id": row.user_id, "stage": stage, "event_date": stage_date.date()})
            else:
                reached_all = False

        subscribed = "Subscribe" in stage_dates
        trial_started = "Start Trial" in stage_dates
        activated = "Create First Workflow" in stage_dates

        if subscribed:
            plan = str(RNG.choice(["Starter", "Growth", "Scale"], p=[0.52, 0.36, 0.12]))
            status = "Paid"
            subscription_date = stage_dates["Subscribe"].date()
        elif trial_started:
            plan = "Free"
            status = "Trial"
            subscription_date = pd.NaT
        else:
            plan = "Free"
            status = "Free"
            subscription_date = pd.NaT

        user_updates.append(
            {
                "user_id": row.user_id,
                "activated": activated,
                "trial_started": trial_started,
                "subscription_status": status,
                "plan": plan,
                "subscription_date": subscription_date,
                "monthly_price": PLANS[plan],
            }
        )

    funnel_events = pd.DataFrame(stage_records)
    user_updates_df = pd.DataFrame(user_updates)
    users = users.merge(user_updates_df, on="user_id", how="left")
    return users, funnel_events


def simulate_activity(users: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Create daily user activity, feature events, and purchases."""
    activity_records = []
    feature_records = []
    purchase_records = []

    for row in users.itertuples(index=False):
        signup = pd.Timestamp(row.signup_date)
        max_days = max(1, (END_DATE - signup).days + 1)
        days_since_signup = np.arange(max_days)

        plan_boost = {"Free": 0.65, "Starter": 1.0, "Growth": 1.22, "Scale": 1.42}[row.plan]
        activation_boost = 1.42 if row.activated else 0.62
        base_propensity = np.clip(0.10 * row.quality_score * plan_boost * activation_boost, 0.01, 0.68)
        decay = np.exp(-days_since_signup / (95 + 40 * row.quality_score))
        weekday_effect = np.array([(signup + pd.Timedelta(days=int(i))).weekday() < 5 for i in days_since_signup])
        weekday_multiplier = np.where(weekday_effect, 1.15, 0.65)
        activity_probability = np.clip(base_propensity * decay * weekday_multiplier + 0.012, 0.003, 0.76)

        active_mask = RNG.random(max_days) < activity_probability
        active_days = days_since_signup[active_mask]

        churn_day = None
        if len(active_days) > 0:
            last_active_day = int(active_days[-1])
            if END_DATE - (signup + pd.Timedelta(days=last_active_day)) > pd.Timedelta(days=30):
                churn_day = last_active_day + 31

        for day in active_days:
            event_date = signup + pd.Timedelta(days=int(day))
            sessions = int(np.clip(RNG.poisson(1.25 + row.quality_score / 2), 1, 6))
            avg_session = float(np.clip(RNG.normal(13.5 * plan_boost * row.quality_score, 7.0), 1.5, 85))
            total_minutes = round(sessions * avg_session, 2)
            workflows = int(RNG.poisson(max(0.03, 0.12 * row.quality_score * activation_boost * plan_boost)))
            automations = int(RNG.poisson(max(0.02, workflows * RNG.uniform(1.2, 3.5))))

            activity_records.append(
                {
                    "user_id": row.user_id,
                    "activity_date": event_date.date(),
                    "sessions": sessions,
                    "session_duration_minutes": total_minutes,
                    "workflows_created": workflows,
                    "automations_run": automations,
                    "retention_event": bool(day in [1, 7, 14, 30, 60, 90] or automations > 0),
                }
            )

            feature_weights = np.array([0.23, 0.15, 0.14, 0.11, 0.10, 0.08, 0.14, 0.05])
            if row.plan in ["Growth", "Scale"]:
                feature_weights += np.array([0.00, 0.00, 0.02, 0.03, 0.03, 0.02, 0.04, 0.03])
            feature_weights = feature_weights / feature_weights.sum()
            feature_count = int(np.clip(RNG.poisson(2.2 * plan_boost), 1, 9))
            chosen_features = RNG.choice(FEATURES, size=feature_count, replace=True, p=feature_weights)
            for feature in chosen_features:
                feature_records.append(
                    {
                        "user_id": row.user_id,
                        "event_date": event_date.date(),
                        "feature_name": str(feature),
                        "event_count": int(RNG.integers(1, 5)),
                    }
                )

        if row.plan != "Free" and pd.notna(row.subscription_date):
            subscription_date = pd.Timestamp(row.subscription_date)
            billing_dates = pd.date_range(subscription_date, END_DATE, freq="30D")
            churn_risk = 0.035 if row.plan == "Scale" else 0.052 if row.plan == "Growth" else 0.072
            retained = True
            for billing_date in billing_dates:
                if retained and RNG.random() < churn_risk:
                    retained = False
                if retained:
                    purchase_records.append(
                        {
                            "user_id": row.user_id,
                            "purchase_date": billing_date.date(),
                            "plan": row.plan,
                            "amount": row.monthly_price,
                        }
                    )

    activity = pd.DataFrame(activity_records)
    feature_usage = pd.DataFrame(feature_records)
    purchases = pd.DataFrame(purchase_records)
    return activity, feature_usage, purchases


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    users = create_users()
    users, funnel_events = simulate_funnel(users)
    activity, feature_usage, purchases = simulate_activity(users)

    users.to_csv(DATA_DIR / "users.csv", index=False)
    activity.to_csv(DATA_DIR / "activity.csv", index=False)
    feature_usage.to_csv(DATA_DIR / "feature_usage.csv", index=False)
    purchases.to_csv(DATA_DIR / "purchases.csv", index=False)
    funnel_events.to_csv(DATA_DIR / "funnel_events.csv", index=False)

    print("Synthetic startup analytics dataset created:")
    print(f"- users: {len(users):,}")
    print(f"- activity rows: {len(activity):,}")
    print(f"- feature events: {len(feature_usage):,}")
    print(f"- purchase rows: {len(purchases):,}")
    print(f"- funnel events: {len(funnel_events):,}")


if __name__ == "__main__":
    main()
