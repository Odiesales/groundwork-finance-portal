from __future__ import annotations

import html
import pandas as pd
import plotly.express as px
import streamlit as st

from utils.data import prep_ar
from utils.paths import AR_SNAPSHOT_DIR, CURRENT_AR_PATH
from utils.ui import apply_multiselect_filter, footer, page_header

BUCKET_ORDER = ["Current", "1-14", "15-30", "31-60", "61-90", "91+"]
PAST_DUE_BUCKETS = ["1-14", "15-30", "31-60", "61-90", "91+"]
OVER_60_BUCKETS = ["61-90", "91+"]
OVER_90_BUCKETS = ["91+"]

# Local report components preserve the detailed AR workflow while the app shell stays shared.
st.markdown("""<style>
.section-card{background:#fff;border:1px solid #D8D1C5;border-radius:14px;padding:22px;margin:26px 0 0;box-shadow:0 7px 22px rgba(37,46,39,.04)}
.section-title{font-size:1.72rem;line-height:1.2;font-weight:900;color:#0B4A3A}.section-note{font-size:1rem;line-height:1.4;color:#596057;margin:6px 0 18px}
.kpi-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.kpi-card{background:#fff;border:1px solid #D8D1C5;border-left:4px solid #E6B92F;border-radius:11px;padding:18px 18px;min-height:116px}.kpi-label{color:#5B6259;font-size:.88rem;font-weight:800}.kpi-value{color:#22251F;font-size:2rem;line-height:1.12;font-weight:900;margin-top:8px;white-space:nowrap}
.report-table-wrap{overflow:auto;border:1px solid #E3DDD2;border-radius:10px;background:#fff}table.report-table{border-collapse:collapse;width:100%;min-width:900px;font-size:.79rem;color:#22251F}table.report-table th{position:sticky;top:0;z-index:1;background:#EEE9DF;color:#22251F;font-weight:800;text-align:left;padding:9px 10px;border-bottom:1px solid #D8D1C5;white-space:nowrap}table.report-table td{background:#fff;color:#22251F;padding:8px 10px;border-bottom:1px solid #ECE7DF;white-space:nowrap}table.report-table tr:nth-child(even) td{background:#FCFAF7}table.report-table td.num,table.report-table th.num{text-align:right;font-variant-numeric:tabular-nums}.badge-red{color:#B42318;font-weight:800}.badge-green{color:#067647;font-weight:800}.badge-amber{color:#B54708;font-weight:800}.terms-heading{font-size:1.8rem;line-height:1.2;font-weight:900;color:#0B4A3A;margin:30px 0 14px}.terms-heading.credit-card{color:#D96B00}.empty-box{background:#EDF7ED;color:#286B35;padding:12px 14px;border-radius:8px;font-weight:650}@media(max-width:900px){.kpi-grid{grid-template-columns:1fr}.section-title{font-size:1.45rem}.terms-heading{font-size:1.5rem}.kpi-value{font-size:1.72rem}}

/* Make "Rank Top 25 by" selectbox have WHITE background + dark text */
div[data-testid="stSelectbox"] {
    background-color: #ffffff !important;
    border-radius: 8px !important;
}

div[data-testid="stSelectbox"] label,
.stSelectbox label {
    color: #22251F !important;   /* dark text */
    font-weight: 700 !important;
}

/* Style the dropdown box itself */
div[data-testid="stSelectbox"] > div {
    background-color: #ffffff !important;
    border: 1px solid #D8D1C5 !important;
}
</style>""", unsafe_allow_html=True)

def money(value):
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def safe_text(series, default=""):
    if not isinstance(series, pd.Series):
        return pd.Series(default, index=[])
    return series.fillna(default).astype(str).str.strip()


def first_nonblank(series):
    values = safe_text(series)
    values = values[~values.eq("")]
    return values.iloc[0] if not values.empty else "—"


def parse_snapshot_date(path):
    raw = path.stem.replace("ar_", "").replace("_", "-")
    parsed = pd.to_datetime(raw, errors="coerce")
    return None if pd.isna(parsed) else parsed


def snapshot_options():
    options = {}
    dated = []
    for path in AR_SNAPSHOT_DIR.glob("ar_*.csv"):
        date = parse_snapshot_date(path)
        if date is not None:
            dated.append((date, path))
    dated.sort(reverse=True)
    if CURRENT_AR_PATH.exists():
        current_date = dated[0][0] if dated else pd.Timestamp.fromtimestamp(CURRENT_AR_PATH.stat().st_mtime)
        options[f"As of {current_date.strftime('%m/%d/%y')}"] = CURRENT_AR_PATH
    for snapshot_date, path in dated:
        options.setdefault(f"As of {snapshot_date.strftime('%m/%d/%y')}", path)
    return options


def date_display(value):
    date = pd.to_datetime(value, errors="coerce")
    return "—" if pd.isna(date) else date.strftime("%m/%d/%y")


def section_start(title, note=""):
    st.markdown(
        f'<div class="section-card"><div class="section-title">{html.escape(title)}</div>'
        f'<div class="section-note">{html.escape(note)}</div>',
        unsafe_allow_html=True,
    )


def section_end():
    st.markdown('</div>', unsafe_allow_html=True)


def render_table(df, money_cols=None, integer_cols=None, max_height=560):
    """Render an interactive, sortable Streamlit table with finance formatting."""
    money_cols = set(money_cols or [])
    integer_cols = set(integer_cols or [])
    if df.empty:
        st.markdown('<div class="empty-box">No records found for the selected filters.</div>', unsafe_allow_html=True)
        return

    display = df.copy()
    column_config = {}
    for col in display.columns:
        if col in money_cols:
            display[col] = pd.to_numeric(display[col], errors="coerce").fillna(0.0)
            column_config[col] = st.column_config.NumberColumn(col, format="$%.2f")
        elif col in integer_cols:
            display[col] = pd.to_numeric(display[col], errors="coerce").fillna(0).astype(int)
            column_config[col] = st.column_config.NumberColumn(col, format="%d")

    def highlight_status(value):
        text = str(value)
        if text in {"Yes", "High Priority"}:
            return "color:#B42318;font-weight:800"
        if text == "No" or text == "Monitor":
            return "color:#067647;font-weight:800"
        if "Review" in text:
            return "color:#B54708;font-weight:800"
        return ""

    styler = display.style
    for col in ["Suggested Hold", "Priority"]:
        if col in display.columns:
            styler = styler.map(highlight_status, subset=[col])

    st.dataframe(
        styler,
        width='stretch',
        hide_index=True,
        height=min(max_height, max(120, 38 * (len(display) + 1))),
        column_config=column_config,
    )


options = snapshot_options()
if not options:
    st.info("Upload and save an AR snapshot in Admin first.")
    st.stop()

selected = st.sidebar.selectbox("As of Date", list(options.keys()))
selected_as_of = selected.replace("As of ", "")

page_header(
    "Accounts Receivable",
    f"AR aging, collection priorities, chargebacks, and customer exposure as of {selected_as_of}.",
    snapshot_date=pd.to_datetime(selected_as_of, errors="coerce"),
)

raw_df = prep_ar(pd.read_csv(options[selected]))
channel_col = "Channel Clean" if "Channel Clean" in raw_df.columns else "Sales Channel: Name"
df = raw_df.copy()

st.sidebar.markdown("## AR Filters")
for label, col in [
    ("Customer", "Reporting Customer"), ("Channel", channel_col),
    ("Sales Rep", "Sales Rep: Name"), ("Terms", "Terms: Name"),
    ("Bucket", "Bucket"), ("Transaction Type", "Transaction Type"),
    ("Deduction Type", "Deduction Type"),
]:
    df = apply_multiselect_filter(df, label, col)

search = st.sidebar.text_input("Search customer / memo / document")
if search:
    value = search.lower().strip()
    mask = pd.Series(False, index=df.index)
    for col in ["Reporting Customer", "Memo", "Document Number", "P.O. No."]:
        if col in df.columns:
            mask |= df[col].fillna("").astype(str).str.lower().str.contains(value, regex=False)
    df = df[mask]

for col in ["Open Balance", "Age"]:
    if col not in df.columns:
        df[col] = 0
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
for col, default in [
    ("Transaction Type", ""), ("Deduction Type", ""), ("Terms: Name", "—"),
    ("Sales Rep: Name", "—"), ("Reporting Customer", "Unknown"), ("Bucket", "Unknown"),
]:
    if col not in df.columns:
        df[col] = default
    df[col] = df[col].fillna(default).astype(str).str.strip()

# Normalize source labels so aging and transaction logic remain reliable across exports.
df["Bucket"] = (
    df["Bucket"].astype(str).str.strip()
    .str.replace(r"^91\+.*$", "91+", regex=True)
    .str.replace(r"^61\s*[-–]\s*90.*$", "61-90", regex=True)
    .str.replace(r"^31\s*[-–]\s*60.*$", "31-60", regex=True)
    .str.replace(r"^15\s*[-–]\s*30.*$", "15-30", regex=True)
    .str.replace(r"^1\s*[-–]\s*14.*$", "1-14", regex=True)
    .str.replace(r"^Current.*$", "Current", regex=True, case=False)
)
df["Transaction Type Normalized"] = df["Transaction Type"].astype(str).str.strip().str.casefold()
df["Deduction Type Normalized"] = df["Deduction Type"].astype(str).str.strip().str.casefold()

if "Due Date" in df.columns:
    df["Due Date Parsed"] = pd.to_datetime(df["Due Date"], errors="coerce")
else:
    df["Due Date Parsed"] = pd.NaT

is_chargeback = df["Transaction Type Normalized"].str.contains("chargeback", na=False)
is_credit = df["Transaction Type Normalized"].str.contains("credit", na=False)
is_payment = df["Transaction Type Normalized"].str.contains("payment", na=False)
is_holdback = df["Deduction Type Normalized"].eq("holdback")
# Treat remaining open AR rows as invoices; this is more reliable across NetSuite export labels.
is_invoice = ~(is_chargeback | is_credit | is_payment)
is_recovery = df["Deduction Type Normalized"].isin({"duplicate pmt", "overpayment", "pmt transfer", "on account payment (oap)"})

invoice_rows = df[is_invoice & ~is_holdback].copy()
chargeback_rows = df[is_chargeback].copy()
recovery_rows = df[is_chargeback & is_recovery].copy()

total_ar = df["Open Balance"].sum()
past_due = invoice_rows.loc[invoice_rows["Bucket"].isin(PAST_DUE_BUCKETS), "Open Balance"].sum()
over_90 = invoice_rows.loc[invoice_rows["Bucket"].isin(OVER_90_BUCKETS), "Open Balance"].sum()
chargebacks = chargeback_rows["Open Balance"].sum()
cb_recoveries = abs(recovery_rows["Open Balance"].sum())
hold_source = invoice_rows[invoice_rows["Bucket"].isin(OVER_60_BUCKETS) & (invoice_rows["Open Balance"] > 0)]
hold_customer_count = hold_source["Reporting Customer"].nunique()

section_start("Executive Summary", "Key AR exposure and collection-risk indicators for the selected snapshot.")
st.markdown(
    '<div class="kpi-grid">' + ''.join([
        f'<div class="kpi-card"><div class="kpi-label">Total AR</div><div class="kpi-value">{money(total_ar)}</div></div>',
        f'<div class="kpi-card"><div class="kpi-label">Past Due</div><div class="kpi-value">{money(past_due)}</div></div>',
        f'<div class="kpi-card"><div class="kpi-label">Invoice 90+</div><div class="kpi-value">{money(over_90)}</div></div>',
        f'<div class="kpi-card"><div class="kpi-label">Suggested Holds</div><div class="kpi-value">{hold_customer_count:,}</div></div>',
        f'<div class="kpi-card"><div class="kpi-label">Open Chargebacks</div><div class="kpi-value">{money(chargebacks)}</div></div>',
        f'<div class="kpi-card"><div class="kpi-label">CB Recoveries</div><div class="kpi-value">{money(cb_recoveries)}</div></div>',
    ]) + '</div>',
    unsafe_allow_html=True,
)
section_end()

records = []
for customer, group in df.groupby("Reporting Customer", dropna=False):
    inv = group[(~group["Transaction Type Normalized"].str.contains("chargeback|credit|payment", regex=True, na=False)) & ~group["Deduction Type Normalized"].eq("holdback")].copy()
    cb = group[group["Transaction Type Normalized"].str.contains("chargeback", na=False)].copy()
    positive_inv = inv[inv["Open Balance"] > 0]
    past_due_balance = inv.loc[inv["Bucket"].isin(PAST_DUE_BUCKETS), "Open Balance"].sum()
    bal_60 = inv.loc[inv["Bucket"].isin(OVER_60_BUCKETS), "Open Balance"].sum()
    bal_90 = inv.loc[inv["Bucket"].isin(OVER_90_BUCKETS), "Open Balance"].sum()
    oldest_age = int(positive_inv["Age"].max()) if not positive_inv.empty else 0
    next_due = positive_inv["Due Date Parsed"].min() if not positive_inv.empty else pd.NaT
    suggested_hold = bal_60 > 0
    if suggested_hold or past_due_balance > 0:
        priority, reason = "High Priority", ("Invoice(s) over 60 days" if suggested_hold else "Past-due invoice balance")
    elif cb["Open Balance"].sum() > 0:
        priority, reason = "Review CB", "Open chargeback balance"
    else:
        priority, reason = "Monitor", "No immediate collection risk"
    records.append({
        "Customer": customer, "Total AR": group["Open Balance"].sum(), "Past Due": past_due_balance,
        "60+": bal_60, "90+": bal_90, "Chargebacks": cb["Open Balance"].sum(),
        "Oldest Invoice Days": oldest_age, "Next Due Date": date_display(next_due),
        "Terms": first_nonblank(group["Terms: Name"]), "Sales Rep": first_nonblank(group["Sales Rep: Name"]),
        "Suggested Hold": "Yes" if suggested_hold else "No", "Status": "—", "Priority": priority, "Reason": reason,
    })
customer_summary = pd.DataFrame(records)

section_start("1. Top 25 Customer Exposure", "Customers ranked by the selected exposure measure.")
sort_choice = st.selectbox("Rank Top 25 by", ["Past Due", "Total AR", "60+", "90+", "Chargebacks"], index=0)
top_25 = customer_summary.sort_values(sort_choice, ascending=False).head(25)[[
    "Customer", "Total AR", "Past Due", "60+", "90+", "Chargebacks", "Terms", "Sales Rep", "Suggested Hold", "Status", "Priority"
]]
render_table(top_25, money_cols=["Total AR", "Past Due", "60+", "90+", "Chargebacks"], max_height=760)
section_end()

section_start("2. Terms Priority", "Accounts requiring attention based on 5th MFI, 10th MFI, or credit-card terms.")

def terms_queue(title, pattern, regex=False):
    heading_class = "terms-heading credit-card" if title == "Credit Card Accounts" else "terms-heading"
    st.markdown(f'<div class="{heading_class}">{html.escape(title)}</div>', unsafe_allow_html=True)
    mask = customer_summary["Terms"].fillna("").str.contains(pattern, case=False, na=False, regex=regex)
    table = customer_summary[mask & (customer_summary["Total AR"] != 0)].sort_values(["Past Due", "Total AR"], ascending=False)
    table = table[["Customer", "Next Due Date", "Total AR", "Past Due", "Oldest Invoice Days", "Sales Rep", "Priority"]].head(50)
    render_table(table, money_cols=["Total AR", "Past Due"], integer_cols=["Oldest Invoice Days"], max_height=430)

terms_queue("5th MFI Auto-Debit", "5th MFI")
terms_queue("10th MFI Auto-Debit", "10th MFI")
terms_queue("Credit Card Accounts", r"\bCC\b|Credit Card", regex=True)
section_end()

hold_table = customer_summary[customer_summary["60+"] > 0].sort_values(["60+", "90+"], ascending=False)
section_start(
    f"3. Suggested Credit Holds ({len(hold_table):,} Customers | {money(hold_table['60+'].sum())} Exposure)",
    "Positive invoice balances in the 61-90 or 91+ buckets. Chargebacks and holdbacks are excluded.",
)
render_table(
    hold_table[["Customer", "60+", "90+", "Past Due", "Oldest Invoice Days", "Terms", "Sales Rep", "Status", "Reason"]].head(50),
    money_cols=["60+", "90+", "Past Due"], integer_cols=["Oldest Invoice Days"], max_height=530,
)
section_end()

collection_table = customer_summary[customer_summary["Past Due"] > 0].sort_values(["Past Due", "90+", "Oldest Invoice Days"], ascending=False)
section_start(
    f"4. Collection Priority ({money(collection_table['Past Due'].sum())} Past Due)",
    "Customers ranked by past-due invoice exposure, 90+ balance, and oldest invoice.",
)
render_table(
    collection_table[["Customer", "Past Due", "60+", "90+", "Oldest Invoice Days", "Terms", "Sales Rep", "Priority"]].head(50),
    money_cols=["Past Due", "60+", "90+"], integer_cols=["Oldest Invoice Days"], max_height=560,
)
section_end()

section_start("5. Chargeback Center", "Open chargebacks, recoveries, and largest chargeback exposures.")
cb_customers = chargeback_rows.groupby("Reporting Customer", dropna=False)["Open Balance"].sum().sort_values(ascending=False).head(25).reset_index()
cb_customers = cb_customers.rename(columns={"Reporting Customer": "Customer", "Open Balance": "Chargebacks"})
render_table(cb_customers, money_cols=["Chargebacks"], max_height=430)
section_end()

section_start("6. Analytics", "Aging distribution by bucket, channel, and payment terms.")
bucket = df.groupby("Bucket")["Open Balance"].sum().reindex(BUCKET_ORDER).fillna(0).reset_index()
fig = px.bar(bucket, x="Bucket", y="Open Balance", text="Open Balance")
fig.update_traces(texttemplate="$%{text:,.2f}", textposition="outside", cliponaxis=False, marker_color="#5B6EF5")
fig.update_layout(
    height=460, margin=dict(l=115, r=35, t=55, b=65), paper_bgcolor="white", plot_bgcolor="white",
    font=dict(size=15, color="#111827"), xaxis_title="Aging Bucket", yaxis_title="Open Balance",
    xaxis=dict(automargin=True, tickfont=dict(size=14, color="#111827"), title_font=dict(size=15, color="#111827"), linecolor="#111827"),
    yaxis=dict(automargin=True, tickfont=dict(size=13, color="#111827"), title_font=dict(size=15, color="#111827"), tickformat="$,.0f", gridcolor="#d7dce3", linecolor="#111827"),
    showlegend=False,
)
st.plotly_chart(fig, width='stretch', theme=None)

st.markdown("### Aging by Channel by Bucket")
channel_matrix = pd.pivot_table(df, index=channel_col, columns="Bucket", values="Open Balance", aggfunc="sum", fill_value=0)
for name in BUCKET_ORDER:
    if name not in channel_matrix.columns: channel_matrix[name] = 0
channel_matrix = channel_matrix[BUCKET_ORDER]
channel_matrix["Grand Total"] = channel_matrix.sum(axis=1)
channel_matrix = channel_matrix.sort_values("Grand Total", ascending=False).reset_index().rename(columns={channel_col: "Channel"})
channel_long = channel_matrix.melt(id_vars=["Channel", "Grand Total"], value_vars=BUCKET_ORDER, var_name="Bucket", value_name="Open Balance")
channel_fig = px.bar(channel_long, x="Channel", y="Open Balance", color="Bucket", category_orders={"Bucket": BUCKET_ORDER})
channel_fig.update_layout(
    height=500, margin=dict(l=115, r=35, t=45, b=105), paper_bgcolor="white", plot_bgcolor="white",
    font=dict(size=14, color="#111827"), barmode="stack", legend_title_text="",
    xaxis=dict(automargin=True, tickangle=-20, tickfont=dict(size=13, color="#111827"), title="Channel"),
    yaxis=dict(automargin=True, tickformat="$,.0f", tickfont=dict(size=13, color="#111827"), title="Open Balance", gridcolor="#d7dce3"),
)
st.plotly_chart(channel_fig, width='stretch', theme=None)
with st.expander("View Channel Aging Detail"):
    render_table(channel_matrix, money_cols=BUCKET_ORDER + ["Grand Total"], max_height=520)

st.markdown("### Aging by Terms by Bucket")
terms_matrix = pd.pivot_table(df, index="Terms: Name", columns="Bucket", values="Open Balance", aggfunc="sum", fill_value=0)
for name in BUCKET_ORDER:
    if name not in terms_matrix.columns: terms_matrix[name] = 0
terms_matrix = terms_matrix[BUCKET_ORDER]
terms_matrix["Grand Total"] = terms_matrix.sum(axis=1)
terms_matrix = terms_matrix.sort_values("Grand Total", ascending=False)
terms_matrix.loc["Grand Total"] = terms_matrix.sum(axis=0)
terms_matrix = terms_matrix.reset_index().rename(columns={"Terms: Name": "Terms"})
render_table(terms_matrix, money_cols=BUCKET_ORDER + ["Grand Total"], max_height=650)
section_end()

with st.expander("Transaction Detail"):
    st.dataframe(df, width='stretch', hide_index=True, height=620)
footer()
