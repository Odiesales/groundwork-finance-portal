import pandas as pd
import streamlit as st

from utils.cleaner import clean_uploaded_revenue_report, convert_df_to_excel
from utils.data import (
    delete_revenue_weeks,
    load_revenue_history,
    merge_revenue_history,
    revenue_week_label,
    revenue_week_table,
    revenue_week_values,
    save_revenue_history,
)
from utils.paths import REVENUE_HISTORY_PATH
from utils.ui import footer, format_money, page_header, section
from utils.google_drive import connection_test, sync_from_drive, upload_file as upload_drive_file

page_header(
    "Sales Revenue Administration",
    "Upload weekly NetSuite sales exports and manage the consolidated Revenue history.",
    badge="Data Ops",
)

cloud_ok, cloud_message = connection_test()
status_col, sync_col = st.columns([4, 1])
with status_col:
    st.success("Google Drive: Connected") if cloud_ok else st.error(f"Google Drive: {cloud_message}")
with sync_col:
    if st.button("Sync from Drive", disabled=not cloud_ok, use_container_width=True):
        with st.spinner("Downloading shared Revenue history..."):
            sync_from_drive()
        st.session_state["drive_initial_sync_complete"] = True
        st.success("Revenue history synced from Google Drive.")
        st.rerun()

history = load_revenue_history()
weeks = revenue_week_values(history)
section("Revenue Weekly Upload", "Upload the newest week or a multi-week file. Existing weeks are protected unless Replace Existing Weeks is selected.")

if history.empty:
    st.info("No Revenue history is currently loaded.")
else:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows in History", f"{len(history):,}")
    c2.metric("Weeks Loaded", f"{len(weeks):,}")
    c3.metric("Revenue", format_money(history["Revenue"].sum()))
    lbs_series = pd.to_numeric(history.get("Lbs", 0), errors="coerce").fillna(0)
    eligible = lbs_series.gt(0) & ~history.get("Sales Channel", pd.Series("", index=history.index)).fillna("").astype(str).str.contains("retail|cafe|caf", case=False, regex=True)
    eligible_lbs = lbs_series.where(eligible, 0).sum()
    eligible_revenue = pd.to_numeric(history.get("Revenue", 0), errors="coerce").fillna(0).where(eligible, 0).sum()
    c4.metric("Weighted $/LB", format_money(eligible_revenue / eligible_lbs if eligible_lbs else 0))

rev_file = st.file_uploader("Upload Revenue export", type=["xlsx", "xls", "csv"], key="rev_upload")
if rev_file:
    try:
        rev_df = clean_uploaded_revenue_report(rev_file)
        upload_weeks = revenue_week_values(rev_df)
        existing_weeks = set(weeks)
        duplicates = sorted(set(upload_weeks) & existing_weeks)
        new_weeks = sorted(set(upload_weeks) - existing_weeks)

        st.success("Revenue file cleaned successfully.")
        c1, c2, c3 = st.columns(3)
        c1.metric("Rows", f"{len(rev_df):,}")
        c2.metric("Weeks in Upload", f"{len(upload_weeks):,}")
        c3.metric("Revenue", format_money(rev_df["Revenue"].sum()))

        if new_weeks:
            st.info("New week(s): " + ", ".join(revenue_week_label(w, include_range=True) for w in new_weeks))
        if duplicates:
            st.warning("Already loaded: " + ", ".join(revenue_week_label(w, include_range=True) for w in duplicates))

        mode = st.radio("Save Mode", ["Append New Weeks Only", "Replace Existing Weeks"], horizontal=True)
        replace = mode == "Replace Existing Weeks"
        if st.button("Save Revenue History", type="primary"):
            combined, duplicate_weeks, added_weeks = merge_revenue_history(history, rev_df, replace=replace)
            save_revenue_history(combined)
            try:
                upload_drive_file(REVENUE_HISTORY_PATH, "revenue", "revenue_history.csv")
                st.success("Revenue history saved to Google Drive.")
            except Exception as exc:
                st.error(f"Revenue saved locally, but Google Drive upload failed: {exc}")
            st.rerun()

        st.download_button("Download Cleaned Revenue Excel", convert_df_to_excel(rev_df), "cleaned_revenue_report.xlsx")
        st.dataframe(rev_df.head(300), width="stretch", hide_index=True)
    except Exception as exc:
        st.error(f"Could not process Revenue file: {exc}")

st.divider()
section("Revenue History Manager", "Review or delete loaded reporting weeks.")
history = load_revenue_history()
weeks = revenue_week_values(history)
if weeks:
    delete_weeks = st.multiselect("Weeks to Delete", options=weeks, format_func=lambda w: revenue_week_label(w, include_range=True))
    confirm = st.checkbox("I understand these weeks will be removed from Revenue history.")
    if st.button("Delete Selected Weeks", disabled=not (delete_weeks and confirm)):
        revised = delete_revenue_weeks(history, delete_weeks)
        save_revenue_history(revised)
        try:
            upload_drive_file(REVENUE_HISTORY_PATH, "revenue", "revenue_history.csv")
            st.success("Selected Revenue week(s) deleted and Google Drive updated.")
        except Exception as exc:
            st.error(f"Revenue history updated locally, but Google Drive upload failed: {exc}")
        st.rerun()
    st.dataframe(revenue_week_table(history), width="stretch", hide_index=True, column_config={
        "Revenue": st.column_config.NumberColumn("Revenue", format="$%,.2f"),
        "Lbs": st.column_config.NumberColumn("Lbs", format="%.1f"),
        "Weighted $/LB": st.column_config.NumberColumn("Weighted $/LB", format="$%,.2f"),
    })
else:
    st.info("No weeks are available to manage.")

footer()
