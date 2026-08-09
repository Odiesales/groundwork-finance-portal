import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from utils.data import load_ar_history
from utils.ui import YELLOW, chart_layout, page_header, section, footer

page_header("AR Trends & Analytics", "Historical receivables trends and selectable AR snapshot comparisons.", badge="Historical")
ar = load_ar_history(include_current=False)
if ar.empty:
    st.info("Save AR snapshots in Administration first. Trends will appear once historical AR data exists.")
    footer(); st.stop()

ar["Snapshot Date"] = pd.to_datetime(ar.get("Snapshot Date"), errors="coerce")
ar["Open Balance"] = pd.to_numeric(ar.get("Open Balance", 0), errors="coerce").fillna(0)
ar["Bucket"] = ar.get("Bucket", "Unknown").fillna("Unknown").astype(str).str.strip()
dates = sorted(ar["Snapshot Date"].dropna().dt.normalize().unique(), reverse=True)
date_options = [pd.Timestamp(d) for d in dates]


def snapshot_values(value):
    snap = ar[ar["Snapshot Date"].dt.normalize().eq(pd.Timestamp(value))].copy()
    balances = snap["Open Balance"]
    current_mask = snap["Bucket"].str.casefold().eq("current")
    total = float(balances.sum())
    current = float(balances[current_mask].sum())
    return {"Total AR":total, "Current":current, "Past Due":total-current}

history_rows = []
for d in sorted(date_options):
    history_rows.append({"As of Date":d, **snapshot_values(d)})
hist = pd.DataFrame(history_rows).sort_values("As of Date")
hist["WoW Change"] = hist["Total AR"].diff()

section("AR Balance Trend", "Total AR, Current, and Past Due across saved snapshots. No sales or pricing activity is included on this page.")
fig = go.Figure()
for metric in ["Total AR", "Current", "Past Due"]:
    fig.add_trace(go.Scatter(x=hist["As of Date"], y=hist[metric], mode="lines+markers", name=metric))
fig.update_yaxes(title="Open AR", tickformat="$,.0f")
st.plotly_chart(chart_layout(fig, height=380), width="stretch")

section("AR Snapshot Comparison", "Pick any two saved as-of dates and compare Total AR, Current, and Past Due.")
c1, c2 = st.columns(2)
with c1:
    current_date = st.selectbox("As of Date", date_options, format_func=lambda d: d.strftime("%b %d, %Y"), key="trend_ar_current")
with c2:
    prior_date = st.selectbox("Compare Against", date_options, index=min(1, len(date_options)-1), format_func=lambda d: d.strftime("%b %d, %Y"), key="trend_ar_prior")
current_values = snapshot_values(current_date); prior_values = snapshot_values(prior_date)
rows = []
for metric in ["Total AR", "Current", "Past Due"]:
    current_amount, prior_amount = current_values[metric], prior_values[metric]
    change = current_amount - prior_amount
    rows.append({"Metric":metric, pd.Timestamp(current_date).strftime("%b %d, %Y"):current_amount, pd.Timestamp(prior_date).strftime("%b %d, %Y"):prior_amount, "Change":change, "Change %":change/abs(prior_amount) if prior_amount else pd.NA})
comparison = pd.DataFrame(rows)
st.download_button("⇩ Export AR Comparison", comparison.to_csv(index=False).encode("utf-8"), "AR_Snapshot_Comparison.csv", "text/csv")
amount_cols = [c for c in comparison.columns if c not in ["Metric", "Change %"]]
config = {c:st.column_config.NumberColumn(c, format="$%,.2f") for c in amount_cols}; config["Change %"] = st.column_config.NumberColumn("Change %", format="%.2f%%")
st.dataframe(comparison, width="stretch", hide_index=True, column_config=config)

section("AR Snapshot History", "All saved AR snapshots, newest first.")
display_hist = hist.sort_values("As of Date", ascending=False).copy()
st.download_button("⇩ Export AR History", display_hist.to_csv(index=False).encode("utf-8"), "AR_History.csv", "text/csv")
st.dataframe(display_hist, width="stretch", hide_index=True, column_config={"As of Date":st.column_config.DateColumn("As of Date", format="MMM DD, YYYY"), "Total AR":st.column_config.NumberColumn("Total AR", format="$%,.2f"), "Current":st.column_config.NumberColumn("Current", format="$%,.2f"), "Past Due":st.column_config.NumberColumn("Past Due", format="$%,.2f"), "WoW Change":st.column_config.NumberColumn("WoW Change", format="$%,.2f")})
footer()
