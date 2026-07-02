import streamlit as st

st.set_page_config(page_title="Accounts Receivable", page_icon="💰", layout="wide")

st.title("💰 Accounts Receivable")
st.caption("Version 0.1.0 — dashboard placeholder")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total AR", "$0")
col2.metric("Current", "$0")
col3.metric("Past Due", "$0")
col4.metric("91+", "$0")

st.info("Next version will connect this page to the AR Aging upload.")

st.subheader("Planned Sections")
st.markdown("""
- Aging by Bucket
- Aging by Channel: Foodservice / Grocery
- Aging by Terms
- Top Past Due Customers
- Customer / Invoice Detail
""")
