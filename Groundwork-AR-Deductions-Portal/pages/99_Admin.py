import pandas as pd
import streamlit as st
from datetime import date

from utils.cleaner import clean_uploaded_ar_report, convert_df_to_excel
from utils.data import (
    ar_snapshot_table,
    delete_ar_snapshots,
    load_revenue_history,
    sync_current_ar_from_latest,
)
from utils.paths import AR_SNAPSHOT_DIR, CURRENT_AR_PATH
from utils.ui import footer, format_money, page_header, section
from utils.google_drive import (
    connection_test,
    delete_file as delete_drive_file,
    sync_from_drive,
    upload_file as upload_drive_file,
)

page_header(
    "AR & Deductions Administration",
    "Upload AR aging snapshots and manage the data used by AR, DSO, and Chargeback reporting.",
    badge="Data Ops",
)

cloud_ok, cloud_message = connection_test()
status_col, sync_col = st.columns([4, 1])
with status_col:
    st.success("Google Drive: Connected") if cloud_ok else st.error(f"Google Drive: {cloud_message}")
with sync_col:
    if st.button("Sync from Drive", disabled=not cloud_ok, use_container_width=True):
        with st.spinner("Downloading shared AR and DSO sales-feed data..."):
            result = sync_from_drive()
        st.session_state["drive_initial_sync_complete"] = True
        st.success(f"Synced {result['ar_snapshots']} AR snapshot(s) and the shared sales feed.")
        st.rerun()

snapshot_date = st.date_input(
    "AR Reporting / Snapshot Date",
    value=date.today(),
    help="Use the Monday reporting date for the weekly AR portal refresh.",
)

section("AR Aging Upload", "Clean the NetSuite AR export and save a dated point-in-time snapshot.")
ar_file = st.file_uploader("Upload AR Aging export", type=["xlsx", "xls", "csv"], key="ar_upload")
if ar_file:
    try:
        ar_df = clean_uploaded_ar_report(ar_file)
        ar_df["Snapshot Date"] = snapshot_date.isoformat()
        st.success("AR file cleaned successfully.")
        c1, c2, c3 = st.columns(3)
        c1.metric("Rows", f"{len(ar_df):,}")
        c2.metric("Customers", f"{ar_df['Reporting Customer'].nunique():,}" if "Reporting Customer" in ar_df else "0")
        c3.metric("Open AR", format_money(ar_df["Open Balance"].sum()) if "Open Balance" in ar_df else "$0.00")
        ar_target = AR_SNAPSHOT_DIR / f"ar_{snapshot_date:%Y-%m-%d}.csv"
        if ar_target.exists():
            st.warning("An AR snapshot already exists for this date. Saving will replace it.")
        if st.button("Save AR Snapshot", type="primary", key="save_ar_snapshot"):
            CURRENT_AR_PATH.parent.mkdir(parents=True, exist_ok=True)
            AR_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
            ar_df.to_csv(ar_target, index=False)
            sync_current_ar_from_latest()
            try:
                upload_drive_file(ar_target, "ar")
                st.success("AR snapshot saved to Google Drive.")
            except Exception as exc:
                st.error(f"Saved locally, but Google Drive upload failed: {exc}")
        st.download_button("Download Cleaned AR Excel", convert_df_to_excel(ar_df), "cleaned_ar_report.xlsx")
        st.dataframe(ar_df.head(200), width="stretch", hide_index=True)
    except Exception as exc:
        st.error(f"Could not process AR file: {exc}")

st.divider()
section("AR Snapshot Manager", "Review or delete selected AR snapshots. Historical point-in-time balances are never added together.")
inventory = ar_snapshot_table()
if inventory.empty:
    st.info("No dated AR snapshots are available to manage.")
else:
    snapshot_dates = inventory["As of Date"].tolist()
    delete_dates = st.multiselect(
        "AR Snapshot Dates to Delete",
        options=snapshot_dates,
        format_func=lambda d: pd.Timestamp(d).strftime("%b %d, %Y"),
    )
    confirm = st.checkbox("I understand only the selected AR snapshot date(s) will be permanently removed.")
    if st.button("Delete Selected AR Snapshots", disabled=not (delete_dates and confirm)):
        deleted, latest = delete_ar_snapshots(delete_dates)
        cloud_errors = []
        for deleted_date in deleted:
            remote_name = f"ar_{pd.Timestamp(deleted_date):%Y-%m-%d}.csv"
            try:
                delete_drive_file("ar", remote_name)
            except Exception as exc:
                cloud_errors.append(f"{remote_name}: {exc}")
        if cloud_errors:
            st.warning("Local snapshots were deleted, but some Drive deletions failed: " + "; ".join(cloud_errors))
        else:
            st.success(f"Deleted {len(deleted)} selected AR snapshot(s).")
        st.rerun()
    st.dataframe(
    inventory,
    use_container_width=True,
    hide_index=True,
    column_config={
        # keep your existing column_config contents here
    },
)
        "As of Date": st.column_config.DateColumn("As of Date", format="MMM DD, YYYY"),
        "Rows": st.column_config.NumberColumn("Rows", format="%d"),
        "Customers": st.column_config.NumberColumn("Customers", format="%d"),
        "Total AR": st.column_config.NumberColumn("Total AR", format="$%,.2f"),
        "Current": st.column_config.NumberColumn("Current", format="$%,.2f"),
        "Past Due": st.column_config.NumberColumn("Past Due", format="$%,.2f"),
    })

st.divider()
section("DSO Sales Feed", "DSO reads the shared Revenue history created by the separate Sales Revenue portal. Revenue reporting is not displayed in this portal.")
revenue = load_revenue_history()
if revenue.empty:
    st.warning("No Revenue history is currently available. DSO cannot be calculated until the Sales Revenue portal has saved sales data.")
else:
    dates = pd.to_datetime(revenue.get("Date"), errors="coerce").dropna()
    c1, c2, c3 = st.columns(3)
    c1.metric("Sales Rows Available", f"{len(revenue):,}")
    c2.metric("First Sales Date", dates.min().strftime("%b %d, %Y") if not dates.empty else "Unknown")
    c3.metric("Latest Sales Date", dates.max().strftime("%b %d, %Y") if not dates.empty else "Unknown")

footer()
