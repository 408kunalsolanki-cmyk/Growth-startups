# Startup Growth Analytics: FlowPilot

FlowPilot is a complete product analytics case study for a simulated B2B SaaS startup. The project tracks acquisition, activation, engagement, retention, churn signals, funnel conversion, revenue, feature usage, and a North Star Metric using Python, Pandas, NumPy, Matplotlib, Seaborn, Plotly, and Streamlit.

## Business Problem

The startup is seeing slower growth and needs to understand:

- Why user growth is slowing
- Where users drop off before becoming paying customers
- Which acquisition channels and customer segments are highest quality
- How retention changes by signup cohort
- Which product behavior should become the North Star Metric

## North Star Metric

**Weekly Automation Runs per Active Account**

This metric is stronger than raw DAU or logins because FlowPilot's core value is not opening the app. The product wins when teams create workflows that run automatically and save time every week.

## Project Structure

```text
.
├── dashboard/
│   └── app.py
├── data/
│   ├── activity.csv
│   ├── feature_usage.csv
│   ├── funnel_events.csv
│   ├── purchases.csv
│   └── users.csv
├── outputs/
│   ├── charts/
│   ├── daily_metrics.csv
│   ├── feature_metrics.csv
│   ├── funnel_metrics.csv
│   ├── ltv_by_channel_segment.csv
│   ├── retention_cohorts.csv
│   ├── revenue_metrics.csv
│   ├── segment_metrics.csv
│   └── weekly_monthly_metrics.csv
├── reports/
│   └── business_insights_report.md
├── src/
│   ├── analyze_growth.py
│   └── generate_data.py
├── requirements.txt
└── README.md
```

## Dataset

The synthetic dataset models a realistic SaaS funnel and event stream:

- User IDs and signup dates
- Acquisition channels, segments, region, device, and company size
- Login and daily activity
- Session duration
- Feature usage events
- Subscription plan and purchase history
- Funnel stages from landing page to paid subscription
- Retention events and automation usage

The simulation intentionally includes common startup problems: declining acquisition quality, weak mobile onboarding, paid-channel inefficiency, and retention decay after early activation.

## Metrics Covered

- DAU, WAU, MAU
- DAU/MAU stickiness
- Activation rate
- Paid conversion rate
- Retention cohorts
- Churn risk through inactivity
- Average session time
- Revenue and rolling MRR
- Funnel step conversion and drop-off
- Feature usage
- Segment and acquisition-channel value
- North Star Metric trend

## How to Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Generate the synthetic dataset:

```bash
python src/generate_data.py
```

Run the analysis and create charts/reports:

```bash
python src/analyze_growth.py
```

Launch the dashboard:

```bash
streamlit run dashboard/app.py
```

## Key Findings

The generated report in `reports/business_insights_report.md` summarizes the latest KPI values and recommendations. The main expected findings are:

- The biggest funnel leak happens around onboarding and first workflow creation.
- Retention declines after the first month because not enough users build a weekly automation habit.
- Referral, content, and partnership traffic are higher quality than low-intent paid/social traffic.
- Ops Managers and Founders usually show stronger activation and revenue potential.
- Automation usage is the best behavioral proxy for long-term customer value.

## Recommendations

- Guide new users to create their first workflow with templates and sample data.
- Shift growth spend toward high-activation channels and reduce inefficient paid cohorts.
- Trigger lifecycle campaigns when weekly automation runs fall below target.
- Ask for teammate invites after the first workflow succeeds.
- Build segment-specific onboarding for Founders and Ops Managers.

## Dashboard Preview

Run the Streamlit app to view interactive tabs for:

- Overview KPIs
- Funnel analysis
- Cohort retention
- Segment performance
- Revenue trends

Static chart exports are saved in `outputs/charts/`.
