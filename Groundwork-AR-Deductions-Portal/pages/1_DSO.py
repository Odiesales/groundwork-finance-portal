from __future__ import annotations

import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.data import load_ar_history, load_revenue_history
from utils.ui import YELLOW, chart_layout, footer, format_money, kpi_row, page_header, section

FINANCE_CHANNELS = [
    "Foodservice Direct", "Foodservice Distributor", "Grocery Direct", "Grocery Distributor",
]


def clean_text(value):
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def finance_channel(value):
    text = clean_text(value)
    if "foodservice" in text or "food service" in text:
        return "Foodservice Distributor" if "distribut" in text else "Foodservice Direct"
    if "grocery" in text:
        return "Grocery Distributor" if "distribut" in text else "Grocery Direct"
    return str(value or "Other").strip() or "Other"


def prep_ar_monthly(ar):
    if ar.empty:
        return pd.DataFrame()
    work = ar.copy()
    work["Snapshot Date"] = pd.to_datetime(work.get("Snapshot Date"), errors="coerce")
    work = work.dropna(subset=["Snapshot Date"])
    if work.empty:
        return work
    work["Month"] = work["Snapshot Date"].dt.to_period("M")
    latest = work.groupby("Month")["Snapshot Date"].transform("max")
    work = work[work["Snapshot Date"].eq(latest)].copy()
    work["Open Balance"] = pd.to_numeric(work.get("Open Balance", 0), errors="coerce").fillna(0)
    work["Finance Channel"] = work.get("Channel Clean", "Unknown").map(finance_channel)
    work["Customer Key"] = work.get("Reporting Customer", "Unknown").map(clean_text)
    return work


def prep_sales(revenue):
    if revenue.empty:
        return pd.DataFrame()
    work = revenue.copy()
    work["Date"] = pd.to_datetime(work.get("Date"), errors="coerce")
    work = work.dropna(subset=["Date"])
    if work.empty:
        return work
    work["Month"] = work["Date"].dt.to_period("M")
    work["Revenue"] = pd.to_numeric(work.get("Revenue", 0), errors="coerce").fillna(0)
    work["Finance Channel"] = work.get("Sales Channel", "Unknown").map(finance_channel)
    work["Customer Key"] = work.get("Customer", "Unknown").map(clean_text)
    return work


def dso(ar_value, sales_value, elapsed_days):
    return (ar_value / sales_value * elapsed_days) if sales_value else None


def aligned_month(ar, sales, period):
    """Use the latest AR snapshot in the month and sales only through that same as-of date."""
    p = pd.Period(period, freq="M")
    ar_m = ar[ar["Month"].eq(p)].copy()
    if ar_m.empty:
        return ar_m, sales.iloc[0:0].copy(), None, None
    as_of = pd.Timestamp(ar_m["Snapshot Date"].max()).normalize()
    sales_m = sales[(sales["Month"].eq(p)) & (sales["Date"].dt.normalize().le(as_of))].copy()
    elapsed_days = int(as_of.day)
    return ar_m, sales_m, as_of, elapsed_days


ar = prep_ar_monthly(load_ar_history())
sales = prep_sales(load_revenue_history())

page_header("Days Sales Outstanding", "Finance DSO aligned to each AR as-of date: Net AR / sales through the same date x elapsed calendar days.")

if ar.empty:
    st.info("Upload AR snapshots in Administration to calculate DSO."); footer(); st.stop()
if sales.empty:
    st.warning("Sales history is not available. DSO requires sales data as a denominator."); footer(); st.stop()

common_months = sorted(set(ar["Month"].unique()) & set(sales["Month"].unique()))
if not common_months:
    st.warning("AR and sales data do not currently overlap in the same month."); footer(); st.stop()

selected_period = pd.Period(st.selectbox("Reporting Month", options=list(reversed(common_months)), format_func=lambda p: pd.Period(p, freq="M").strftime("%B %Y")), freq="M")
ar_m, sales_m, as_of, elapsed_days = aligned_month(ar, sales, selected_period)

total_ar = ar_m["Open Balance"].sum()
total_sales = sales_m["Revenue"].sum()
overall_dso = dso(total_ar, total_sales, elapsed_days)

history_rows = []
for period in common_months:
    p = pd.Period(period, freq="M")
    a_df, s_df, p_as_of, p_days = aligned_month(ar, sales, p)
    a = a_df["Open Balance"].sum()
    s = s_df["Revenue"].sum()
    history_rows.append({"Month": p.to_timestamp(), "As of Date": p_as_of, "Net AR": a, "Sales Through As Of": s, "Elapsed Days": p_days, "DSO": dso(a, s, p_days)})
history = pd.DataFrame(history_rows).sort_values("Month")

month_ts = selected_period.to_timestamp()
prior = history[history["Month"].lt(month_ts)].tail(1)
prior_dso = float(prior["DSO"].iloc[0]) if not prior.empty and pd.notna(prior["DSO"].iloc[0]) else None
change = overall_dso - prior_dso if overall_dso is not None and prior_dso is not None else None
avg_12 = history.tail(12)["DSO"].dropna().mean()

kpi_row([
    {"label":"Overall DSO", "value":f"{overall_dso:,.0f} days" if overall_dso is not None else "N/M"},
    {"label":"Prior Month", "value":f"{prior_dso:,.0f} days" if prior_dso is not None else "N/M"},
    {"label":"Change", "value":f"{change:+,.0f} days" if change is not None else "N/M"},
    {"label":"Net AR", "value":format_money(total_ar, 2)},
    {"label":"Sales Through As Of", "value":format_money(total_sales, 2)},
    {"label":"12-Month Avg", "value":f"{avg_12:,.0f} days" if pd.notna(avg_12) else "N/M"},
])
st.caption(f"Selected AR snapshot: {as_of:%B %d, %Y} · Sales denominator through the same date · {elapsed_days} elapsed calendar days")

section("DSO Trend", "Each point aligns the AR snapshot, sales cutoff, and elapsed day count to the same as-of date.")
fig = go.Figure(go.Scatter(x=history["Month"], y=history["DSO"], mode="lines+markers+text", text=[f"{v:.0f}" if pd.notna(v) else "" for v in history["DSO"]], textposition="top center", line=dict(color=YELLOW, width=3), marker=dict(size=8)))
fig.update_yaxes(title="DSO (Days)")
st.plotly_chart(chart_layout(fig, height=360), use_container_width=True)

section("DSO by Channel", "Four-channel Finance view using the same aligned as-of methodology.")
rows = []
channels = FINANCE_CHANNELS + sorted((set(ar_m["Finance Channel"]) | set(sales_m["Finance Channel"])) - set(FINANCE_CHANNELS))
for channel in channels:
    a = ar_m.loc[ar_m["Finance Channel"].eq(channel), "Open Balance"].sum()
    s = sales_m.loc[sales_m["Finance Channel"].eq(channel), "Revenue"].sum()
    if a == 0 and s == 0: continue
    rows.append({"Channel":channel, "Net AR":a, "Sales Through As Of":s, "DSO":dso(a, s, elapsed_days)})
channel_df = pd.DataFrame(rows)
if not channel_df.empty:
    grand = pd.DataFrame([{"Channel":"Grand Total", "Net AR":total_ar, "Sales Through As Of":total_sales, "DSO":overall_dso}])
    display_channel = pd.concat([channel_df, grand], ignore_index=True)
    styler = display_channel.style.format({"Net AR":"${:,.2f}", "Sales Through As Of":"${:,.2f}", "DSO":lambda v: "N/M" if pd.isna(v) else f"{v:,.0f}"}).apply(lambda r: ["font-weight: 700" if r["Channel"] == "Grand Total" else "" for _ in r], axis=1)
    st.dataframe(
        styler,
        use_container_width=True,
        hide_index=True,
    )

section("Customer DSO", "Customer open AR divided by customer sales through the same as-of date. N/M means sales are zero or unavailable.")
ar_customer = ar_m.groupby(["Customer Key", "Reporting Customer"], dropna=False)["Open Balance"].sum().reset_index()
sales_customer = sales_m.groupby("Customer Key", dropna=False)["Revenue"].sum().reset_index().rename(columns={"Revenue":"Sales Through As Of"})
customer = ar_customer.merge(sales_customer, on="Customer Key", how="outer")
customer["Reporting Customer"] = customer["Reporting Customer"].fillna(customer["Customer Key"])
customer["Open Balance"] = pd.to_numeric(customer["Open Balance"], errors="coerce").fillna(0)
customer["Sales Through As Of"] = pd.to_numeric(customer["Sales Through As Of"], errors="coerce").fillna(0)
customer["DSO"] = customer.apply(lambda r: dso(r["Open Balance"], r["Sales Through As Of"], elapsed_days), axis=1)
customer = customer.sort_values(["DSO", "Open Balance"], ascending=[False, False], na_position="first")
show = customer[["Reporting Customer", "Open Balance", "Sales Through As Of", "DSO"]].rename(columns={"Reporting Customer":"Customer"})
st.dataframe(show, use_container_width=True, hide_index=True, height=520, column_config={"Open Balance":st.column_config.NumberColumn("Open AR", format="$%,.2f"), "Sales Through As Of":st.column_config.NumberColumn("Sales Through As Of", format="$%,.2f"), "DSO":st.column_config.NumberColumn("DSO (Days)", format="%.0f")})

st.caption("DSO formula: Net AR / sales through the AR snapshot date x elapsed calendar days in that month. This prevents partial-month sales from being multiplied by a full-month day count.")
footer()
