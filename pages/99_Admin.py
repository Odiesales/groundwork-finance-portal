import streamlit as st
import pandas as pd
from pathlib import Path

from utils.cleaner import clean_ar_data

st.set_page_config(
    page_title="Admin | Groundwork Finance Portal",
    page_icon="⚙️",
    layout="wide"
)

st.title("⚙️ Administration")
st.subheader("Upload Weekly AR Aging")

EXPORT_PATH = Path("data/exports/current_ar_clean.csv")
EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

uploaded_file = st.file_uploader(
    "Choose AR Aging Excel File",
    type=["xlsx", "xls"]
)

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    df = clean_ar_data(df)

    st.success("File uploaded and cleaned successfully!")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Rows", f"{len(df):,}")

    with col2:
        st.metric("Customers", f"{df['Reporting Customer'].nunique():,}")

    with col3:
        st.metric("Total AR", f"${df['Open Balance'].sum():,.2f}")

    if st.button("Save Current AR Snapshot"):
        st.session_state["current_ar_data"] = df
        df.to_csv(EXPORT_PATH, index=False)
        st.success("Current AR snapshot saved for this session. Go to Accounts Receivable dashboard.")

    preview = df[
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

    st.markdown("## Cleaned Data Preview")
    st.dataframe(preview, use_container_width=True, hide_index=True)

else:
    st.info("Upload a weekly AR Aging Excel report.")