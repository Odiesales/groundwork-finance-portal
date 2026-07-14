import streamlit as st
from utils.data import load_revenue_history, revenue_summary, monthly_revenue_summary
from utils.ui import (
    page_header, section, footer, metric_row, format_money, format_number,
    apply_multiselect_filter, style_revenue_table, bar_chart, line_chart
)

st.set_page_config(page_title="Weekly Revenue Report", page_icon="💰", layout="wide")
page_header(
    "Weekly Revenue Report",
    "Weekly revenue, pounds sold, weighted $/LB, channel mix, customer pricing, and package-size analysis.",
    badge="Weekly Upload"
)

df = load_revenue_history()
if df.empty:
    st.info("Upload and save a Revenue snapshot in Administration first.")
    footer()
    st.stop()

st.sidebar.markdown("## Revenue Filters")
for label, col in [
    ("Channel", "Sales Channel"),
    ("Customer", "Customer"),
    ("Sales Rep", "Sales Rep"),
    ("Item Class", "Item Class"),
    ("Coffee Size", "Coffee Size"),
]:
    df = apply_multiselect_filter(df, label, col)

if df["Trend Date"].notna().any():
    min_date = df["Trend Date"].min().date()
    max_date = df["Trend Date"].max().date()
    date_range = st.sidebar.date_input("Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = date_range
        df = df[(df["Trend Date"].dt.date >= start) & (df["Trend Date"].dt.date <= end)]

search = st.sidebar.text_input("Search customer / item")
if search:
    s = search.lower()
    df = df[
        df["Customer"].str.lower().str.contains(s, na=False)
        | df["Item / Memo"].str.lower().str.contains(s, na=False)
    ]

revenue = df["Revenue"].sum()
lbs = df["Lbs"].sum()
weighted = revenue / lbs if lbs else 0
avg_lb = df.loc[df["$/LB"].ne(0), "$/LB"].mean() if not df.empty else 0
rows = len(df)
customers = df["Customer"].nunique()
orders = df["Document Number"].nunique() if "Document Number" in df.columns else rows

section("Revenue KPIs", "Filtered totals from the loaded revenue data.")
metric_row([
    ("Revenue", format_money(revenue, 2)),
    ("Pounds Sold", format_number(lbs, 1)),
    ("Weighted $/LB", format_money(weighted)),
    ("Avg $/LB", format_money(avg_lb)),
    ("Customers", f"{customers:,}"),
    ("Orders / Rows", f"{orders:,}"),
])

monthly = monthly_revenue_summary(df)
left, right = st.columns(2)
with left:
    section("Revenue Trend")
    if monthly.empty:
        st.info("No date available for trend chart.")
    else:
        st.plotly_chart(bar_chart(monthly, "Month", "Revenue", text="Revenue"), use_container_width=True)
with right:
    section("Weighted $/LB Trend")
    if monthly.empty:
        st.info("No date available for $/LB trend chart.")
    else:
        st.plotly_chart(line_chart(monthly, "Month", "Weighted $/LB"), use_container_width=True)

left, right = st.columns(2)
with left:
    section("Channel Analysis", "Revenue, pounds, mix, and realized $/LB by sales channel.")
    channel = revenue_summary(df, "Sales Channel")
    st.dataframe(style_revenue_table(channel), use_container_width=True, hide_index=True)
with right:
    section("Coffee Size Analysis", "Shows whether price movement is driven by package-size mix.")
    st.dataframe(style_revenue_table(revenue_summary(df, "Coffee Size").head(50)), use_container_width=True, hide_index=True)

left, right = st.columns(2)
with left:
    section("Top Customers by Revenue")
    st.dataframe(style_revenue_table(revenue_summary(df, "Customer").head(25)), use_container_width=True, hide_index=True)
with right:
    section("Sales Rep Performance")
    st.dataframe(style_revenue_table(revenue_summary(df, "Sales Rep").head(25)), use_container_width=True, hide_index=True)

section("Product / Item Pricing")
st.dataframe(style_revenue_table(revenue_summary(df, "Item / Memo").head(75)), use_container_width=True, hide_index=True)

with st.expander("Cleaned Revenue Detail"):
    st.dataframe(df, use_container_width=True, hide_index=True)

footer()
