# FlowPilot Growth Analytics Insights Report

## Executive Summary

FlowPilot generated 8,500 simulated signups and $178,476 in subscription revenue across 2025. The product has meaningful demand, but growth slows because paid acquisition quality is weaker than referral/content traffic and too many users fail to reach the first value moment: creating an automated workflow.

Recommended North Star Metric: **Weekly Automation Runs per Active Account**. This metric captures repeated customer value better than raw logins because the product promise is workflow automation, not passive visits.

## KPI Snapshot

| Metric | Value |
|---|---:|
| Latest 7-day average DAU | 266 |
| Latest MAU | 4,746 |
| DAU/MAU stickiness | 5.7% |
| Activation rate | 36.0% |
| Paid conversion rate | 7.0% |
| Average session time | 26.1 minutes |
| Month 1 retention | 80.5% |
| Month 3 retention | 71.9% |

## Main Findings

1. **Largest funnel leak:** Subscribe has a 50.5% step drop-off. Users are interested enough to sign up, but too many do not reach a collaborative or monetizable workflow moment.
2. **Retention declines after onboarding:** average month 1 retention is 80.5%, falling to 71.9% by month 3. This suggests the product creates initial curiosity but does not consistently form a weekly operating habit.
3. **Weakest acquisition channel:** Social has only 23.9% activation and 2.1% paid conversion among scaled channels.
4. **Highest-value segment:** Ops Manager from Referral produces $63.64 revenue per user with 59.0% activation.
5. **Most-used feature:** Dashboard Viewed drives 92,565 events and should be connected more clearly to activation and team collaboration.

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
