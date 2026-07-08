import streamlit as st
import pandas as pd
import plotly.express as px

from utils.cleaner import clean_uploaded_ar_report, convert_df_to_excel, convert_df_to_csv


st.set_page_config(
    page_title="Groundwork Finance Portal",
    page_icon="☕",
    layout="wide"
)


# -----------------------------
# Helper functions
# -----------------------------
def money(value):
    try:
        return "${:,.2f}".format(float(value))
    except Exception:
        return "$0.00"


def safe_sum(df, column):
    if column not in df.columns:
        return 0
    return pd.to_numeric(df[column], errors="coerce").fillna(0).sum()


def find_amount_column(df):
    preferred = ["Open Balance", "Amount (Gross)", "Amount", "Balance"]
    for col in preferred:
        if col in df.columns:
            return col
    return None


def get_customer_column(df):
    preferred = ["Reporting Customer", "Parent Customer/Project: Company Name", "Customer"]
    for col in preferred:
        if col in df.columns:
            return col
    return None


def clean_customer_display(value):
    text = str(value).strip()
    if text.lower() in ["none", "nan", ""]:
        return "Unknown"

    # Remove leading customer number such as CX111119, C12345, or similar.
    parts = text.split()
    if parts and (parts[0].upper().startswith("CX") or parts[0].upper().startswith("C")):
        if any(char.isdigit() for char in parts[0]):
            text = " ".join(parts[1:]).strip()

    return text if text else "Unknown"


def build_customer_display(df):
    df = df.copy()

    parent_col = "Parent Customer/Project: Company Name"
    customer_col = "Customer"
    reporting_col = "Reporting Customer"

    if reporting_col in df.columns:
        base = df[reporting_col]
    elif parent_col in df.columns:
        base = df[parent_col]
    elif customer_col in df.columns:
        base = df[customer_col]
    else:
        return pd.Series(["Unknown"] * len(df), index=df.index)

    display = base.astype(str)

    # If parent/reporting customer is None, use Customer column and strip customer number.
    if customer_col in df.columns:
        none_mask = display.str.strip().str.lower().isin(["none", "nan", ""])
        display.loc[none_mask] = df.loc[none_mask, customer_col].astype(str)

    return display.apply(clean_customer_display)


def prepare_dashboard_df(df):
    df = df.copy()

    amount_col = find_amount_column(df)

    if amount_col:
        df[amount_col] = pd.to_numeric(df[amount_col], errors="coerce").fillna(0)

    if "Age" in df.columns:
        df["Age"] = pd.to_numeric(df["Age"], errors="coerce").fillna(0)

    if "Transaction Type Clean" not in df.columns:
        if "Transaction Type" in df.columns:
            df["Transaction Type Clean"] = df["Transaction Type"]
        else:
            df["Transaction Type Clean"] = ""

    if "Transaction Reason" not in df.columns:
        df["Transaction Reason"] = ""

    if "Memo" not in df.columns:
        df["Memo"] = ""

    df["Customer Display"] = build_customer_display(df)

    return df, amount_col


def aging_bucket_totals(df, amount_col):
    if "Bucket" not in df.columns or not amount_col:
        return pd.DataFrame()

    bucket_order = ["Current", "1-14", "15-30", "31-60", "61-90", "91+"]
    out = (
        df.groupby("Bucket", dropna=False)[amount_col]
        .sum()
        .reindex(bucket_order)
        .fillna(0)
        .reset_index()
    )
    out.columns = ["Bucket", "Amount"]
    return out


def format_number(value):
    try:
        value = float(value)
        if value < 0:
            return f"({abs(value):,.0f})"
        return f"{value:,.0f}"
    except Exception:
        return ""


def aging_matrix(df, group_col, amount_col):
    if group_col not in df.columns or "Bucket" not in df.columns or not amount_col:
        return pd.DataFrame()

    bucket_order = ["Current", "1-14", "15-30", "31-60", "61-90", "91+"]

    matrix = pd.pivot_table(
        df,
        index=group_col,
        columns="Bucket",
        values=amount_col,
        aggfunc="sum",
        fill_value=0,
        margins=False,
    )

    for bucket in bucket_order:
        if bucket not in matrix.columns:
            matrix[bucket] = 0

    matrix = matrix[bucket_order]
    matrix["Grand Total"] = matrix.sum(axis=1)
    matrix = matrix.sort_values("Grand Total", ascending=False)

    total_row = pd.DataFrame(matrix.sum(axis=0)).T
    total_row.index = ["Grand Total"]
    matrix = pd.concat([matrix, total_row])

    matrix = matrix.reset_index().rename(columns={group_col: group_col})

    for col in bucket_order + ["Grand Total"]:
        matrix[col] = matrix[col].apply(format_number)

    return matrix


def chargeback_df(df):
    return df[df["Transaction Type Clean"].astype(str).str.lower() == "chargeback"].copy()


def holdback_df(df):
    memo_has_holdback = df["Memo"].astype(str).str.lower().str.contains("holdback", na=False) if "Memo" in df.columns else False
    return df[
        (df["Transaction Reason"].astype(str).str.lower() == "holdback")
        | (
            (df["Transaction Type Clean"].astype(str).str.lower() == "invoice")
            & memo_has_holdback
        )
    ].copy()


def apply_filters(df):
    st.sidebar.markdown("## Filters")

    filtered = df.copy()

    customers = sorted(filtered["Customer Display"].dropna().unique())
    selected_customers = st.sidebar.multiselect("Customer", customers)

    if "Sales Channel: Name" in filtered.columns:
        channels = sorted(filtered["Sales Channel: Name"].dropna().unique())
        selected_channels = st.sidebar.multiselect("Sales Channel", channels)
    else:
        selected_channels = []

    if "Sales Rep: Name" in filtered.columns:
        reps = sorted(filtered["Sales Rep: Name"].dropna().unique())
        selected_reps = st.sidebar.multiselect("Sales Rep", reps)
    else:
        selected_reps = []

    if "Terms: Name" in filtered.columns:
        terms = sorted(filtered["Terms: Name"].fillna("Blank").astype(str).unique())
        selected_terms = st.sidebar.multiselect("Terms", terms)
    else:
        selected_terms = []

    if "Bucket" in filtered.columns:
        buckets = ["Current", "1-14", "15-30", "31-60", "61-90", "91+"]
        selected_buckets = st.sidebar.multiselect("Bucket", buckets)
    else:
        selected_buckets = []

    if selected_customers:
        filtered = filtered[filtered["Customer Display"].isin(selected_customers)]

    if selected_channels and "Sales Channel: Name" in filtered.columns:
        filtered = filtered[filtered["Sales Channel: Name"].isin(selected_channels)]

    if selected_reps and "Sales Rep: Name" in filtered.columns:
        filtered = filtered[filtered["Sales Rep: Name"].isin(selected_reps)]

    if selected_terms and "Terms: Name" in filtered.columns:
        filtered = filtered[filtered["Terms: Name"].fillna("Blank").astype(str).isin(selected_terms)]

    if selected_buckets and "Bucket" in filtered.columns:
        filtered = filtered[filtered["Bucket"].isin(selected_buckets)]

    return filtered


def show_admin_tab():
    st.subheader("Admin")
    st.caption("Upload raw NetSuite AR data, download cleaned reports, and validate columns.")

    uploaded_file = st.file_uploader(
        "Upload raw NetSuite AR report",
        type=["csv", "xlsx", "xls"],
        key="admin_ar_upload"
    )

    if uploaded_file is None:
        st.info("Upload the raw AR report here to load the dashboard.")
        return None

    try:
        cleaned_df = clean_uploaded_ar_report(uploaded_file)
    except Exception as e:
        st.error(f"Could not clean the uploaded file: {e}")
        return None

    st.success("File uploaded and cleaned successfully.")

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="Download Cleaned Excel",
            data=convert_df_to_excel(cleaned_df),
            file_name="cleaned_ar_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    with col2:
        st.download_button(
            label="Download Cleaned CSV",
            data=convert_df_to_csv(cleaned_df),
            file_name="cleaned_ar_report.csv",
            mime="text/csv"
        )

    st.markdown("### Cleaned Data Preview")
    st.dataframe(cleaned_df, use_container_width=True, hide_index=True)

    st.markdown("### Column Check")
    st.write(list(cleaned_df.columns))

    return cleaned_df


# -----------------------------
# App layout
# -----------------------------
st.title("☕ Groundwork Finance Portal")
st.caption("AR Aging, Chargebacks, Holdbacks, and Customer Health")

tab_exec, tab_aging, tab_cb, tab_customer, tab_data, tab_admin = st.tabs([
    "Executive",
    "Aging",
    "Chargebacks",
    "Customer Health",
    "Data",
    "Admin"
])

with tab_admin:
    uploaded_cleaned_df = show_admin_tab()
    if uploaded_cleaned_df is not None:
        st.session_state["cleaned_ar_df"] = uploaded_cleaned_df

if "cleaned_ar_df" not in st.session_state:
    with tab_exec:
        st.info("Go to the Admin tab and upload the raw NetSuite AR report to begin.")
    st.stop()

cleaned_df = st.session_state["cleaned_ar_df"]
df, amount_col = prepare_dashboard_df(cleaned_df)

if not amount_col:
    with tab_exec:
        st.error("Could not find an amount column. Expected one of: Open Balance, Amount (Gross), Amount, Balance.")
    st.stop()

filtered = apply_filters(df)


# -----------------------------
# Executive tab
# -----------------------------
with tab_exec:
    st.subheader("Executive AR Overview")

    total_ar = safe_sum(filtered, amount_col)

    current_ar = 0
    past_due_ar = 0
    if "Bucket" in filtered.columns:
        current_ar = safe_sum(filtered[filtered["Bucket"] == "Current"], amount_col)
        past_due_ar = safe_sum(filtered[filtered["Bucket"] != "Current"], amount_col)

    cb_total = safe_sum(chargeback_df(filtered), amount_col)
    hb_total = safe_sum(holdback_df(filtered), amount_col)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total AR", money(total_ar))
    col2.metric("Current AR", money(current_ar))
    col3.metric("Past Due AR", money(past_due_ar))
    col4.metric("Chargebacks", money(cb_total))
    col5.metric("Holdbacks", money(hb_total))

    st.divider()

    left, right = st.columns(2)

    with left:
        st.markdown("### Aging by Bucket")
        aging_totals = aging_bucket_totals(filtered, amount_col)
        if not aging_totals.empty:
            fig = px.bar(aging_totals, x="Bucket", y="Amount", text_auto=".2s")
            st.plotly_chart(fig, use_container_width=True, key="exec_aging_bucket")
        else:
            st.warning("Bucket column not available.")

    with right:
        st.markdown("### Top 10 Customers by Open AR")
        top_customers = (
            filtered.groupby("Customer Display")[amount_col]
            .sum()
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
        )
        fig = px.bar(top_customers, x=amount_col, y="Customer Display", orientation="h", text_auto=".2s")
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True, key="exec_top_customers")


# -----------------------------
# Aging tab
# -----------------------------
with tab_aging:
    st.subheader("AR Aging")

    st.markdown("### Aging by Bucket")
    aging_totals = aging_bucket_totals(filtered, amount_col)
    if not aging_totals.empty:
        st.dataframe(
            aging_totals.assign(Amount=aging_totals["Amount"].map(money)),
            use_container_width=True,
            hide_index=True
        )

    st.markdown("### Aging by Channel by Bucket")
    if "Sales Channel: Name" in filtered.columns:
        channel_matrix = aging_matrix(filtered, "Sales Channel: Name", amount_col)
        st.dataframe(channel_matrix, use_container_width=True, hide_index=True)
    else:
        st.warning("Sales Channel: Name column not available.")

    st.markdown("### Aging by Terms by Bucket")
    if "Terms: Name" in filtered.columns:
        terms_matrix = aging_matrix(filtered, "Terms: Name", amount_col)
        st.dataframe(terms_matrix, use_container_width=True, hide_index=True)
    else:
        st.warning("Terms: Name column not available.")

    st.markdown("### Transactions")
    st.dataframe(filtered, use_container_width=True, hide_index=True)


# -----------------------------
# Chargebacks tab
# -----------------------------
with tab_cb:
    st.subheader("Chargeback Dashboard")

    cb = chargeback_df(filtered)

    if cb.empty:
        st.info("No chargebacks found in the current filtered data.")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Chargebacks", money(safe_sum(cb, amount_col)))
        col2.metric("Chargeback Count", f"{len(cb):,}")
        col3.metric("Avg Chargeback", money(safe_sum(cb, amount_col) / max(len(cb), 1)))

        left, right = st.columns(2)

        with left:
            st.markdown("### By Reason")
            by_reason = (
                cb.groupby("Transaction Reason")[amount_col]
                .sum()
                .sort_values(ascending=False)
                .reset_index()
            )
            fig = px.bar(by_reason, x=amount_col, y="Transaction Reason", orientation="h", text_auto=".2s")
            fig.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, use_container_width=True, key="chargeback_reason")

        with right:
            st.markdown("### By Customer")
            by_customer = (
                cb.groupby("Customer Display")[amount_col]
                .sum()
                .sort_values(ascending=False)
                .head(10)
                .reset_index()
            )
            fig = px.bar(by_customer, x=amount_col, y="Customer Display", orientation="h", text_auto=".2s")
            fig.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, use_container_width=True, key="chargeback_customer")

        st.markdown("### Chargeback Detail")
        st.dataframe(cb, use_container_width=True, hide_index=True)


# -----------------------------
# Customer Health tab
# -----------------------------
with tab_customer:
    st.subheader("Customer Health")

    customer_list = sorted(filtered["Customer Display"].dropna().unique())

    if not customer_list:
        st.info("No customers available with the current filters.")
    else:
        selected_customer = st.selectbox("Select Customer", customer_list)

        customer_df = filtered[filtered["Customer Display"] == selected_customer].copy()
        customer_cb = chargeback_df(customer_df)
        customer_hb = holdback_df(customer_df)

        customer_total = safe_sum(customer_df, amount_col)
        customer_current = safe_sum(customer_df[customer_df["Bucket"] == "Current"], amount_col) if "Bucket" in customer_df.columns else 0
        customer_past_due = customer_total - customer_current

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Open AR", money(customer_total))
        c2.metric("Current", money(customer_current))
        c3.metric("Past Due", money(customer_past_due))
        c4.metric("Chargebacks", money(safe_sum(customer_cb, amount_col)))
        c5.metric("Holdbacks", money(safe_sum(customer_hb, amount_col)))

        left, right = st.columns(2)

        with left:
            st.markdown("### Customer Aging")
            customer_aging = aging_bucket_totals(customer_df, amount_col)
            if not customer_aging.empty:
                fig = px.bar(customer_aging, x="Bucket", y="Amount", text_auto=".2s")
                st.plotly_chart(fig, use_container_width=True, key="customer_aging")

        with right:
            st.markdown("### Chargebacks by Reason")
            if customer_cb.empty:
                st.info("No chargebacks for this customer.")
            else:
                reason_chart = (
                    customer_cb.groupby("Transaction Reason")[amount_col]
                    .sum()
                    .sort_values(ascending=False)
                    .reset_index()
                )
                fig = px.bar(reason_chart, x=amount_col, y="Transaction Reason", orientation="h", text_auto=".2s")
                fig.update_layout(yaxis={"categoryorder": "total ascending"})
                st.plotly_chart(fig, use_container_width=True, key="customer_reason")

        st.markdown("### Customer Transactions")
        st.dataframe(customer_df, use_container_width=True, hide_index=True)


# -----------------------------
# Data tab
# -----------------------------
with tab_data:
    st.subheader("Cleaned Data Preview")
    st.dataframe(filtered, use_container_width=True, hide_index=True)

    st.markdown("### Column Check")
    st.write(list(filtered.columns))
