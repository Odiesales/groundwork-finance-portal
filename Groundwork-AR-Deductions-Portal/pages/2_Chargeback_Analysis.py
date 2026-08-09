from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.data import load_ar_history
from utils.ui import YELLOW, chart_layout, footer, format_money, kpi_row, page_header, section


def prep_history():
    df = load_ar_history().copy()
    if df.empty:
        return df
    df["Snapshot Date"] = pd.to_datetime(df.get("Snapshot Date"), errors="coerce")
    df["Open Balance"] = pd.to_numeric(df.get("Open Balance", 0), errors="coerce").fillna(0)
    df["Age"] = pd.to_numeric(df.get("Age", 0), errors="coerce").fillna(0)
    df["Transaction Type"] = df.get("Transaction Type", "").fillna("").astype(str)
    df["Deduction Type"] = df.get("Deduction Type", "").fillna("").astype(str)
    df = df[df["Transaction Type"].str.strip().str.casefold().eq("chargeback")].copy()
    return df


def latest_by_month(df):
    if df.empty:
        return df
    work = df.dropna(subset=["Snapshot Date"]).copy()
    work["Month"] = work["Snapshot Date"].dt.to_period("M")
    latest = work.groupby("Month")["Snapshot Date"].transform("max")
    return work[work["Snapshot Date"].eq(latest)].copy()


history = prep_history()
page_header("Chargeback Analysis", "Executive view of open deduction exposure, mix, aging, and monthly movement.")
if history.empty:
    st.info("No chargebacks are available in saved AR snapshots.")
    footer(); st.stop()

as_of = history["Snapshot Date"].max()
current = history[history["Snapshot Date"].dt.normalize().eq(pd.Timestamp(as_of).normalize())].copy()

for col, default in {"Reporting Customer": "Unknown", "Channel Clean": "Unknown", "Bucket": "Unknown", "Deduction Type": "Unspecified"}.items():
    if col not in current.columns:
        current[col] = default

total = current["Open Balance"].sum()
count = len(current)
avg_age = current.loc[current["Open Balance"].ne(0), "Age"].mean() if current["Open Balance"].ne(0).any() else 0
aged_60 = current.loc[current["Age"].gt(60), "Open Balance"].sum()
largest_customer = current.groupby("Reporting Customer")["Open Balance"].sum().sort_values(ascending=False)
largest_type = current.groupby("Deduction Type")["Open Balance"].sum().sort_values(ascending=False)

kpi_row([
    {"label": "Open Chargebacks", "value": format_money(total, 2)},
    {"label": "Open Items", "value": f"{count:,}"},
    {"label": "Average Age", "value": f"{avg_age:,.0f} days"},
    {"label": "> 60 Days", "value": format_money(aged_60, 2)},
    {"label": "Largest Customer", "value": largest_customer.index[0] if not largest_customer.empty else "-", "delta": format_money(largest_customer.iloc[0], 2) if not largest_customer.empty else None},
    {"label": "Largest Type", "value": largest_type.index[0] if not largest_type.empty else "-", "delta": format_money(largest_type.iloc[0], 2) if not largest_type.empty else None},
])

c1, c2 = st.columns(2, gap="large")
with c1:
    section("Top Customer Exposure", "Customers with the largest open deduction balances.")
    top = largest_customer.head(10).sort_values()
    fig = go.Figure(go.Bar(x=top.values, y=top.index, orientation="h", marker_color=YELLOW, text=[format_money(v, 2) for v in top.values], textposition="inside"))
    fig.update_xaxes(tickformat="$,.2f")
    st.plotly_chart(chart_layout(fig, height=380), width="stretch")
with c2:
    section("Deduction Mix", "Current open balance by deduction type.")
    mix = largest_type.head(10).sort_values()
    fig = go.Figure(go.Bar(x=mix.values, y=mix.index, orientation="h", marker_color=YELLOW, text=[format_money(v, 2) for v in mix.values], textposition="inside"))
    fig.update_xaxes(tickformat="$,.2f")
    st.plotly_chart(chart_layout(fig, height=380), width="stretch")

section("Open Chargeback Trend", "Month-end proxy uses the latest saved AR snapshot within each month; snapshots are never added together.")
monthly = latest_by_month(history)
trend = monthly.groupby("Month")["Open Balance"].sum().reset_index()
trend["Month Date"] = trend["Month"].dt.to_timestamp()
fig = go.Figure(go.Scatter(x=trend["Month Date"], y=trend["Open Balance"], mode="lines+markers+text", text=[format_money(v, 2) for v in trend["Open Balance"]], textposition="top center", line=dict(color=YELLOW, width=3)))
fig.update_yaxes(tickformat="$,.2f")
st.plotly_chart(chart_layout(fig, height=340), width="stretch")

section("Management Attention", "Current open exposure ranked by customer, with aging and primary deduction driver.")
customer_rows = []
for customer, grp in current.groupby("Reporting Customer"):
    by_type = grp.groupby("Deduction Type")["Open Balance"].sum().sort_values(ascending=False)
    customer_rows.append({
        "Customer": customer,
        "Open CB": grp["Open Balance"].sum(),
        "% of CB": (grp["Open Balance"].sum() / total * 100) if total else 0,
        "Largest Deduction": by_type.index[0] if not by_type.empty else "-",
        "Avg Age": grp["Age"].mean(),
        "Oldest": grp["Age"].max(),
    })
attention = pd.DataFrame(customer_rows).sort_values("Open CB", ascending=False)
st.dataframe(
    attention,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Open CB": st.column_config.NumberColumn("Open CB", format="dollar"),
        "% of CB": st.column_config.NumberColumn("% of CB", format="%.1f%%"),
        "Avg Age": st.column_config.NumberColumn("Avg Age", format="%.0f"),
        "Oldest": st.column_config.NumberColumn("Oldest", format="%.0f"),
    },
)
footer()
