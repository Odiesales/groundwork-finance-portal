from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.data import load_ar_history
from utils.ui import (
    GREEN, GREEN_2, YELLOW, RED, chart_layout, footer, format_money,
    insight_box, kpi_row, page_header, section, style_money_table,
)

def _norm_text(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip().str.lower()


def _snapshot_frames(df: pd.DataFrame):
    data = df.copy()
    data["Snapshot Date"] = pd.to_datetime(data.get("Snapshot Date"), errors="coerce")
    dates = sorted(data["Snapshot Date"].dropna().dt.normalize().unique())
    if not dates:
        return data, pd.DataFrame(), None, None
    current_date = pd.Timestamp(dates[-1])
    previous_date = pd.Timestamp(dates[-2]) if len(dates) > 1 else None
    current = data[data["Snapshot Date"].dt.normalize().eq(current_date)].copy()
    previous = data[data["Snapshot Date"].dt.normalize().eq(previous_date)].copy() if previous_date is not None else pd.DataFrame()
    return current, previous, current_date, previous_date


def _position_metrics(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"total":0, "past_due":0, "current_pct":0, "dso":0, "customers":0, "over_90":0}
    balances = pd.to_numeric(df["Open Balance"], errors="coerce").fillna(0)
    total = balances.sum()
    current = balances[df["Bucket"].fillna("").eq("Current")].sum()
    past_due = total - current
    over_90 = balances[df["Bucket"].fillna("").isin(["91+", "90+"])].sum()
    age = pd.to_numeric(df.get("Age", 0), errors="coerce").fillna(0).clip(lower=0)
    positive = balances.clip(lower=0)
    weighted_age = float((age * positive).sum() / positive.sum()) if positive.sum() else 0
    return {
        "total": float(total), "past_due": float(past_due),
        "current_pct": float(current / total) if total else 0,
        "dso": weighted_age, "customers": int(df.loc[balances.ne(0), "Reporting Customer"].nunique()),
        "over_90": float(over_90),
    }


def _weekly_activity(df: pd.DataFrame, snapshot_date: pd.Timestamp | None) -> dict:
    result = {"sales":0, "credits":0, "chargebacks":0, "recoveries":0}
    if df.empty or snapshot_date is None:
        return result
    work = df.copy()
    work["Date"] = pd.to_datetime(work.get("Date"), errors="coerce")
    start = snapshot_date - pd.Timedelta(days=6)
    week = work[work["Date"].between(start, snapshot_date, inclusive="both")].copy()
    transaction = _norm_text(week["Transaction Type"])
    reason = _norm_text(week["Deduction Type"])
    gross = pd.to_numeric(week.get("Amount (Gross)", 0), errors="coerce").fillna(0).abs()
    open_balance = pd.to_numeric(week.get("Open Balance", 0), errors="coerce").fillna(0).abs()

    invoice_mask = transaction.str.contains("invoice", regex=False) & ~reason.eq("holdback")
    credit_mask = transaction.str.contains("credit", regex=False)
    recovery_mask = transaction.str.contains("chargeback", regex=False) & reason.isin(["duplicate pmt", "overpayment", "on account payment (oap)"])
    chargeback_mask = transaction.str.contains("chargeback", regex=False) & ~recovery_mask

    result["sales"] = float(gross[invoice_mask].sum())
    result["credits"] = float(gross[credit_mask].sum())
    result["chargebacks"] = float(gross[chargeback_mask].sum())
    result["recoveries"] = float(open_balance[recovery_mask].sum())
    return result


def _delta(current, previous, money=True, percent_value=False):
    if previous is None:
        return "No prior Monday"
    change = current - previous
    arrow = "▲" if change > 0 else "▼" if change < 0 else "—"
    if percent_value:
        return f"{arrow} {change:+.1%} WoW"
    if money:
        pct = change / abs(previous) if previous else np.nan
        pct_text = f" ({pct:+.1%})" if not pd.isna(pct) else ""
        return f"{arrow} {format_money(abs(change), 2)}{pct_text} WoW"
    return f"{arrow} {change:+,.0f} WoW"


def _customer_balances(df):
    if df.empty:
        return pd.Series(dtype=float)
    return df.groupby("Reporting Customer", dropna=False)["Open Balance"].sum().sort_values(ascending=False)


ar_all = load_ar_history()
current, previous, snapshot_date, previous_date = _snapshot_frames(ar_all)

page_header(
    "Executive Scorecard",
    "Weekly receivables position, business activity, risk, and customer movement.",
    snapshot_date=snapshot_date,
    compared_date=previous_date,
)

if current.empty:
    st.info("Upload an AR Aging report in Administration to populate the Executive Scorecard.")
    footer()
    st.stop()

current_pos = _position_metrics(current)
previous_pos = _position_metrics(previous) if not previous.empty else None
current_activity = _weekly_activity(current, snapshot_date)
previous_activity = _weekly_activity(previous, previous_date) if not previous.empty else None

section("Financial Position", "Where receivables stand as of the current Monday snapshot.")
kpi_row([
    {"label":"Total AR", "value":format_money(current_pos["total"], 2), "delta":_delta(current_pos["total"], previous_pos["total"] if previous_pos else None), "inverse":True},
    {"label":"Past Due", "value":format_money(current_pos["past_due"], 2), "delta":_delta(current_pos["past_due"], previous_pos["past_due"] if previous_pos else None), "inverse":True},
    {"label":"Current %", "value":f'{current_pos["current_pct"]:.1%}', "delta":_delta(current_pos["current_pct"], previous_pos["current_pct"] if previous_pos else None, money=False, percent_value=True)},
    {"label":"Avg. Days Outstanding", "value":f'{current_pos["dso"]:.0f}', "delta":_delta(current_pos["dso"], previous_pos["dso"] if previous_pos else None, money=False), "inverse":True},
    {"label":"Active Customers", "value":f'{current_pos["customers"]:,}', "delta":_delta(current_pos["customers"], previous_pos["customers"] if previous_pos else None, money=False)},
    {"label":"90+ Exposure", "value":format_money(current_pos["over_90"], 2), "delta":_delta(current_pos["over_90"], previous_pos["over_90"] if previous_pos else None), "inverse":True},
])

section("This Week's Activity", "Transactions dated within the seven-day period ending on the selected Monday snapshot.")
kpi_row([
    {"label":"New Sales · Gross Invoices", "value":format_money(current_activity["sales"], 2), "delta":_delta(current_activity["sales"], previous_activity["sales"] if previous_activity else None)},
    {"label":"New Credit Memos", "value":format_money(current_activity["credits"], 2), "delta":_delta(current_activity["credits"], previous_activity["credits"] if previous_activity else None), "inverse":True},
    {"label":"New Chargebacks", "value":format_money(current_activity["chargebacks"], 2), "delta":_delta(current_activity["chargebacks"], previous_activity["chargebacks"] if previous_activity else None), "inverse":True},
    {"label":"CB Recoveries", "value":format_money(current_activity["recoveries"], 2), "delta":_delta(current_activity["recoveries"], previous_activity["recoveries"] if previous_activity else None)},
])

insights = []
if previous_pos:
    total_change = current_pos["total"] - previous_pos["total"]
    past_due_change = current_pos["past_due"] - previous_pos["past_due"]
    insights.append(f'Total AR {"increased" if total_change > 0 else "decreased"} by {format_money(abs(total_change), 2)} week over week.')
    insights.append(f'Past due AR {"increased" if past_due_change > 0 else "improved"} by {format_money(abs(past_due_change), 2)}.')
else:
    insights.append("A second Monday snapshot will activate all week-over-week comparisons.")
insights.append(f'New sales totaled {format_money(current_activity["sales"], 2)} for the seven-day reporting period.')
net_cb = current_activity["recoveries"] - current_activity["chargebacks"]
insights.append(f'CB recoveries were {format_money(abs(net_cb), 2)} {"above" if net_cb >= 0 else "below"} new chargebacks.')
insight_box("Monday Overview", insights)

left, right = st.columns([1, 1.05], gap="large")
with left:
    section("Cash at Risk", "Open AR by aging bucket.")
    bucket_order = ["Current", "1-14", "15-30", "31-60", "61-90", "91+"]
    aging = current.groupby("Bucket", dropna=False)["Open Balance"].sum().reindex(bucket_order).fillna(0)
    colors = [GREEN_2, "#6E8D7E", "#A7A58B", YELLOW, "#D98D55", RED]
    fig = go.Figure(go.Bar(
        x=aging.values, y=aging.index, orientation="h",
        marker_color=colors, text=[format_money(v, 2) for v in aging.values], textposition="auto",
        hovertemplate="%{y}: $%{x:,.0f}<extra></extra>",
    ))
    fig.update_layout(yaxis=dict(autorange="reversed"))
    st.plotly_chart(chart_layout(fig, height=335), width='stretch')

with right:
    section("Top Customer Exposure", "Largest open balances in the current snapshot.")
    top = _customer_balances(current).head(10).sort_values()
    fig = go.Figure(go.Bar(
        x=top.values, y=top.index, orientation="h", marker_color=GREEN_2,
        text=[format_money(v, 2) for v in top.values], textposition="auto",
        hovertemplate="%{y}: $%{x:,.0f}<extra></extra>",
    ))
    st.plotly_chart(chart_layout(fig, height=335), width='stretch')

section("Executive Watchlist", "Accounts with the largest aged balances and collection exposure.")
watch = current.copy()
watch["Open Balance"] = pd.to_numeric(watch["Open Balance"], errors="coerce").fillna(0)
watch["Past Due"] = np.where(watch["Bucket"].eq("Current"), 0, watch["Open Balance"])
watch["90+ Balance"] = np.where(watch["Bucket"].isin(["91+", "90+"]), watch["Open Balance"], 0)
watchlist = watch.groupby("Reporting Customer", dropna=False).agg(
    **{"Open Balance":("Open Balance", "sum"), "Past Due":("Past Due", "sum"), "90+ Balance":("90+ Balance", "sum")},
    Channel=("Channel Clean", "first"), Terms=("Terms: Name", "first"),
).reset_index()
watchlist["Past Due %"] = np.where(watchlist["Open Balance"].ne(0), watchlist["Past Due"] / watchlist["Open Balance"], 0)
watchlist["Priority"] = np.select(
    [watchlist["90+ Balance"] >= 50000, watchlist["Past Due"] >= 100000, watchlist["Past Due %"] >= .75],
    ["Critical", "High", "Elevated"], default="Monitor",
)
watchlist = watchlist.sort_values(["90+ Balance", "Past Due"], ascending=False).head(12)
st.dataframe(
    watchlist.style.format({"Open Balance":"${:,.2f}", "Past Due":"${:,.2f}", "90+ Balance":"${:,.2f}", "Past Due %":"{:.1%}"}),
    width='stretch', hide_index=True,
)

section("Largest Customer Changes", "Week-over-week movement by customer.")
if previous.empty:
    st.info("Save one more Monday snapshot to show the largest customer increases and reductions.")
else:
    current_customers = _customer_balances(current)
    previous_customers = _customer_balances(previous)
    movement = pd.concat([current_customers.rename("Current AR"), previous_customers.rename("Prior AR")], axis=1).fillna(0)
    movement["WoW Change"] = movement["Current AR"] - movement["Prior AR"]
    movement = movement.reset_index().rename(columns={"index":"Reporting Customer"})
    increases = movement.nlargest(8, "WoW Change")
    reductions = movement.nsmallest(8, "WoW Change")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        section("Largest Increases")
        st.dataframe(style_money_table(increases), width='stretch', hide_index=True)
    with c2:
        section("Largest Reductions")
        st.dataframe(style_money_table(reductions), width='stretch', hide_index=True)

footer()
