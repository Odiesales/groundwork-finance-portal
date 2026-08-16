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
from pathlib import Path
import calendar


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
    c2.metric("Periods Loaded", f"{len(weeks):,}")
    c3.metric("Revenue", format_money(history["Revenue"].sum()))

    # Use the reconciled pounds methodology only. Never use the legacy Lbs column
    # as package weight because it may already contain calculated pounds.
    required_pricing = {"Size in Pounds", "Sum of Quantity", "Sales Channel"}
    if required_pricing.issubset(history.columns):
        size_lbs = pd.to_numeric(history["Size in Pounds"], errors="coerce").fillna(0).abs()
        qty = pd.to_numeric(history["Sum of Quantity"], errors="coerce").fillna(0).abs()
        if "Sum of # of Units" in history.columns:
            units = pd.to_numeric(history["Sum of # of Units"], errors="coerce").fillna(1).abs()
            units = units.where(units > 0, 1.0)
        else:
            units = pd.Series(1.0, index=history.index)
        channel = history["Sales Channel"].fillna("").astype(str).str.lower()
        grocery = channel.str.contains("grocery", na=False)
        foodservice = channel.str.contains(r"foodservice|food service", regex=True, na=False)
        wholesale = grocery | foodservice
        calc_lbs = pd.Series(0.0, index=history.index)
        calc_lbs.loc[grocery] = (qty * units * size_lbs).loc[grocery]
        calc_lbs.loc[foodservice] = (qty * size_lbs).loc[foodservice]
        eligible = wholesale & size_lbs.gt(0) & calc_lbs.gt(0)
        eligible_lbs = calc_lbs.where(eligible, 0).sum()
        revenue_series = pd.to_numeric(history.get("Revenue", 0), errors="coerce").fillna(0)
        eligible_revenue = revenue_series.where(eligible, 0).sum()
        c4.metric("Weighted $/LB", format_money(eligible_revenue / eligible_lbs if eligible_lbs else 0, 2))
    else:
        c4.metric("Weighted $/LB", "N/M")

rev_file = st.file_uploader("Upload Revenue export", type=["xlsx", "xls", "csv"], key="rev_upload")
if rev_file:
    try:
        rev_df = clean_uploaded_revenue_report(rev_file)
        if "Size in Pounds" not in rev_df.columns:
            raise ValueError(
                "This Revenue export does not contain 'Size in Pounds'. Use the full Revenue Analysis export "
                "with Size in Pounds so the portal can calculate wholesale $/LB accurately."
            )
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
        st.dataframe(rev_df.head(300), use_container_width=True, hide_index=True)
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
    st.dataframe(revenue_week_table(history), use_container_width=True, hide_index=True, column_config={
        "Revenue": st.column_config.NumberColumn("Revenue", format="$%,.2f"),
        "Lbs": st.column_config.NumberColumn("Lbs", format="%.1f"),
        "Weighted $/LB": st.column_config.NumberColumn("Weighted $/LB", format="$%,.2f"),
    })
else:
    st.info("No weeks are available to manage.")


st.divider()
section(
    "Month-End AR Aging — DSO",
    "Upload one exact month-end AR Aging snapshot per month. These snapshots are used only for the Monthly DSO schedule."
)

AR_DSO_DIR = Path("data") / "ar_month_end"
AR_DSO_DIR.mkdir(parents=True, exist_ok=True)

ar_file = st.file_uploader(
    "Upload Month-End AR Aging",
    type=["xlsx", "xls", "csv"],
    key="ar_eom_upload",
    help="Use the AR Aging as of the exact calendar month-end (for example, 07/31/2026).",
)
ar_as_of = st.date_input("Aging As-of Date", key="ar_eom_as_of")

last_day = calendar.monthrange(ar_as_of.year, ar_as_of.month)[1]
is_month_end = ar_as_of.day == last_day

if not is_month_end:
    st.warning(
        f"DSO requires an exact month-end snapshot. "
        f"{ar_as_of:%B %Y} month-end is {ar_as_of.replace(day=last_day):%m/%d/%Y}."
    )

if ar_file is not None:
    st.info(
        "This snapshot will be retained for Monthly DSO. "
        "Only Foodservice Direct, Foodservice Distributor, Grocery Direct, and Grocery Distributor "
        "will be used in the DSO calculation."
    )

    save_ar = st.button(
        "Save Month-End AR Snapshot",
        type="primary",
        disabled=not is_month_end,
    )

    if save_ar:
        suffix = Path(ar_file.name).suffix.lower()
        snapshot_name = f"ar_aging_{ar_as_of:%Y-%m-%d}{suffix}"
        snapshot_path = AR_DSO_DIR / snapshot_name
        snapshot_path.write_bytes(ar_file.getvalue())

        try:
            upload_drive_file(
                snapshot_path,
                "revenue",
                f"ar_month_end/{snapshot_name}",
            )
            st.success(
                f"Month-end AR Aging saved for {ar_as_of:%m/%d/%Y} and uploaded to Google Drive."
            )
        except Exception as exc:
            st.error(
                f"AR snapshot saved locally, but Google Drive upload failed: {exc}"
            )

saved_snapshots = sorted(AR_DSO_DIR.glob("ar_aging_*"), reverse=True)
if saved_snapshots:
    st.caption("Saved Month-End AR Snapshots")
    snapshot_rows = []
    for p in saved_snapshots:
        snapshot_rows.append({
            "Snapshot": p.name,
            "Stored File": str(p),
        })
    st.dataframe(
        pd.DataFrame(snapshot_rows),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No month-end AR Aging snapshots are currently saved.")

footer()
