import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(
    page_title="Accounts Receivable | Groundwork Finance Portal",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Accounts Receivable Dashboard")

DATA_PATH = Path("data/exports/current_ar_clean.csv")

if "current_ar_data" in st.session_state:
    df = st.session_state["current_ar_data"].copy()
elif DATA_PATH.exists():
    df = pd.read_csv(DATA_PATH)
else:
    st.warning("No AR snapshot found. Go to Admin, upload an AR Aging file, and click Save Current AR Snapshot.")
    st.stop()

df["Open Balance"] = pd.to_numeric(df["Open Balance"], errors="coerce").fillna(0)
df["Age"] = pd.to_numeric(df["Age"], errors="coerce").fillna(0)
df["Bucket"] = df["Bucket"].fillna("Unknown")
df["Channel Clean"] = df["Channel Clean"].fillna("Unknown")
df["Terms: Name"] = df["Terms: Name"].fillna("Unknown")

bucket_order = ["Current", "1-14", "15-30", "31-60", "61-90", "91+"]

total_ar = df["Open Balance"].sum()
current_ar = df.loc[df["Bucket"].eq("Current"), "Open Balance"].sum()
past_due = total_ar - current_ar
over_91 = df.loc[df["Bucket"].eq("91+"), "Open Balance"].sum()
customer_count = df["Reporting Customer"].nunique()

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total AR", f"${total_ar:,.0f}")
col2.metric("Current", f"${current_ar:,.0f}")
col3.metric("Past Due", f"${past_due:,.0f}")
col4.metric("91+", f"${over_91:,.0f}")
col5.metric("Customers", f"{customer_count:,}")

st.divider()

st.markdown("## Aging by Channel by Bucket")

channel_table = pd.pivot_table(
    df,
    values="Open Balance",
    index="Channel Clean",
    columns="Bucket",
    aggfunc="sum",
    fill_value=0,
)

for bucket in bucket_order:
    if bucket not in channel_table.columns:
        channel_table[bucket] = 0

channel_table = channel_table[bucket_order]
channel_table["Grand Total"] = channel_table.sum(axis=1)

grand_total_row = pd.DataFrame(channel_table.sum()).T
grand_total_row.index = ["Grand Total"]

channel_table = pd.concat([channel_table, grand_total_row])

st.dataframe(
    channel_table.style.format("${:,.0f}"),
    use_container_width=True
)

st.markdown("## Aging by Terms by Bucket")

terms_table = pd.pivot_table(
    df,
    values="Open Balance",
    index="Terms: Name",
    columns="Bucket",
    aggfunc="sum",
    fill_value=0,
)

for bucket in bucket_order:
    if bucket not in terms_table.columns:
        terms_table[bucket] = 0

terms_table = terms_table[bucket_order]
terms_table["Grand Total"] = terms_table.sum(axis=1)

grand_total_terms = pd.DataFrame(terms_table.sum()).T
grand_total_terms.index = ["Grand Total"]

terms_table = pd.concat([terms_table, grand_total_terms])

st.dataframe(
    terms_table.style.format("${:,.0f}"),
    use_container_width=True
)

st.markdown("## Top 25 Past Due Customers")

past_due_df = df[df["Age"] > 0]

top_customers = (
    past_due_df
    .groupby(["Reporting Customer", "Channel Clean"], as_index=False)["Open Balance"]
    .sum()
    .sort_values("Open Balance", ascending=False)
    .head(25)
)

st.dataframe(
    top_customers.style.format({"Open Balance": "${:,.0f}"}),
    use_container_width=True,
    hide_index=True
)

st.markdown("## Invoice Detail")

detail = df[
    [
        "Reporting Customer",
        "Channel Clean",
        "Terms: Name",
        "Document Number",
        "Due Date",
        "Age",
        "Bucket",
        "Open Balance",
    ]
]

st.dataframe(
    detail.style.format({"Open Balance": "${:,.0f}"}),
    use_container_width=True,
    hide_index=True
)