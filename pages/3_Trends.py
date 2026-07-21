import pandas as pd
import streamlit as st
from utils.data import load_revenue_history, load_ar_history, monthly_revenue_summary
from utils.ui import style_revenue_table, style_money_table, page_header, section, footer

page_header("Trends & Analytics", "Table-first MoM revenue and selectable AR snapshot comparisons.", badge="Historical")
rev = load_revenue_history(include_current=False)
ar = load_ar_history(include_current=False)
if rev.empty and ar.empty:
    st.info("Save snapshots in Admin first. Trends will appear once historical data exists.")
    st.stop()

if not rev.empty:
    section("Month-over-Month Revenue", "Monthly numbers are shown first for faster executive review.")
    monthly = monthly_revenue_summary(rev)
    monthly["Revenue Change"] = monthly["Revenue"].diff()
    monthly["$/LB Change"] = monthly["Weighted $/LB"].diff()
    st.download_button("⇩ Export MoM Revenue", monthly.to_csv(index=False).encode("utf-8"), "Revenue_MoM.csv", "text/csv")
    st.dataframe(style_revenue_table(monthly), width="stretch", hide_index=True, column_config={"Revenue Change": st.column_config.NumberColumn(format="$%.2f"), "$/LB Change": st.column_config.NumberColumn(format="$%.2f")})

if not ar.empty:
    ar["Snapshot Date"] = pd.to_datetime(ar.get("Snapshot Date"), errors="coerce")
    dates = sorted(ar["Snapshot Date"].dropna().dt.normalize().unique(), reverse=True)
    section("AR Snapshot Comparison", "Pick any two saved as-of dates and review the numbers instead of relying on a graph.")
    c1, c2 = st.columns(2)
    with c1:
        current_date = st.selectbox("As of Date", [pd.Timestamp(d) for d in dates], format_func=lambda d: d.strftime("%b %d, %Y"), key="trend_ar_current")
    with c2:
        prior_date = st.selectbox("Compare Against", [pd.Timestamp(d) for d in dates], index=min(1, len(dates)-1), format_func=lambda d: d.strftime("%b %d, %Y"), key="trend_ar_prior")
    rows=[]
    for d, label in [(current_date,"Current"),(prior_date,"Comparison")]:
        snap=ar[ar["Snapshot Date"].dt.normalize().eq(pd.Timestamp(d))].copy()
        balances=pd.to_numeric(snap["Open Balance"], errors="coerce").fillna(0)
        current=balances[snap["Bucket"].fillna("").eq("Current")].sum()
        total=balances.sum()
        rows.append({"Period":label,"As of Date":pd.Timestamp(d).strftime("%b %d, %Y"),"Total AR":total,"Past Due":total-current,"90+":balances[snap["Bucket"].isin(["91+","90+"])].sum(),"Active Customers":snap.loc[balances.ne(0),"Reporting Customer"].nunique()})
    comparison=pd.DataFrame(rows)
    delta={"Period":"Change","As of Date":"Current vs Comparison","Total AR":comparison.loc[0,"Total AR"]-comparison.loc[1,"Total AR"],"Past Due":comparison.loc[0,"Past Due"]-comparison.loc[1,"Past Due"],"90+":comparison.loc[0,"90+"]-comparison.loc[1,"90+"],"Active Customers":comparison.loc[0,"Active Customers"]-comparison.loc[1,"Active Customers"]}
    comparison=pd.concat([comparison,pd.DataFrame([delta])],ignore_index=True)
    st.download_button("⇩ Export AR Comparison", comparison.to_csv(index=False).encode("utf-8"), "AR_Snapshot_Comparison.csv", "text/csv")
    st.dataframe(style_money_table(comparison), width="stretch", hide_index=True)

    section("AR Snapshot History", "All saved snapshots, shown as numbers.")
    hist=ar.groupby(ar["Snapshot Date"].dt.normalize()).agg(**{"Total AR":("Open Balance","sum"),"Active Customers":("Reporting Customer","nunique")}).reset_index().rename(columns={"Snapshot Date":"As of Date"}).sort_values("As of Date",ascending=False)
    hist["WoW Change"]=hist["Total AR"]-hist["Total AR"].shift(-1)
    st.download_button("⇩ Export AR History", hist.to_csv(index=False).encode("utf-8"), "AR_History.csv", "text/csv")
    st.dataframe(style_money_table(hist), width="stretch", hide_index=True)
footer()
