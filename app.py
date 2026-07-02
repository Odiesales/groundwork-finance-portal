import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="Groundwork Finance Portal",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("☕ Groundwork Finance Portal")
st.caption("Version 0.1.0 — Application Shell")

st.markdown("### Welcome")
st.info("Use the pages on the left to open Accounts Receivable or Admin.")

col1, col2, col3 = st.columns(3)
col1.metric("Total AR", "$0")
col2.metric("Past Due", "$0")
col3.metric("Customers", "0")

st.divider()
st.markdown("""
#### Current Sprint
- Build the app shell
- Add Admin upload page
- Prepare AR dashboard structure
- Prepare folders for future historical snapshots
""")
