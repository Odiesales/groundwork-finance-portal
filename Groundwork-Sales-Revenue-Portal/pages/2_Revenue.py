from __future__ import annotations

import calendar
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.data import load_revenue_history
from utils.paths import AR_SNAPSHOT_DIR
from utils.ui import (
    apply_multiselect_filter,
    footer,
    format_money,
    format_number,
    metric_row,
    page_header,
    section,
)


page_header(
    "Sales Revenue & DSO",
    "Executive weekly revenue, wholesale $/LB, calendar-month revenue, and trade DSO.",
    badge="Weekly Upload",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.15rem; padding-bottom: 2rem; max-width: 1550px;}
    .gw-note {color:#66736d;font-size:.88rem;margin-top:-.35rem;margin-bottom:.8rem;}
    .gw-grid-wrap {overflow-x:auto; margin: .35rem 0 1.5rem 0; border:1px solid #dfe7e2; border-radius:12px; background:#fff;}
    table.gw-grid {border-collapse:collapse; min-width:100%; width:max-content; font-size:.82rem; color:#202623;}
    .gw-grid th,.gw-grid td {padding:8px 12px; border-right:6px solid #fff; white-space:nowrap; text-align:right;}
    .gw-grid th:first-child,.gw-grid td:first-child {text-align:left; min-width:205px;}
    .gw-grid thead th {background:#111; color:#fff; font-weight:800;}
    .gw-grid tbody tr.metric-row td:first-child {background:#111;color:#fff;font-weight:800;}
    .gw-grid tbody tr.total-row td {background:#111;color:#fff;font-weight:800;}
    .gw-grid tbody tr.dso-total td {background:#176681;color:#fff;font-weight:800;}
    .gw-grid tbody tr.dso-channel td {background:#96440d;color:#fff;font-weight:800;}
    .gw-grid tbody tr.data-row td {background:#fff;}
    .gw-grid .na {color:#8a8a8a;font-style:italic;}
    div[data-testid="stPlotlyChart"] {background:#fff;border:1px solid #e1e8e4;border-radius:12px;padding:.35rem .45rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


TRADE_BUCKETS = [
    "Foodservice Direct",
    "Foodservice Distributor",
    "Grocery Direct",
    "Grocery Distributor",
]


def safe_numeric(frame: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce").fillna(default)


def safe_text(frame: pd.DataFrame, column: str, default: str = "") -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype="object")
    return frame[column].fillna(default).astype(str).str.strip()


def first_column(frame: pd.DataFrame, candidates: list[str]) -> str | None:
    return next((name for name in candidates if name in frame.columns), None)


def trade_bucket(value: object) -> str | None:
    text = str(value).strip().lower()
    if not text or text in {"nan", "none"}:
        return None
    if "foodservice" in text or "food service" in text:
        if "distributor" in text:
            return "Foodservice Distributor"
        if "direct" in text:
            return "Foodservice Direct"
        return "Foodservice Direct"
    if "grocery" in text:
        if "distributor" in text:
            return "Grocery Distributor"
        if "direct" in text:
            return "Grocery Direct"
        return "Grocery Direct"
    return None


def percent_change(current: float, prior: float) -> float | None:
    if prior == 0 or pd.isna(prior):
        return None
    return ((current - prior) / abs(prior)) * 100


def delta_label(current: float, prior: float, label: str = "prior week") -> str:
    change = percent_change(current, prior)
    if change is None:
        return f"No {label} comparison"
    arrow = "▲" if change >= 0 else "▼"
    return f"{arrow} {abs(change):.1f}% vs {label}"


def normalize_revenue(source: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    frame = source.copy()

    date_col = first_column(frame, ["Trend Date", "Date", "Transaction Date"])
    if date_col is None:
        raise ValueError("Revenue history does not contain a usable transaction date column.")
    frame["Report Date"] = pd.to_datetime(frame[date_col], errors="coerce").dt.normalize()
    frame = frame[frame["Report Date"].notna()].copy()

    revenue_col = first_column(frame, ["Revenue", "Sum of Amount (Credit)", "Amount"])
    if revenue_col is None:
        raise ValueError("Revenue history does not contain Revenue or Sum of Amount (Credit).")
    frame["Revenue Calc"] = safe_numeric(frame, revenue_col)

    channel_col = first_column(frame, ["Sales Channel", "Sales Channel 1", "Channel"])
    customer_col = first_column(frame, ["Customer", "Top Level Parent", "Reporting Customer"])
    item_col = first_column(frame, ["Item / Memo", "Memo", "Description"])
    item_class_col = first_column(frame, ["Item Class", "Class"])
    sales_rep_col = first_column(frame, ["Sales Rep", "Sales Rep: Name"])
    document_col = first_column(frame, ["Document Number", "Document", "Transaction Number"])

    frame["Sales Channel Calc"] = safe_text(frame, channel_col or "")
    frame["Customer Calc"] = safe_text(frame, customer_col or "")
    frame["Item Calc"] = safe_text(frame, item_col or "")
    frame["Item Class Calc"] = safe_text(frame, item_class_col or "")
    frame["Sales Rep Calc"] = safe_text(frame, sales_rep_col or "")
    frame["Document Calc"] = safe_text(frame, document_col or "")
    frame["Trade Bucket"] = frame["Sales Channel Calc"].map(trade_bucket)

    # Strict Monday-Sunday reporting calendar.
    frame["Week Start"] = frame["Report Date"] - pd.to_timedelta(frame["Report Date"].dt.weekday, unit="D")
    frame["Week End"] = frame["Week Start"] + pd.Timedelta(days=6)
    frame["Month"] = frame["Report Date"].dt.to_period("M").dt.to_timestamp()

    qty_col = first_column(frame, ["Sum of Quantity", "Quantity"])
    units_col = first_column(frame, ["Sum of # of Units", "# of Units", "Units"])
    qty = safe_numeric(frame, qty_col or "").abs()
    units = safe_numeric(frame, units_col or "", default=1.0).abs()
    units = units.where(units > 0, 1.0)

    # Size in Pounds is authoritative when present. - None -, blank, zero, and
    # nonnumeric values are not eligible for pounds or $/LB.
    has_size_in_pounds = "Size in Pounds" in frame.columns
    if has_size_in_pounds:
        size_lbs = pd.to_numeric(frame["Size in Pounds"], errors="coerce").fillna(0.0).abs()
    else:
        legacy_col = first_column(frame, ["Lbs", "lbs", "lbs (override)"])
        size_lbs = safe_numeric(frame, legacy_col or "").abs()

    is_grocery = frame["Trade Bucket"].isin(["Grocery Direct", "Grocery Distributor"])
    is_foodservice = frame["Trade Bucket"].isin(["Foodservice Direct", "Foodservice Distributor"])
    frame["Calculated Lbs"] = 0.0
    frame.loc[is_grocery, "Calculated Lbs"] = (qty * units * size_lbs)[is_grocery]
    frame.loc[is_foodservice, "Calculated Lbs"] = (qty * size_lbs)[is_foodservice]

    roasted = frame["Item Class Calc"].str.contains(
        r"finished goods\s*:\s*roasted coffee|roasted coffee", case=False, regex=True, na=False
    )
    excluded_customer = frame["Customer Calc"].str.contains(r"sample|employee", case=False, regex=True, na=False)
    trade = frame["Trade Bucket"].notna()
    valid_weight = size_lbs.gt(0) & frame["Calculated Lbs"].gt(0)
    eligible = roasted & trade & (~excluded_customer) & valid_weight

    frame["Eligible Lbs"] = frame["Calculated Lbs"].where(eligible, 0.0)
    frame["Eligible Revenue"] = frame["Revenue Calc"].where(eligible, 0.0)
    frame["Included in $/LB"] = eligible
    frame["Missing Weight Revenue"] = frame["Revenue Calc"].where(roasted & trade & (~excluded_customer) & (~valid_weight), 0.0)
    return frame, has_size_in_pounds


def weekly_summary(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    out = (
        frame.groupby(["Week Start", "Week End"], as_index=False)
        .agg(
            Revenue=("Revenue Calc", "sum"),
            Eligible_Revenue=("Eligible Revenue", "sum"),
            Lbs=("Eligible Lbs", "sum"),
            Orders=("Document Calc", "nunique"),
            Customers=("Customer Calc", "nunique"),
            Missing_Weight_Revenue=("Missing Weight Revenue", "sum"),
        )
        .sort_values("Week Start")
    )
    out["Weighted $/LB"] = out["Eligible_Revenue"].div(out["Lbs"].replace(0, pd.NA)).fillna(0.0)
    out["Week Label"] = out.apply(lambda r: f"{r['Week Start']:%b %d}–{r['Week End']:%b %d}", axis=1)
    return out


def monthly_summary(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    out = (
        frame.groupby("Month", as_index=False)
        .agg(
            Revenue=("Revenue Calc", "sum"),
            Orders=("Document Calc", "nunique"),
            Customers=("Customer Calc", "nunique"),
        )
        .sort_values("Month")
    )
    out["Month Label"] = out["Month"].dt.strftime("%b-%Y")
    out["MoM %"] = out["Revenue"].pct_change() * 100
    return out


def parse_snapshot_date(path: Path) -> pd.Timestamp | None:
    raw = path.stem.replace("ar_", "", 1).replace("_", "-")
    value = pd.to_datetime(raw, errors="coerce")
    return None if pd.isna(value) else pd.Timestamp(value).normalize()


def month_end_snapshot_map() -> dict[pd.Timestamp, Path]:
    snapshots: dict[pd.Timestamp, Path] = {}
    if not AR_SNAPSHOT_DIR.exists():
        return snapshots
    for path in AR_SNAPSHOT_DIR.glob("ar_*.csv"):
        date = parse_snapshot_date(path)
        if date is None:
            continue
        month_end = date + pd.offsets.MonthEnd(0)
        if date == month_end:
            snapshots[date.to_period("M").to_timestamp()] = path
    return snapshots


def load_trade_ar(path: Path) -> dict[str, float]:
    raw = pd.read_csv(path)
    balance_col = first_column(raw, ["Open Balance", "Amount Remaining", "Balance"])
    channel_col = first_column(raw, ["Channel Clean", "Sales Channel: Name", "Sales Channel", "Channel"])
    if balance_col is None or channel_col is None:
        return {bucket: 0.0 for bucket in TRADE_BUCKETS}
    raw["Balance Calc"] = pd.to_numeric(raw[balance_col], errors="coerce").fillna(0.0)
    raw["Trade Bucket"] = safe_text(raw, channel_col).map(trade_bucket)
    grouped = raw[raw["Trade Bucket"].notna()].groupby("Trade Bucket")["Balance Calc"].sum()
    return {bucket: float(grouped.get(bucket, 0.0)) for bucket in TRADE_BUCKETS}


def trade_sales_by_month(frame: pd.DataFrame) -> pd.DataFrame:
    trade = frame[frame["Trade Bucket"].notna()].copy()
    if trade.empty:
        return pd.DataFrame(columns=["Month", "Trade Bucket", "Revenue"])
    return (
        trade.groupby(["Month", "Trade Bucket"], as_index=False)["Revenue Calc"]
        .sum()
        .rename(columns={"Revenue Calc": "Revenue"})
    )


def build_dso(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[pd.Timestamp, Path]]:
    sales = trade_sales_by_month(frame)
    snapshots = month_end_snapshot_map()
    months = sorted(pd.Timestamp(m) for m in frame["Month"].dropna().unique())
    records: list[dict] = []
    for month in months:
        month = pd.Timestamp(month)
        days = calendar.monthrange(month.year, month.month)[1]
        snapshot = snapshots.get(month)
        ar_values = load_trade_ar(snapshot) if snapshot else {bucket: pd.NA for bucket in TRADE_BUCKETS}
        for bucket in TRADE_BUCKETS:
            bucket_sales = sales[(sales["Month"] == month) & (sales["Trade Bucket"] == bucket)]
            sales_value = float(bucket_sales["Revenue"].sum()) if not bucket_sales.empty else 0.0
            ar_value = ar_values[bucket]
            dso = (float(ar_value) / sales_value * days) if snapshot and sales_value else pd.NA
            records.append({
                "Month": month,
                "Channel": bucket,
                "AR": ar_value,
                "Sales": sales_value,
                "Days": days,
                "DSO": dso,
                "Has EOM Snapshot": snapshot is not None,
            })
    return pd.DataFrame(records), snapshots


def fmt_currency(value: object) -> str:
    if pd.isna(value):
        return "N/M"
    return f"${float(value):,.0f}"


def fmt_dso(value: object) -> str:
    if pd.isna(value):
        return "N/M"
    return f"{float(value):.0f}"


def finance_grid_html(row_defs: list[tuple[str, str, dict[pd.Timestamp, object]]], months: list[pd.Timestamp]) -> str:
    headers = "".join(f"<th>{m:%b-%Y}</th>" for m in months)
    rows = []
    for label, css_class, values in row_defs:
        cells = []
        for month in months:
            value = values.get(month, pd.NA)
            if css_class.startswith("dso"):
                text = fmt_dso(value)
            else:
                text = fmt_currency(value)
            cls = ' class="na"' if text == "N/M" else ""
            cells.append(f"<td{cls}>{text}</td>")
        rows.append(f'<tr class="{css_class}"><td>{label}</td>{"".join(cells)}</tr>')
    return f'<div class="gw-grid-wrap"><table class="gw-grid"><thead><tr><th></th>{headers}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def weekly_chart(summary: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(x=summary["Week Label"], y=summary["Revenue"], name="Revenue", marker_color="#155b49")
    fig.add_trace(go.Scatter(x=summary["Week Label"], y=summary["Weighted $/LB"], name="Weighted $/LB", mode="lines+markers", yaxis="y2", line=dict(color="#d7a928", width=3)))
    fig.update_layout(
        template="plotly_white", height=430, hovermode="x unified",
        margin=dict(l=55, r=60, t=65, b=70),
        legend=dict(orientation="h", y=1.08, x=0),
        yaxis=dict(title="Revenue", tickprefix="$", tickformat="~s", gridcolor="#e8eeea"),
        yaxis2=dict(title="Weighted $/LB", overlaying="y", side="right", tickprefix="$", tickformat=".2f", showgrid=False),
    )
    return fig


def monthly_chart(summary: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(
        x=summary["Month Label"], y=summary["Revenue"], marker_color="#155b49",
        text=summary["Revenue"], texttemplate="$%{text:,.0f}", textposition="outside",
        hovertemplate="%{x}<br>Revenue: $%{y:,.2f}<extra></extra>",
    )
    fig.update_layout(
        template="plotly_white", height=400, showlegend=False,
        margin=dict(l=55, r=25, t=40, b=60),
        yaxis=dict(title="Revenue", tickprefix="$", tickformat="~s", gridcolor="#e8eeea"),
    )
    return fig


# -----------------------------------------------------------------------------
# Load data
# -----------------------------------------------------------------------------
raw_revenue = load_revenue_history()
if raw_revenue.empty:
    st.info("Upload and save Revenue history in Administration first.")
    footer()
    st.stop()

try:
    df, has_size_in_pounds = normalize_revenue(raw_revenue)
except ValueError as exc:
    st.error(str(exc))
    footer()
    st.stop()

if not has_size_in_pounds:
    st.warning(
        "Revenue history does not yet contain 'Size in Pounds'. The page is using the legacy pounds field as a temporary fallback. "
        "Reload the full March-August Revenue Analysis report with Size in Pounds before relying on $/LB."
    )

# -----------------------------------------------------------------------------
# Sidebar
# -----------------------------------------------------------------------------
st.sidebar.markdown("## Revenue Filters")
available_weeks = sorted(df["Week Start"].dropna().unique(), reverse=True)
week_options = [pd.Timestamp(value) for value in available_weeks]
selected_week = st.sidebar.selectbox(
    "Week Of",
    options=week_options,
    format_func=lambda value: f"{value:%b %d} – {(value + pd.Timedelta(days=6)):%b %d, %Y}",
)
history_weeks = st.sidebar.slider("Trend Weeks", min_value=4, max_value=26, value=16, step=1)

filtered = df.copy()
for label, col in [
    ("Channel", "Sales Channel Calc"),
    ("Customer", "Customer Calc"),
    ("Sales Rep", "Sales Rep Calc"),
    ("Item Class", "Item Class Calc"),
]:
    filtered = apply_multiselect_filter(filtered, label, col)

search = st.sidebar.text_input("Search customer / item")
if search:
    needle = search.lower().strip()
    filtered = filtered[
        filtered["Customer Calc"].str.lower().str.contains(needle, na=False)
        | filtered["Item Calc"].str.lower().str.contains(needle, na=False)
    ]

selected_df = filtered[filtered["Week Start"] == selected_week].copy()
if selected_df.empty:
    st.warning("No transactions match the selected week and filters.")
    footer()
    st.stop()

history_start = selected_week - pd.Timedelta(weeks=history_weeks - 1)
trend_df = filtered[(filtered["Week Start"] >= history_start) & (filtered["Week Start"] <= selected_week)].copy()
weekly = weekly_summary(trend_df)
all_weekly = weekly_summary(filtered)
current = weekly[weekly["Week Start"] == selected_week].iloc[0]
prior_rows = all_weekly[all_weekly["Week Start"] == selected_week - pd.Timedelta(days=7)]
prior = prior_rows.iloc[0] if not prior_rows.empty else None
prior_four = all_weekly[(all_weekly["Week Start"] < selected_week) & (all_weekly["Week Start"] >= selected_week - pd.Timedelta(days=28))]

monthly = monthly_summary(filtered)
selected_month = selected_week.to_period("M").to_timestamp()
current_month_rows = monthly[monthly["Month"] == selected_month]
current_month_revenue = float(current_month_rows["Revenue"].sum()) if not current_month_rows.empty else 0.0
prior_month = selected_month - pd.offsets.MonthBegin(1)
prior_month_rows = monthly[monthly["Month"] == prior_month]
prior_month_revenue = float(prior_month_rows["Revenue"].sum()) if not prior_month_rows.empty else 0.0

dso_full, eom_snapshots = build_dso(df)
latest_dso = pd.NA
latest_dso_month = None
if not dso_full.empty:
    total_dso_rows = []
    for month, group in dso_full.groupby("Month"):
        if not bool(group["Has EOM Snapshot"].all()):
            continue
        total_ar = pd.to_numeric(group["AR"], errors="coerce").sum(min_count=1)
        total_sales = group["Sales"].sum()
        days = int(group["Days"].iloc[0])
        if pd.notna(total_ar) and total_sales:
            total_dso_rows.append((pd.Timestamp(month), float(total_ar) / float(total_sales) * days))
    if total_dso_rows:
        latest_dso_month, latest_dso = sorted(total_dso_rows, key=lambda x: x[0])[-1]

# -----------------------------------------------------------------------------
# Executive Summary
# -----------------------------------------------------------------------------
section(
    "Executive Summary",
    f"Selected week: {selected_week:%b %d}–{(selected_week + pd.Timedelta(days=6)):%b %d, %Y}. Weekly reporting is always Monday–Sunday; monthly reporting follows calendar months.",
)
current_revenue = float(current["Revenue"])
current_lbs = float(current["Lbs"])
current_weighted = float(current["Weighted $/LB"])
prior_revenue = float(prior["Revenue"]) if prior is not None else 0.0
prior_weighted = float(prior["Weighted $/LB"]) if prior is not None else 0.0
four_avg = float(prior_four["Revenue"].mean()) if not prior_four.empty else 0.0
metric_row([
    (f"Weekly Revenue • {delta_label(current_revenue, prior_revenue)}", format_money(current_revenue, 2)),
    ("Eligible Coffee Lbs", format_number(current_lbs, 1)),
    (f"Weighted $/LB • {delta_label(current_weighted, prior_weighted)}", format_money(current_weighted, 2)),
    ("Current Month Revenue", format_money(current_month_revenue, 2)),
    ("Prior Month Revenue", format_money(prior_month_revenue, 2)),
    (f"Latest Trade DSO • {latest_dso_month:%b-%Y}" if latest_dso_month is not None else "Latest Trade DSO", f"{float(latest_dso):.0f} days" if pd.notna(latest_dso) else "N/M"),
])

missing_weight_revenue = float(selected_df["Missing Weight Revenue"].sum())
with st.container(border=True):
    st.markdown("#### Executive Story")
    change = percent_change(current_revenue, prior_revenue)
    if change is not None:
        direction = "up" if change >= 0 else "down"
        st.markdown(f"- Weekly revenue is **{direction} {abs(change):.1f}%** versus the prior Monday–Sunday week.")
    if four_avg:
        four_change = percent_change(current_revenue, four_avg)
        if four_change is not None:
            position = "above" if four_change >= 0 else "below"
            st.markdown(f"- The selected week is **{abs(four_change):.1f}% {position}** the prior 4-week average of {format_money(four_avg, 0)}.")
    st.markdown(f"- Wholesale weighted pricing is **{format_money(current_weighted, 2)}/lb** on **{format_number(current_lbs, 1)} lbs** with valid Size in Pounds.")
    if missing_weight_revenue:
        st.markdown(f"- **{format_money(missing_weight_revenue, 2)}** of otherwise trade roasted-coffee revenue has no usable Size in Pounds and is excluded from $/LB.")

# -----------------------------------------------------------------------------
# Weekly Revenue + $/LB
# -----------------------------------------------------------------------------
section(
    "Weekly Revenue + $/LB",
    "Monday–Sunday operating view. Total revenue includes all selected revenue; pounds and weighted $/LB use only trade roasted-coffee rows with a positive Size in Pounds.",
)
st.plotly_chart(weekly_chart(weekly), width="stretch")
weekly_display = weekly[["Week Start", "Week End", "Revenue", "Eligible_Revenue", "Lbs", "Weighted $/LB", "Orders", "Customers", "Missing_Weight_Revenue"]].copy().sort_values("Week Start", ascending=False)
weekly_display["Week"] = weekly_display.apply(lambda r: f"{r['Week Start']:%m/%d/%y} - {r['Week End']:%m/%d/%y}", axis=1)
weekly_display = weekly_display[["Week", "Revenue", "Eligible_Revenue", "Lbs", "Weighted $/LB", "Orders", "Customers", "Missing_Weight_Revenue"]]
st.dataframe(
    weekly_display,
    width="stretch",
    hide_index=True,
    column_config={
        "Revenue": st.column_config.NumberColumn("Total Revenue", format="$%,.2f"),
        "Eligible_Revenue": st.column_config.NumberColumn("Revenue Used in $/LB", format="$%,.2f"),
        "Lbs": st.column_config.NumberColumn("Eligible Lbs", format="%,.1f"),
        "Weighted $/LB": st.column_config.NumberColumn("Weighted $/LB", format="$%.2f"),
        "Missing_Weight_Revenue": st.column_config.NumberColumn("Missing Weight Revenue", format="$%,.2f"),
    },
)

# -----------------------------------------------------------------------------
# Monthly Revenue
# -----------------------------------------------------------------------------
section(
    "Monthly Revenue",
    "Calendar-month revenue view. No $/LB is calculated here, so month-end accounting stays separate from weekly pricing analysis.",
)
st.plotly_chart(monthly_chart(monthly), width="stretch")
monthly_display = monthly[["Month Label", "Revenue", "Orders", "Customers", "MoM %"]].copy().sort_values("Month Label")
st.dataframe(
    monthly_display,
    width="stretch",
    hide_index=True,
    column_config={
        "Month Label": "Month",
        "Revenue": st.column_config.NumberColumn("Revenue", format="$%,.2f"),
        "MoM %": st.column_config.NumberColumn("MoM %", format="%.1f%%"),
    },
)

# -----------------------------------------------------------------------------
# Monthly DSO
# -----------------------------------------------------------------------------
section(
    "DSO by Month",
    "Trade DSO = month-end trade AR ÷ calendar-month trade revenue × days in month. Only exact month-end AR snapshots are used.",
)
st.markdown(
    '<div class="gw-note">Included: Foodservice Direct, Foodservice Distributor, Grocery Direct, Grocery Distributor. Excluded: Retail, E-Commerce, Samples, Employees, and other non-trade activity.</div>',
    unsafe_allow_html=True,
)

if dso_full.empty:
    st.info("No DSO history can be calculated yet.")
else:
    months = sorted(pd.Timestamp(m) for m in dso_full["Month"].unique())[-13:]
    total_ar_values: dict[pd.Timestamp, object] = {}
    total_sales_values: dict[pd.Timestamp, object] = {}
    total_dso_values: dict[pd.Timestamp, object] = {}

    for month in months:
        group = dso_full[dso_full["Month"] == month]
        has_snapshot = bool(group["Has EOM Snapshot"].all())
        total_ar = pd.to_numeric(group["AR"], errors="coerce").sum(min_count=1) if has_snapshot else pd.NA
        total_sales = float(group["Sales"].sum())
        days = calendar.monthrange(month.year, month.month)[1]
        total_ar_values[month] = total_ar
        total_sales_values[month] = total_sales
        total_dso_values[month] = (float(total_ar) / total_sales * days) if has_snapshot and pd.notna(total_ar) and total_sales else pd.NA

    overall_rows = [
        ("Net AR", "metric-row", total_ar_values),
        ("Total Sales", "metric-row", total_sales_values),
        ("DSO", "dso-total", total_dso_values),
    ]
    st.markdown(finance_grid_html(overall_rows, months), unsafe_allow_html=True)

    missing_months = [m for m in months if m not in eom_snapshots]
    if missing_months:
        st.caption("N/M = no exact month-end AR snapshot saved for: " + ", ".join(m.strftime("%b %Y") for m in missing_months) + ".")

    section("DSO by Month by Channel", "AR, monthly sales, and DSO for each trade channel, matching the finance schedule format.")
    for bucket in TRADE_BUCKETS:
        channel_rows = dso_full[dso_full["Channel"] == bucket]
        ar_map = {pd.Timestamp(r["Month"]): r["AR"] for _, r in channel_rows.iterrows()}
        sales_map = {pd.Timestamp(r["Month"]): r["Sales"] for _, r in channel_rows.iterrows()}
        dso_map = {pd.Timestamp(r["Month"]): r["DSO"] for _, r in channel_rows.iterrows()}
        st.markdown(f"**{bucket}**")
        st.markdown(finance_grid_html([
            (f"AR - {bucket}", "data-row", ar_map),
            (f"Sales - {bucket}", "data-row", sales_map),
            ("DSO", "dso-channel", dso_map),
        ], months), unsafe_allow_html=True)

    dso_export = dso_full.copy()
    dso_export["Month"] = dso_export["Month"].dt.strftime("%Y-%m")
    st.download_button(
        "⇩ Export Monthly DSO",
        dso_export.to_csv(index=False).encode("utf-8"),
        "Monthly_Trade_DSO.csv",
        "text/csv",
    )

footer()
