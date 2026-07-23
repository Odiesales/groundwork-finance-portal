import pandas as pd
import streamlit as st
from utils.data import load_revenue_history, load_ar_history, monthly_revenue_summary
from utils.ui import page_header, section, footer

page_header("Trends & Analytics", "Month-over-month Revenue and selectable AR snapshot comparisons.", badge="Historical")
rev = load_revenue_history(include_current=False)
ar = load_ar_history(include_current=False)
if rev.empty and ar.empty:
    st.info("Save snapshots in Administration first. Trends will appear once historical data exists.")
    st.stop()

if not rev.empty:
    section("Month-over-Month Revenue", "Monthly numbers are shown first for faster executive review.")
    monthly = monthly_revenue_summary(rev)
    monthly["Revenue Change"] = monthly["Revenue"].diff()
    monthly["$/LB Change"] = monthly["Weighted $/LB"].diff()
    st.download_button("⇩ Export MoM Revenue", monthly.to_csv(index=False).encode("utf-8"), "Revenue_MoM.csv", "text/csv")
    st.dataframe(
        monthly, width="stretch", hide_index=True,
        column_config={
            "Revenue": st.column_config.NumberColumn("Revenue", format="$%,.2f"),
            "Lbs": st.column_config.NumberColumn("Lbs", format="%,.2f"),
            "Weighted $/LB": st.column_config.NumberColumn("Weighted $/LB", format="$%,.2f"),
            "MoM Revenue %": st.column_config.NumberColumn("MoM Revenue %", format="%.2f%%"),
            "MoM $/LB %": st.column_config.NumberColumn("MoM $/LB %", format="%.2f%%"),
            "Revenue Change": st.column_config.NumberColumn("Revenue Change", format="$%,.2f"),
            "$/LB Change": st.column_config.NumberColumn("$/LB Change", format="$%,.2f"),
        },
    )

if not ar.empty:
    ar["Snapshot Date"] = pd.to_datetime(ar.get("Snapshot Date"), errors="coerce")
    ar["Open Balance"] = pd.to_numeric(ar.get("Open Balance", 0), errors="coerce").fillna(0)
    ar["Bucket"] = ar.get("Bucket", "Unknown").fillna("Unknown").astype(str).str.strip()
    dates = sorted(ar["Snapshot Date"].dropna().dt.normalize().unique(), reverse=True)
    section("AR Snapshot Comparison", "Pick any two saved as-of dates and compare Total AR, Current, and Past Due.")
    c1, c2 = st.columns(2)
    date_options = [pd.Timestamp(d) for d in dates]
    with c1:
        current_date = st.selectbox("As of Date", date_options, format_func=lambda d: d.strftime("%b %d, %Y"), key="trend_ar_current")
    with c2:
        prior_date = st.selectbox("Compare Against", date_options, index=min(1, len(date_options)-1), format_func=lambda d: d.strftime("%b %d, %Y"), key="trend_ar_prior")

    def snapshot_values(value):
        snap = ar[ar["Snapshot Date"].dt.normalize().eq(pd.Timestamp(value))].copy()
        balances = snap["Open Balance"]
        current_mask = snap["Bucket"].str.casefold().eq("current")
        total = float(balances.sum())
        current = float(balances[current_mask].sum())
        return {"Total AR": total, "Current": current, "Past Due": total - current}

    current_values = snapshot_values(current_date)
    prior_values = snapshot_values(prior_date)
    rows = []
    for metric in ["Total AR", "Current", "Past Due"]:
        current_amount = current_values[metric]
        prior_amount = prior_values[metric]
        change = current_amount - prior_amount
        change_pct = change / abs(prior_amount) if prior_amount else pd.NA
        rows.append({
            "Metric": metric,
            pd.Timestamp(current_date).strftime("%b %d, %Y"): current_amount,
            pd.Timestamp(prior_date).strftime("%b %d, %Y"): prior_amount,
            "Change": change,
            "Change %": change_pct,
        })
    comparison = pd.DataFrame(rows)
    st.download_button("⇩ Export AR Comparison", comparison.to_csv(index=False).encode("utf-8"), "AR_Snapshot_Comparison.csv", "text/csv")
    amount_cols = [c for c in comparison.columns if c not in ["Metric", "Change %"]]
    config = {c: st.column_config.NumberColumn(c, format="$%,.2f") for c in amount_cols}
    config["Change %"] = st.column_config.NumberColumn("Change %", format="%.2f%%")
    st.dataframe(comparison, width="stretch", hide_index=True, column_config=config)

    section("AR Snapshot History", "All saved snapshots are preserved and shown newest first.")
    history_rows = []
    for d in sorted(date_options):
        values = snapshot_values(d)
        history_rows.append({"As of Date": d, **values})
    hist = pd.DataFrame(history_rows).sort_values("As of Date", ascending=False)
    hist["WoW Change"] = hist["Total AR"] - hist["Total AR"].shift(-1)
    st.download_button("⇩ Export AR History", hist.to_csv(index=False).encode("utf-8"), "AR_History.csv", "text/csv")
    st.dataframe(
        hist, width="stretch", hide_index=True,
        column_config={
            "As of Date": st.column_config.DateColumn("As of Date", format="MMM DD, YYYY"),
            "Total AR": st.column_config.NumberColumn("Total AR", format="$%,.2f"),
            "Current": st.column_config.NumberColumn("Current", format="$%,.2f"),
            "Past Due": st.column_config.NumberColumn("Past Due", format="$%,.2f"),
            "WoW Change": st.column_config.NumberColumn("WoW Change", format="$%,.2f"),
        },
    )
footer()
