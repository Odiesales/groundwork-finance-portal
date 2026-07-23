import math
from datetime import timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.data import load_revenue_history, revenue_summary
from utils.ui import (
    page_header,
    section,
    footer,
    metric_row,
    format_money,
    format_number,
    apply_multiselect_filter,
    style_revenue_table,
)


page_header(
    "Weekly Revenue Report",
    "Weekly revenue, roasted-coffee pounds, average and weighted $/LB, channel performance, and sales trends.",
    badge="Weekly Upload",
)


# CEO-ready page polish: light chart cards, readable tabs, and spacing that
# prevents titles, legends, and labels from overlapping.
st.markdown(
    """
    <style>
    .block-container {padding-top: 1.15rem; padding-bottom: 2rem; max-width: 1500px;}
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #ffffff;
        border: 1px solid #dfe7e2 !important;
        border-radius: 14px;
        box-shadow: 0 3px 12px rgba(20, 73, 58, 0.06);
    }
    button[data-baseweb="tab"] {
        background: #f4f7f5 !important;
        border: 1px solid #d8e2dc !important;
        border-radius: 8px 8px 0 0 !important;
        padding: 0.65rem 1rem !important;
        margin-right: 0.35rem !important;
    }
    button[data-baseweb="tab"] p {
        color: #163f35 !important;
        font-size: 0.94rem !important;
        font-weight: 700 !important;
        opacity: 1 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background: #0f4b3c !important;
        border-color: #0f4b3c !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] p {color: #ffffff !important;}
    div[data-testid="stPlotlyChart"] {
        background: #ffffff;
        border: 1px solid #e1e8e4;
        border-radius: 12px;
        padding: 0.4rem 0.5rem 0.2rem;
        box-shadow: 0 2px 8px rgba(20, 73, 58, 0.05);
    }
    div[data-testid="stDataFrame"] {
        border: 1px solid #e1e8e4;
        border-radius: 10px;
        overflow: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def safe_numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(0.0, index=frame.index, dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce").fillna(0.0)


def safe_text(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series("", index=frame.index, dtype="object")
    return frame[column].fillna("").astype(str)


def percent_change(current: float, prior: float) -> float | None:
    if prior == 0 or pd.isna(prior):
        return None
    return ((current - prior) / abs(prior)) * 100


def delta_text(current: float, prior: float) -> str:
    change = percent_change(current, prior)
    if change is None:
        return "No prior-week comparison"
    arrow = "▲" if change >= 0 else "▼"
    return f"{arrow} {abs(change):.1f}% vs prior week"


def four_week_text(current: float, prior_four_average: float) -> str:
    change = percent_change(current, prior_four_average)
    if change is None:
        return "No 4-week comparison"
    arrow = "▲" if change >= 0 else "▼"
    return f"{arrow} {abs(change):.1f}% vs prior 4-week avg"


def channel_group(value: str) -> str:
    text = str(value).strip().lower()
    if "grocery" in text:
        return "Grocery"
    if "foodservice" in text or "food service" in text:
        return "Foodservice"
    if "e-commerce" in text or "ecommerce" in text or "e commerce" in text:
        return "E-Commerce"
    if "retail" in text or "cafe" in text or "café" in text:
        return "Retail"
    if "intercompany" in text:
        return "Intercompany"
    return "Other"


def weekly_summary(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()

    grouped = (
        frame.groupby("Week Start", as_index=False)
        .agg(
            Revenue=("Eligible Revenue", "sum"),
            Roasted_Revenue=("Eligible Revenue", "sum"),
            Lbs=("Eligible Lbs", "sum"),
            Eligible_Revenue=("Eligible Revenue", "sum"),
            Orders=("Document Number", "nunique"),
            Customers=("Customer", "nunique"),
        )
        .sort_values("Week Start")
    )

    # Match the weekly pricing summary:
    #   Average $/LB  = simple average of each eligible source row's $/LB.
    #   Weighted $/LB = total eligible invoiced sales / total eligible pounds.
    # Revenue rows with zero pounds remain in invoiced sales (the numerator),
    # while their undefined row-level $/LB is naturally excluded from the average.
    row_rates = frame.loc[frame["Eligible Lbs"] > 0, ["Week Start", "Eligible Revenue", "Eligible Lbs"]].copy()
    row_rates["Row $/LB"] = row_rates["Eligible Revenue"].div(
        row_rates["Eligible Lbs"].replace(0, pd.NA)
    )
    average_rates = (
        row_rates.groupby("Week Start")["Row $/LB"]
        .mean()
        .rename("Average $/LB")
    )

    grouped = grouped.merge(average_rates, on="Week Start", how="left")
    grouped["Average $/LB"] = grouped["Average $/LB"].fillna(0.0)
    grouped["Weighted $/LB"] = grouped["Eligible_Revenue"].div(
        grouped["Lbs"].replace(0, pd.NA)
    ).fillna(0.0)
    return grouped


def _base_layout(height: int = 410) -> dict:
    return dict(
        template="plotly_white",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(family="Arial, sans-serif", color="#173f35", size=12),
        hovermode="x unified",
        margin=dict(l=62, r=72, t=78, b=78),
        height=height,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.08,
            xanchor="left",
            x=0,
            font=dict(size=11, color="#173f35"),
            bgcolor="rgba(255,255,255,0.85)",
        ),
        xaxis=dict(
            title=None,
            tickangle=0,
            tickfont=dict(size=10, color="#36564d"),
            showgrid=False,
            automargin=True,
        ),
    )


def combo_chart(summary: pd.DataFrame, title: str = "") -> go.Figure:
    fig = go.Figure()
    fig.add_bar(
        x=summary["Week Label"],
        y=summary["Roasted_Revenue"],
        name="Invoiced Sales",
        marker_color="#155b49",
        hovertemplate="%{x}<br>Invoiced Sales: $%{y:,.2f}<extra></extra>",
    )
    fig.add_trace(go.Scatter(
        x=summary["Week Label"],
        y=summary["Lbs"],
        name="Lbs (Qty)",
        mode="lines+markers",
        line=dict(color="#1aa6d9", width=2.4),
        marker=dict(size=6),
        hovertemplate="%{x}<br>Lbs: %{y:,.1f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=summary["Week Label"],
        y=summary["Average $/LB"],
        name="$/LB (Average)",
        mode="lines+markers",
        yaxis="y2",
        line=dict(color="#f2b400", width=2.6),
        marker=dict(size=6),
        hovertemplate="%{x}<br>Average $/LB: $%{y:,.2f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=summary["Week Label"],
        y=summary["Weighted $/LB"],
        name="$/LB (Weighted)",
        mode="lines+markers",
        yaxis="y2",
        line=dict(color="#e31a1c", width=2.6),
        marker=dict(size=6),
        hovertemplate="%{x}<br>Weighted $/LB: $%{y:,.2f}<extra></extra>",
    ))
    layout = _base_layout(455)
    layout.update(
        title=dict(text=title, x=0.01, xanchor="left", font=dict(size=14)) if title else None,
        barmode="group",
        yaxis=dict(
            title="Invoiced Sales / Lbs",
            tickprefix="$",
            tickformat=",.2f",
            gridcolor="#e8eeea",
            zeroline=False,
        ),
        yaxis2=dict(
            title="$/LB",
            overlaying="y",
            side="right",
            showgrid=False,
            tickprefix="$",
            tickformat=".2f",
            rangemode="tozero",
        ),
    )
    fig.update_layout(**layout)
    return fig


def revenue_trend_chart(summary: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(
        x=summary["Week Label"], y=summary["Revenue"], name="Revenue",
        marker_color="#155b49", text=summary["Revenue"],
        texttemplate="$%{text:,.2f}", textposition="outside", cliponaxis=False,
        textfont=dict(size=10, color="#173f35"),
        hovertemplate="%{x}<br>Revenue: $%{y:,.2f}<extra></extra>",
    )
    if len(summary) >= 2:
        average = summary["Revenue"].mean()
        fig.add_hline(y=average, line_dash="dot", line_color="#d7a928",
                      annotation_text=f"Average ${average:,.2f}",
                      annotation_position="top left",
                      annotation_font_color="#6b5715")
    layout = _base_layout(420)
    layout.update(
        showlegend=False,
        margin=dict(l=62, r=28, t=55, b=78),
        yaxis=dict(title="Revenue", tickprefix="$", tickformat=",.2f", gridcolor="#e8eeea", zeroline=False),
    )
    fig.update_layout(**layout)
    return fig


def line_chart(pivot: pd.DataFrame, title: str, y_title: str, currency: bool = True) -> go.Figure:
    fig = go.Figure()
    palette = ["#155b49", "#2f7dbd", "#d7a928", "#9b5f93", "#d05b47", "#4f8b5b"]
    for idx, column in enumerate(pivot.columns):
        fig.add_trace(go.Scatter(
            x=pivot.index, y=pivot[column], name=str(column), mode="lines+markers",
            line=dict(width=2.2, color=palette[idx % len(palette)]), marker=dict(size=5),
        ))
    layout = _base_layout(430)
    layout.update(
        title=dict(text=title, x=0.01, xanchor="left", font=dict(size=14)),
        margin=dict(l=62, r=28, t=105, b=72),
        legend=dict(orientation="h", yanchor="bottom", y=1.14, xanchor="left", x=0,
                    font=dict(size=10, color="#173f35"), bgcolor="rgba(255,255,255,0.9)"),
        yaxis=dict(title=y_title, tickprefix="$" if currency else "",
                   tickformat=",.2f" if currency else "~s", gridcolor="#e8eeea", zeroline=False),
    )
    fig.update_layout(**layout)
    return fig


def make_insights(current: pd.Series, prior: pd.Series | None, prior_four: pd.DataFrame) -> list[str]:
    insights: list[str] = []

    if prior is not None:
        rev_change = percent_change(current["Revenue"], prior["Revenue"])
        lbs_change = percent_change(current["Lbs"], prior["Lbs"])
        price_change = percent_change(current["Weighted $/LB"], prior["Weighted $/LB"])

        if rev_change is not None:
            direction = "increased" if rev_change >= 0 else "decreased"
            insights.append(
                f"Revenue {direction} {abs(rev_change):.1f}% versus the prior week, "
                f"from {format_money(prior['Revenue'], 2)} to {format_money(current['Revenue'], 2)}."
            )
        if lbs_change is not None and price_change is not None:
            lbs_direction = "increased" if lbs_change >= 0 else "decreased"
            price_direction = "increased" if price_change >= 0 else "decreased"
            insights.append(
                f"Eligible roasted-coffee pounds {lbs_direction} {abs(lbs_change):.1f}%, while weighted $/LB "
                f"{price_direction} {abs(price_change):.1f}% to {format_money(current['Weighted $/LB'])}."
            )

    if not prior_four.empty:
        four_avg = prior_four["Revenue"].mean()
        four_change = percent_change(current["Revenue"], four_avg)
        if four_change is not None:
            position = "above" if four_change >= 0 else "below"
            insights.append(
                f"The selected week finished {abs(four_change):.1f}% {position} the prior four-week revenue average "
                f"of {format_money(four_avg, 2)}."
            )

    return insights or ["More weekly history is needed before comparative insights can be calculated."]


# -----------------------------------------------------------------------------
# Load and normalize data
# -----------------------------------------------------------------------------
df = load_revenue_history()
if df.empty:
    st.info("Upload and save a Revenue snapshot in Administration first.")
    footer()
    st.stop()

for required_column, default in [
    ("Revenue", 0.0),
    ("Lbs", 0.0),
    ("Sales Channel", "Unassigned"),
    ("Customer", "Unassigned"),
    ("Sales Rep", "Unassigned"),
    ("Item Class", "Unassigned"),
    ("Coffee Size", "Unassigned"),
    ("Item / Memo", ""),
    ("Document Number", ""),
]:
    if required_column not in df.columns:
        df[required_column] = default

if "Week" not in df.columns:
    st.error("Revenue data does not contain the source Week column (Column B).")
    footer()
    st.stop()

df["Revenue"] = safe_numeric(df, "Revenue")
df["Lbs"] = safe_numeric(df, "Lbs")
df["Sales Channel"] = safe_text(df, "Sales Channel").replace("", "Unassigned")
df["Customer"] = safe_text(df, "Customer").replace("", "Unassigned")
df["Sales Rep"] = safe_text(df, "Sales Rep").replace("", "Unassigned")
df["Item Class"] = safe_text(df, "Item Class").replace("", "Unassigned")
df["Coffee Size"] = safe_text(df, "Coffee Size").replace("", "Unassigned")
df["Item / Memo"] = safe_text(df, "Item / Memo")
df["Document Number"] = safe_text(df, "Document Number")
df["Channel Group"] = df["Sales Channel"].map(channel_group)

# Column B (Week) is the reporting calendar source of truth.
# Examples: "(26-Jun) 26", "(26-Jun) 27", "(26-Jul) 28".
# The number is the reporting week and the two-digit prefix is the year.
def parse_source_week(value):
    import re

    text = str(value).strip()
    match = re.search(r"\((\d{2})-[A-Za-z]{3}\)\s*(\d{1,2})$", text)
    if not match:
        return pd.NaT, pd.NA

    year = 2000 + int(match.group(1))
    week_number = int(match.group(2))
    try:
        # Finance weeks run Sunday through Saturday. ISO week N begins Monday,
        # so subtract one day to obtain the Sunday that opens reporting week N.
        week_start = (pd.Timestamp.fromisocalendar(year, week_number, 1) - pd.Timedelta(days=1)).normalize()
        return week_start, week_number
    except ValueError:
        return pd.NaT, pd.NA

parsed_week = df["Week"].map(parse_source_week)
df["Week Start"] = parsed_week.map(lambda item: item[0])
df["Week Number"] = parsed_week.map(lambda item: item[1]).astype("Int64")
df["Week Raw"] = safe_text(df, "Week")

invalid_week_rows = int(df["Week Start"].isna().sum())
if invalid_week_rows:
    st.warning(
        f"{invalid_week_rows:,} row(s) have an invalid or blank Week value in Column B and were excluded."
    )

df = df[df["Week Start"].notna()].copy()
if df.empty:
    st.error("No valid reporting weeks were found in Column B (Week).")
    footer()
    st.stop()

# Wholesale pricing population: Finished Goods: Roasted Coffee sold through
# wholesale channels. E-Commerce, Corporate, Retail, and intercompany café
# activity are reported separately from the wholesale $/LB calculation.
excluded_pricing_channel_mask = df["Sales Channel"].str.contains(
    r"e[- ]?commerce|corporate|(^|:)\s*retail($|\s|:)|intercompany.*retail.*caf",
    case=False,
    regex=True,
    na=False,
)
roasted_coffee_mask = df["Item Class"].str.contains(
    r"finished goods\s*:\s*roasted coffee",
    case=False,
    regex=True,
    na=False,
)

quantity_column = next(
    (name for name in ["Sum of Quantity", "Quantity"] if name in df.columns),
    None,
)
units_column = next(
    (name for name in ["Sum of # of Units", "# of Units", "Units"] if name in df.columns),
    None,
)
size_column = next(
    (name for name in ["Roasted Coffee Size", "Coffee Size", "Coffee Size Oz", "Size Oz"] if name in df.columns),
    None,
)

def parse_package_weight_lbs(value) -> float:
    """Convert package-size values such as 12 oz, 2 lb, or numeric ounces to lbs."""
    if pd.isna(value):
        return 0.0
    text = str(value).strip().lower().replace("pounds", "lb").replace("pound", "lb")
    text = text.replace("ounces", "oz").replace("ounce", "oz")
    import re
    match = re.search(r"(-?\d+(?:\.\d+)?)", text)
    if not match:
        return 0.0
    number = abs(float(match.group(1)))
    if "oz" in text:
        return number / 16.0
    if "lb" in text:
        return number
    # Numeric helper columns are assumed to be ounces when their name says Oz;
    # otherwise treat them as pounds.
    return number / 16.0 if size_column and "oz" in size_column.lower() else number

quantity = pd.to_numeric(df[quantity_column], errors="coerce").abs() if quantity_column else pd.Series(0.0, index=df.index)
units = pd.to_numeric(df[units_column], errors="coerce").abs() if units_column else pd.Series(1.0, index=df.index)
units = units.where(units > 0, 1.0)
package_weight_lbs = df[size_column].apply(parse_package_weight_lbs) if size_column else pd.Series(0.0, index=df.index)

# Quantity behaves differently by channel in the source report:
# - Grocery quantity is case quantity, so multiply by units per case.
# - Foodservice quantity already represents sellable packages, so do not
#   multiply by units again.
# - Other channels use the full quantity x units calculation for audit purposes.
grocery_mask = df["Channel Group"].eq("Grocery")
foodservice_mask = df["Channel Group"].eq("Foodservice")
calculated_lbs = quantity * units * package_weight_lbs
calculated_lbs = calculated_lbs.where(~foodservice_mask, quantity * package_weight_lbs)

source_lbs = pd.to_numeric(df["Lbs"], errors="coerce").abs()
df["Calculated Lbs"] = calculated_lbs.where(calculated_lbs > 0, source_lbs).fillna(0.0)
df["Lbs Method"] = "Quantity × Units × Package Weight"
df.loc[foodservice_mask, "Lbs Method"] = "Quantity × Package Weight"
df.loc[df["Calculated Lbs"] <= 0, "Lbs Method"] = "Missing / unavailable"

eligible_pricing_mask = roasted_coffee_mask & (~excluded_pricing_channel_mask)
eligible_lb_mask = eligible_pricing_mask & (df["Calculated Lbs"] > 0)
df["Eligible Lbs"] = df["Calculated Lbs"].where(eligible_lb_mask, 0.0)
# Eligible roasted-coffee sales with missing pounds remain visible for review;
# no pounds; those rows affect weighted $/LB but not the simple average $/LB.
df["Eligible Revenue"] = df["Revenue"].where(eligible_pricing_mask, 0.0)

# Revenue-audit classifications. These fields do not silently remove source data;
# they explain how each row is treated and surface records that need review.
channel_lower = df["Sales Channel"].str.lower()
intercompany_retail_mask = channel_lower.str.contains(
    r"intercompany.*(retail|caf)|(?:retail|caf).*intercompany|i/c.*(retail|caf)",
    regex=True,
    na=False,
)
retail_cafe_mask = channel_lower.str.contains(r"retail|cafe|café", regex=True, na=False)
corporate_mask = channel_lower.str.contains(r"corporate", regex=True, na=False)
ecommerce_mask = channel_lower.str.contains(r"e[- ]?commerce|ecommerce", regex=True, na=False)
missing_lbs_mask = eligible_pricing_mask & (df["Calculated Lbs"] <= 0) & (df["Revenue"] != 0)
negative_lbs_mask = pd.to_numeric(df["Lbs"], errors="coerce").fillna(0) < 0

df["Audit Status"] = "Included in Wholesale $/LB"
df.loc[~roasted_coffee_mask, "Audit Status"] = "Excluded - Non-roasted coffee"
df.loc[ecommerce_mask & roasted_coffee_mask, "Audit Status"] = "Excluded - E-Commerce"
df.loc[corporate_mask & roasted_coffee_mask, "Audit Status"] = "Excluded - Corporate"
df.loc[retail_cafe_mask & roasted_coffee_mask, "Audit Status"] = "Excluded - Retail/Cafe"
df.loc[intercompany_retail_mask & roasted_coffee_mask, "Audit Status"] = "Excluded - Intercompany Retail/Cafe"
df.loc[missing_lbs_mask, "Audit Status"] = "Review - Eligible coffee revenue missing lbs"

df["Audit Issue"] = ""
df.loc[missing_lbs_mask, "Audit Issue"] = "Roasted-coffee revenue has zero or missing pounds"
df.loc[negative_lbs_mask, "Audit Issue"] = "Source pounds are negative; absolute value is used for reporting"
df.loc[df["Sales Channel"].eq("Unassigned"), "Audit Issue"] = "Sales channel is missing"
df.loc[df["Customer"].eq("Unassigned"), "Audit Issue"] = "Customer is missing"

df["Included in Total Revenue"] = True
df["Included in Wholesale Population"] = eligible_pricing_mask
df["Included in Wholesale $/LB"] = eligible_lb_mask
df["Missing Lbs Revenue"] = df["Revenue"].where(missing_lbs_mask, 0.0)
df["Excluded Pricing Revenue"] = df["Revenue"].where(~eligible_pricing_mask, 0.0)

# -----------------------------------------------------------------------------
# Sidebar filters and selected week
# -----------------------------------------------------------------------------
st.sidebar.markdown("## Revenue Filters")

available_weeks = sorted(df["Week Start"].dropna().unique(), reverse=True)
week_options = [pd.Timestamp(value) for value in available_weeks]
selected_week = st.sidebar.selectbox(
    "Week Of",
    options=week_options,
    index=0,
    format_func=lambda value: f"{value:%b %d} – {(value + pd.Timedelta(days=6)):%b %d, %Y}  •  Week {(value + pd.Timedelta(days=6)).isocalendar().week}",
)

history_weeks = st.sidebar.slider("Trend Weeks", min_value=4, max_value=26, value=16, step=1)

filtered = df.copy()
for label, col in [
    ("Channel", "Sales Channel"),
    ("Customer", "Customer"),
    ("Sales Rep", "Sales Rep"),
    ("Item Class", "Item Class"),
    ("Coffee Size", "Coffee Size"),
]:
    filtered = apply_multiselect_filter(filtered, label, col)

search = st.sidebar.text_input("Search customer / item")
if search:
    search_text = search.lower().strip()
    filtered = filtered[
        filtered["Customer"].str.lower().str.contains(search_text, na=False)
        | filtered["Item / Memo"].str.lower().str.contains(search_text, na=False)
    ]

history_start = selected_week - timedelta(weeks=history_weeks - 1)
trend_df = filtered[
    (filtered["Week Start"] >= history_start)
    & (filtered["Week Start"] <= selected_week)
].copy()
selected_df = filtered[filtered["Week Start"] == selected_week].copy()
prior_week = selected_week - timedelta(weeks=1)
prior_df = filtered[filtered["Week Start"] == prior_week].copy()

if selected_df.empty:
    st.warning("No transactions match the selected week and filters.")
    footer()
    st.stop()

weekly = weekly_summary(trend_df)
weekly["Week Label"] = weekly["Week Start"].apply(
    lambda value: f"W{int((value + pd.Timedelta(days=1)).isocalendar().week)} • {value:%b %d}"
)

current_row = weekly.loc[weekly["Week Start"] == selected_week].iloc[0]
prior_rows = weekly.loc[weekly["Week Start"] == prior_week]
prior_row = prior_rows.iloc[0] if not prior_rows.empty else None
prior_four = weekly[
    (weekly["Week Start"] < selected_week)
    & (weekly["Week Start"] >= selected_week - timedelta(weeks=4))
]

current_revenue = float(current_row["Revenue"])
current_lbs = float(current_row["Lbs"])
current_weighted = float(current_row["Weighted $/LB"])
current_orders = int(current_row["Orders"])
current_customers = int(current_row["Customers"])

prior_revenue = float(prior_row["Revenue"]) if prior_row is not None else 0.0
prior_lbs = float(prior_row["Lbs"]) if prior_row is not None else 0.0
prior_weighted = float(prior_row["Weighted $/LB"]) if prior_row is not None else 0.0
prior_orders = float(prior_row["Orders"]) if prior_row is not None else 0.0
prior_four_revenue = float(prior_four["Revenue"].mean()) if not prior_four.empty else 0.0

# -----------------------------------------------------------------------------
# Weekly executive summary
# -----------------------------------------------------------------------------
section(
    f"Week {int((selected_week + pd.Timedelta(days=1)).isocalendar().week)} Executive Summary",
    f"Week of {selected_week:%B %d} through {(selected_week + pd.Timedelta(days=6)):%B %d, %Y}. E-Commerce, Corporate, Retail, and intercompany café activity are excluded from wholesale pricing reporting.",
)
metric_row(
    [
        (f"Weekly Revenue • {delta_text(current_revenue, prior_revenue)}", format_money(current_revenue, 2)),
        (f"Roasted Coffee Lbs • {delta_text(current_lbs, prior_lbs)}", format_number(current_lbs, 1)),
        (f"Weighted $/LB • {delta_text(current_weighted, prior_weighted)}", format_money(current_weighted)),
        (f"Orders • {delta_text(current_orders, prior_orders)}", f"{current_orders:,}"),
        ("Customers", f"{current_customers:,}"),
        (f"Revenue • {four_week_text(current_revenue, prior_four_revenue)}", format_money(prior_four_revenue, 2)),
    ]
)

insights = make_insights(current_row, prior_row, prior_four)

# Add a concise executive story using the selected week's underlying detail.
channel_story = (
    selected_df.groupby("Channel Group", dropna=False)["Revenue"]
    .sum()
    .sort_values(ascending=False)
)
if not channel_story.empty:
    top_channel = str(channel_story.index[0])
    top_channel_revenue = float(channel_story.iloc[0])
    insights.append(
        f"{top_channel} was the largest reported channel at {format_money(top_channel_revenue, 2)} for the selected week."
    )

missing_lbs_revenue = float(selected_df["Missing Lbs Revenue"].sum())
missing_lbs_rows = int((selected_df["Audit Status"] == "Review - Eligible coffee revenue missing lbs").sum())
excluded_pricing_revenue = float(selected_df["Excluded Pricing Revenue"].sum())
if missing_lbs_revenue != 0:
    insights.append(
        f"Data-quality review: {format_money(missing_lbs_revenue, 2)} across {missing_lbs_rows:,} roasted-coffee row(s) has no usable pounds and can distort weighted $/LB."
    )
if excluded_pricing_revenue != 0:
    insights.append(
        f"{format_money(excluded_pricing_revenue, 2)} of selected-week revenue is reported outside the wholesale pricing calculation and is shown separately below."
    )

with st.container(border=True):
    st.markdown("#### Weekly Story")
    for insight in insights:
        st.markdown(f"- {insight}")

# -----------------------------------------------------------------------------
# Data quality and pricing reconciliation
# -----------------------------------------------------------------------------
section(
    "Revenue Audit & Data Quality",
    "This section explains what is included, excluded, or held for review before the charts are interpreted.",
)

total_selected_revenue = float(selected_df["Revenue"].sum())
valid_pricing_revenue = float(selected_df.loc[selected_df["Included in Wholesale $/LB"], "Revenue"].sum())
valid_pricing_lbs = float(selected_df.loc[selected_df["Included in Wholesale $/LB"], "Calculated Lbs"].sum())
valid_weighted = valid_pricing_revenue / valid_pricing_lbs if valid_pricing_lbs else 0.0
retail_ic_revenue = float(
    selected_df.loc[selected_df["Audit Status"] == "Excluded - Intercompany Retail/Cafe", "Revenue"].sum()
)

metric_row(
    [
        ("Total Reported Revenue", format_money(total_selected_revenue, 2)),
        ("Wholesale Coffee Revenue Used", format_money(valid_pricing_revenue, 2)),
        ("Wholesale Coffee Pounds Used", format_number(valid_pricing_lbs, 1)),
        ("Calculated Wholesale $/LB", format_money(valid_weighted)),
        ("Coffee Revenue Missing Pounds", format_money(missing_lbs_revenue, 2)),
        ("Intercompany Retail/Cafe Revenue", format_money(retail_ic_revenue, 2)),
    ]
)

if missing_lbs_revenue != 0:
    st.error(
        f"Wholesale roasted-coffee revenue with no usable pounds: {format_money(missing_lbs_revenue, 2)} across {missing_lbs_rows:,} row(s). "
        "These rows are visible in the audit detail and should be corrected or approved before relying on $/LB."
    )
if retail_ic_revenue != 0:
    st.warning(
        f"Potential intercompany retail/cafe activity totals {format_money(retail_ic_revenue, 2)} and is reported separately from the wholesale pricing calculation."
    )

recon = (
    selected_df.groupby("Audit Status", dropna=False)
    .agg(
        Revenue=("Revenue", "sum"),
        Lbs=("Calculated Lbs", "sum"),
        Rows=("Document Number", "size"),
        Documents=("Document Number", "nunique"),
    )
    .reset_index()
    .rename(columns={"Audit Status": "Classification"})
)
recon["Revenue Share"] = recon["Revenue"].div(total_selected_revenue if total_selected_revenue else 1).mul(100)
recon["Reporting Treatment"] = "Reported separately"
recon.loc[recon["Classification"].eq("Included in Wholesale $/LB"), "Reporting Treatment"] = "Used in wholesale $/LB"
recon.loc[recon["Classification"].str.startswith("Review -", na=False), "Reporting Treatment"] = "Review source data"
recon["Revenue"] = recon["Revenue"].round(2)
recon["Lbs"] = recon["Lbs"].round(2)
recon["Revenue Share"] = recon["Revenue Share"].round(1).map(lambda value: f"{value:.1f}%")
recon = recon[["Classification", "Revenue", "Revenue Share", "Lbs", "Rows", "Documents", "Reporting Treatment"]]
st.dataframe(style_revenue_table(recon), width="stretch", hide_index=True)

audit_detail_columns = [
    "Week Raw", "Sales Channel", "Channel Group", "Customer", "Document Number",
    "Item Class", "Item / Memo", "Revenue", "Calculated Lbs", "Audit Status", "Audit Issue",
]
audit_detail_columns = [c for c in audit_detail_columns if c in selected_df.columns]
audit_detail = selected_df[audit_detail_columns].copy()
issues_only = audit_detail[
    audit_detail["Audit Status"].str.startswith(("Review -", "Excluded -"), na=False)
    | audit_detail["Audit Issue"].ne("")
].copy()

st.download_button(
    "⇩ Export Revenue Audit Detail",
    audit_detail.to_csv(index=False).encode("utf-8"),
    f"Revenue_Audit_{selected_week:%Y-%m-%d}.csv",
    "text/csv",
)
with st.expander(f"View audit exceptions and exclusions ({len(issues_only):,} rows)", expanded=missing_lbs_rows > 0):
    st.dataframe(issues_only, width="stretch", hide_index=True)

# -----------------------------------------------------------------------------
# Weekly trends
# -----------------------------------------------------------------------------
section("Weekly Revenue Detail", "Numbers first: revenue, roasted-coffee pounds, average and weighted $/LB, orders, and customers by week.")
weekly_display = weekly[["Week Start", "Revenue", "Lbs", "Average $/LB", "Weighted $/LB", "Orders", "Customers"]].copy().sort_values("Week Start", ascending=False)
weekly_display["Week Of"] = weekly_display["Week Start"].dt.strftime("%b %d, %Y")
weekly_display = weekly_display[["Week Of", "Revenue", "Lbs", "Average $/LB", "Weighted $/LB", "Orders", "Customers"]]
weekly_display["Average $/LB"] = weekly_display["Average $/LB"].round(2)
weekly_display["Weighted $/LB"] = weekly_display["Weighted $/LB"].round(2)
weekly_display["Lbs"] = weekly_display["Lbs"].round(2)
st.download_button("⇩ Export Weekly Revenue", weekly_display.to_csv(index=False).encode("utf-8"), "Weekly_Revenue.csv", "text/csv")
st.dataframe(style_revenue_table(weekly_display), width="stretch", hide_index=True)

section("Wholesale Sales by Week", "Revenue trend through the selected reporting week.")
st.plotly_chart(revenue_trend_chart(weekly), width='stretch')

section(
    "Sales: Roasted Coffee, Lbs and $/LB",
    "Invoiced Sales, pounds, average $/LB, and weighted $/LB use the wholesale roasted-coffee calculation. Retail/cafe and non-roasted-coffee rows are excluded from this chart.",
)
st.plotly_chart(combo_chart(weekly, ""), width='stretch')

# -----------------------------------------------------------------------------
# Channel-specific weekly analysis
# -----------------------------------------------------------------------------
section("Channel Performance", "Weekly results by channel. Missing-pound revenue and excluded populations are identified in the Revenue Audit above.")
channel_tabs = st.tabs(["Grocery", "Foodservice", "E-Commerce", "Retail"])
for tab, channel_name in zip(channel_tabs, ["Grocery", "Foodservice", "E-Commerce", "Retail"]):
    with tab:
        channel_df = trend_df[trend_df["Channel Group"] == channel_name].copy()
        channel_weekly = weekly_summary(channel_df)
        if channel_weekly.empty:
            st.info(f"No {channel_name} transactions match the current filters.")
        else:
            channel_weekly["Week Label"] = channel_weekly["Week Start"].apply(
                lambda value: f"W{int((value + pd.Timedelta(days=1)).isocalendar().week)} • {value:%b %d}"
            )
            if channel_name == "Retail":
                st.plotly_chart(revenue_trend_chart(channel_weekly), width='stretch')
                st.caption("Retail is revenue-only and is intentionally excluded from pounds and $/LB.")
            else:
                st.plotly_chart(
                    combo_chart(channel_weekly, ""),
                    width='stretch',
                )

# -----------------------------------------------------------------------------
# Retail by location/customer proxy
# -----------------------------------------------------------------------------
retail_trend = trend_df[trend_df["Channel Group"] == "Retail"].copy()
if not retail_trend.empty:
    location_column = "Location" if "Location" in retail_trend.columns else "Customer"
    retail_pivot = (
        retail_trend.groupby(["Week Start", location_column])["Revenue"]
        .sum()
        .unstack(fill_value=0)
    )
    top_locations = retail_pivot.sum().nlargest(8).index
    retail_pivot = retail_pivot.loc[:, top_locations]
    section("Retail: By Location", "Weekly revenue for the leading retail locations.")
    st.plotly_chart(
        line_chart(retail_pivot, "", "Revenue", currency=True),
        width='stretch',
    )

# -----------------------------------------------------------------------------
# Sales representative trends
# -----------------------------------------------------------------------------
rep_source = trend_df[
    ~trend_df["Sales Rep"].str.contains("house account|unassigned", case=False, regex=True, na=False)
].copy()
if not rep_source.empty:
    rep_totals = rep_source.groupby("Sales Rep")["Revenue"].sum().nlargest(5).index
    rep_revenue = (
        rep_source[rep_source["Sales Rep"].isin(rep_totals)]
        .groupby(["Week Start", "Sales Rep"])["Revenue"]
        .sum()
        .unstack(fill_value=0)
    )
    section("Sales by Sales Representative", "Weekly revenue trends for the top five sales representatives.")
    st.plotly_chart(
        line_chart(rep_revenue, "", "Revenue", currency=True),
        width='stretch',
    )

    rep_lb_source = rep_source[rep_source["Eligible Lbs"] > 0].copy()
    if not rep_lb_source.empty:
        rep_lb = (
            rep_lb_source.groupby(["Week Start", "Sales Rep"])
            .agg(Eligible_Revenue=("Eligible Revenue", "sum"), Eligible_Lbs=("Eligible Lbs", "sum"))
            .reset_index()
        )
        rep_lb["Weighted $/LB"] = rep_lb["Eligible_Revenue"].div(
            rep_lb["Eligible_Lbs"].replace(0, pd.NA)
        ).fillna(0.0)
        rep_lb = rep_lb[rep_lb["Sales Rep"].isin(rep_totals)]
        rep_lb_pivot = rep_lb.pivot(index="Week Start", columns="Sales Rep", values="Weighted $/LB").fillna(0)
        section("$/LB by Sales Representative", "Weighted weekly pricing for the top five representatives using eligible non-retail pounds.")
        st.plotly_chart(
            line_chart(rep_lb_pivot, "", "Weighted $/LB", currency=True),
            width='stretch',
        )

# -----------------------------------------------------------------------------
# Selected-week tables
# -----------------------------------------------------------------------------
left, right = st.columns(2)
with left:
    section("Selected Week: Channel Analysis", "Revenue, pounds, mix, and realized $/LB for the selected week.")
    st.dataframe(
        style_revenue_table(revenue_summary(selected_df, "Sales Channel")),
        width='stretch',
        hide_index=True,
    )
with right:
    section("Selected Week: Top Customers", "Top customers ranked by selected-week revenue.")
    st.dataframe(
        style_revenue_table(revenue_summary(selected_df, "Customer").head(25)),
        width='stretch',
        hide_index=True,
    )

st.download_button("⇩ Export Selected Week Detail", selected_df.to_csv(index=False).encode("utf-8"), f"Revenue_{selected_week:%Y-%m-%d}.csv", "text/csv")

section("Selected Week: Product / Item Pricing")
st.dataframe(
    style_revenue_table(revenue_summary(selected_df, "Item / Memo").head(75)),
    width='stretch',
    hide_index=True,
)

with st.expander("Selected Week Revenue Detail"):
    st.dataframe(selected_df, width='stretch', hide_index=True)

footer()
