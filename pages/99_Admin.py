import streamlit as st
import pandas as pd
from datetime import date

from utils.cleaner import clean_uploaded_ar_report, clean_uploaded_revenue_report, convert_df_to_excel
from utils.data import (
    load_revenue_history,
    save_revenue_history,
    merge_revenue_history,
    delete_revenue_weeks,
    revenue_week_values,
    revenue_week_label,
    revenue_week_table,
)
from utils.paths import CURRENT_AR_PATH, AR_SNAPSHOT_DIR
from utils.ui import format_money, page_header, section, footer

page_header(
    "Administration",
    "Upload weekly NetSuite exports, validate results, and manage Revenue history and AR snapshots.",
    badge="Data Ops",
)

snapshot_date = st.date_input(
    "AR Reporting / Snapshot Date",
    value=date.today(),
    help="Use the Monday reporting date for the weekly AR portal refresh.",
)

ar_tab, revenue_tab, health_tab = st.tabs(["AR Upload", "Revenue History", "Data Health"])

with ar_tab:
    section("AR Aging Upload", "Clean the AR export and save a dated snapshot.")
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
                ar_df.to_csv(CURRENT_AR_PATH, index=False)
                ar_df.to_csv(ar_target, index=False)
                st.success("AR snapshot saved.")
            st.download_button("Download Cleaned AR Excel", convert_df_to_excel(ar_df), "cleaned_ar_report.xlsx")
            st.dataframe(ar_df.head(200), width="stretch", hide_index=True)
        except Exception as exc:
            st.error(f"Could not process AR file: {exc}")

with revenue_tab:
    history = load_revenue_history()
    weeks = revenue_week_values(history)
    section(
        "Revenue Weekly Upload",
        "Future uploads may contain only the newest week. Existing weeks are protected unless Replace Existing Weeks is selected.",
    )
    if history.empty:
        st.info("No Revenue history is currently loaded.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Rows in History", f"{len(history):,}")
        c2.metric("Weeks Loaded", f"{len(weeks):,}")
        c3.metric("Revenue", format_money(history["Revenue"].sum()))
        lbs_series = pd.to_numeric(history.get("Lbs", 0), errors="coerce").fillna(0)
        eligible_mask = lbs_series.gt(0) & ~history.get("Sales Channel", pd.Series("", index=history.index)).fillna("").astype(str).str.contains("retail|cafe|café", case=False, regex=True)
        eligible_lbs = lbs_series.where(eligible_mask, 0).sum()
        eligible_revenue = pd.to_numeric(history.get("Revenue", 0), errors="coerce").fillna(0).where(eligible_mask, 0).sum()
        c4.metric("Weighted $/LB", format_money(eligible_revenue / eligible_lbs if eligible_lbs else 0))

    rev_file = st.file_uploader("Upload Revenue export", type=["xlsx", "xls", "csv"], key="rev_upload")
    if rev_file:
        try:
            rev_df = clean_uploaded_revenue_report(rev_file)
            upload_weeks = revenue_week_values(rev_df)
            existing_weeks = set(weeks)
            duplicates = sorted(set(upload_weeks) & existing_weeks)
            new_weeks = sorted(set(upload_weeks) - existing_weeks)

            st.success("Revenue file cleaned successfully using Units Sold × Weight by lbs.")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Rows", f"{len(rev_df):,}")
            c2.metric("Weeks in Upload", f"{len(upload_weeks):,}")
            c3.metric("Revenue", format_money(rev_df["Revenue"].sum()))
            lbs_series = rev_df["Lbs"]
            eligible_mask = lbs_series.gt(0) & ~rev_df["Sales Channel"].fillna("").astype(str).str.contains("retail|cafe|café", case=False, regex=True)
            lbs = lbs_series.where(eligible_mask, 0).sum()
            eligible_revenue = rev_df["Revenue"].where(eligible_mask, 0).sum()
            c4.metric("Weighted $/LB", format_money(eligible_revenue / lbs if lbs else 0))

            if new_weeks:
                st.info("New week(s): " + ", ".join(revenue_week_label(w, include_range=True) for w in new_weeks))
            if duplicates:
                st.warning("Already loaded: " + ", ".join(revenue_week_label(w, include_range=True) for w in duplicates))

            review_count = int(rev_df["Weight Review"].sum()) if "Weight Review" in rev_df else 0
            if review_count:
                st.warning(f"{review_count:,} row(s) need weight review and are excluded from reliable pound analysis until corrected.")

            mode = st.radio(
                "Save Mode",
                ["Append New Weeks Only", "Replace Existing Weeks"],
                horizontal=True,
                key="revenue_save_mode",
            )
            replace = mode == "Replace Existing Weeks"
            button_label = "Append Revenue History" if not replace else "Replace / Append Revenue History"
            if st.button(button_label, type="primary", key="save_revenue_history"):
                combined, duplicate_weeks, added_weeks = merge_revenue_history(history, rev_df, replace=replace)
                save_revenue_history(combined)
                if duplicate_weeks and not replace:
                    st.success(f"Added {len(added_weeks)} new week(s). Existing duplicate week(s) were skipped.")
                else:
                    st.success("Revenue history saved successfully.")
                st.rerun()

            st.download_button("Download Cleaned Revenue Excel", convert_df_to_excel(rev_df), "cleaned_revenue_report.xlsx")
            preview_cols = [c for c in ["Week", "Date", "Document Number", "Customer", "Revenue", "Units Sold", "Package Lbs", "Lbs", "$/LB", "Weight Review"] if c in rev_df.columns]
            st.dataframe(rev_df[preview_cols].head(300), width="stretch", hide_index=True)
        except Exception as exc:
            st.error(f"Could not process Revenue file: {exc}")

    st.divider()
    section("Revenue History Manager", "Delete one or more loaded weeks from the consolidated Revenue history.")
    history = load_revenue_history()
    weeks = revenue_week_values(history)
    if weeks:
        delete_weeks = st.multiselect("Weeks to Delete", options=weeks, format_func=lambda w: revenue_week_label(w, include_range=True), key="delete_revenue_weeks")
        confirm = st.checkbox("I understand these weeks will be removed from Revenue history.")
        if st.button("Delete Selected Weeks", disabled=not (delete_weeks and confirm), key="delete_weeks_button"):
            save_revenue_history(delete_revenue_weeks(history, delete_weeks))
            st.success("Selected Revenue week(s) deleted.")
            st.rerun()
        week_counts = revenue_week_table(history)
        st.dataframe(week_counts, width="stretch", hide_index=True, column_config={
            "Revenue": st.column_config.NumberColumn("Revenue", format="$%.2f"),
            "Lbs": st.column_config.NumberColumn("Lbs", format="%.1f"),
            "Weighted $/LB": st.column_config.NumberColumn("Weighted $/LB", format="$%.2f"),
        })
    else:
        st.info("No weeks are available to manage.")

with health_tab:
    section("Data Health", "Checks applied to the currently loaded Revenue history.")
    history = load_revenue_history()
    if history.empty:
        st.info("Load Revenue history to run checks.")
    else:
        weight_review = int(history.get("Weight Review", pd.Series(False, index=history.index)).fillna(False).astype(bool).sum())
        zero_lbs = int((pd.to_numeric(history.get("Lbs", 0), errors="coerce").fillna(0) <= 0).sum())
        missing_customer = int(history.get("Customer", pd.Series("", index=history.index)).fillna("").astype(str).str.strip().isin(["", "Unknown", "nan"]).sum())
        missing_channel = int(history.get("Sales Channel", pd.Series("", index=history.index)).fillna("").astype(str).str.strip().isin(["", "Unknown", "nan"]).sum())
        invalid_dates = int(pd.to_datetime(history.get("Date"), errors="coerce").isna().sum())
        duplicate_rows = int(history.duplicated().sum())
        checks = pd.DataFrame({
            "Check": ["Weight review", "Zero pounds", "Missing customer", "Missing channel", "Invalid dates", "Exact duplicate rows"],
            "Rows": [weight_review, zero_lbs, missing_customer, missing_channel, invalid_dates, duplicate_rows],
        })
        checks["Status"] = checks["Rows"].map(lambda x: "Pass" if x == 0 else "Review")
        st.dataframe(checks, width="stretch", hide_index=True)

footer()
