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
    "Weekly revenue, roasted-coffee pounds, weighted $/LB, channel performance, and sales trends.",
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
            Revenue=("Revenue", "sum"),
            Lbs=("Eligible Lbs", "sum"),
            Eligible_Revenue=("Eligible Revenue", "sum"),
            Orders=("Document Number", "nunique"),
            Customers=("Customer", "nunique"),
        )
        .sort_values("Week Start")
    )
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
        x=summary["Week Label"], y=summary["Revenue"], name="Revenue",
        marker_color="#155b49",
        hovertemplate="%{x}<br>Revenue: $%{y:,.2f}<extra></extra>",
    )
    fig.add_trace(go.Scatter(
        x=summary["Week Label"], y=summary["Lbs"], name="Eligible Lbs",
        mode="lines+markers", yaxis="y2",
        line=dict(color="#d7a928", width=2.4), marker=dict(size=6),
        hovertemplate="%{x}<br>Eligible Lbs: %{y:,.1f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=summary["Week Label"], y=summary["Weighted $/LB"], name="Weighted $/LB",
        mode="lines+markers", yaxis="y3",
        line=dict(color="#2f7dbd", width=2.4), marker=dict(size=6),
        hovertemplate="%{x}<br>Weighted $/LB: $%{y:,.2f}<extra></extra>",
    ))
    layout = _base_layout(420)
    layout.update(
        title=dict(text=title, x=0.01, xanchor="left", font=dict(size=14)) if title else None,
        barmode="group",
        yaxis=dict(title="Revenue", tickprefix="$", tickformat="~s", gridcolor="#e8eeea", zeroline=False),
        yaxis2=dict(title="Eligible Lbs", overlaying="y", side="right", showgrid=False, position=0.92, tickformat="~s"),
        yaxis3=dict(title="$/LB", overlaying="y", side="right", showgrid=False, anchor="free", position=1.0, tickprefix="$", tickformat=".2f"),
    )
    fig.update_layout(**layout)
    return fig


def revenue_trend_chart(summary: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(
        x=summary["Week Label"], y=summary["Revenue"], name="Revenue",
        marker_color="#155b49", text=summary["Revenue"],
        texttemplate="$%{text:,.0f}", textposition="outside", cliponaxis=False,
        textfont=dict(size=10, color="#173f35"),
        hovertemplate="%{x}<br>Revenue: $%{y:,.2f}<extra></extra>",
    )
    if len(summary) >= 2:
        average = summary["Revenue"].mean()
        fig.add_hline(y=average, line_dash="dot", line_color="#d7a928",
                      annotation_text=f"Average ${average:,.0f}",
                      annotation_position="top left",
                      annotation_font_color="#6b5715")
    layout = _base_layout(420)
    layout.update(
        showlegend=False,
        margin=dict(l=62, r=28, t=55, b=78),
        yaxis=dict(title="Revenue", tickprefix="$", tickformat="~s", gridcolor="#e8eeea", zeroline=False),
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
                   tickformat="~s" if currency else "~s", gridcolor="#e8eeea", zeroline=False),
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
                f"from {format_money(prior['Revenue'], 0)} to {format_money(current['Revenue'], 0)}."
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
                f"of {format_money(four_avg, 0)}."
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

# Retail is intentionally excluded from pounds and $/LB. Revenue is only included
# in the $/LB numerator where an eligible, non-retail row carries positive pounds.
retail_mask = (
    df["Sales Channel"].str.contains("retail|cafe|café", case=False, regex=True, na=False)
    | df["Item Class"].str.contains("retail", case=False, regex=False, na=False)
)
eligible_lb_mask = (~retail_mask) & (df["Lbs"] > 0)
df["Eligible Lbs"] = df["Lbs"].where(eligible_lb_mask, 0.0)
df["Eligible Revenue"] = df["Revenue"].where(eligible_lb_mask, 0.0)

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
    f"Week of {selected_week:%B %d} through {(selected_week + pd.Timedelta(days=6)):%B %d, %Y}. Retail revenue is excluded from pounds and weighted $/LB.",
)
metric_row(
    [
        (f"Weekly Revenue • {delta_text(current_revenue, prior_revenue)}", format_money(current_revenue, 2)),
        (f"Roasted Coffee Lbs • {delta_text(current_lbs, prior_lbs)}", format_number(current_lbs, 1)),
        (f"Weighted $/LB • {delta_text(current_weighted, prior_weighted)}", format_money(current_weighted)),
        (f"Orders • {delta_text(current_orders, prior_orders)}", f"{current_orders:,}"),
        ("Customers", f"{current_customers:,}"),
        (f"Revenue • {four_week_text(current_revenue, prior_four_revenue)}", format_money(prior_four_revenue, 0)),
    ]
)

insights = make_insights(current_row, prior_row, prior_four)
with st.container(border=True):
    st.markdown("#### Weekly Insights")
    for insight in insights:
        st.markdown(f"- {insight}")

# -----------------------------------------------------------------------------
# Weekly trends
# -----------------------------------------------------------------------------
section("Wholesale Sales by Week", "Revenue trend through the selected reporting week.")
st.plotly_chart(revenue_trend_chart(weekly), width='stretch')

section(
    "Sales: Roasted Coffee, Lbs and $/LB",
    "Revenue is shown for all filtered transactions. Lbs and weighted $/LB exclude Retail and rows without positive pounds.",
)
st.plotly_chart(combo_chart(weekly, ""), width='stretch')

# -----------------------------------------------------------------------------
# Channel-specific weekly analysis
# -----------------------------------------------------------------------------
section("Channel Performance", "Weekly revenue, eligible pounds, and weighted $/LB by major channel.")
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
        line_chart(retail_pivot, "Top Retail Locations — Weekly Revenue", "Revenue", currency=True),
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
        line_chart(rep_revenue, "Top 5 Sales Representatives — Weekly Revenue", "Revenue", currency=True),
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
            line_chart(rep_lb_pivot, "Top 5 Sales Representatives — Weighted $/LB", "Weighted $/LB", currency=True),
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

section("Selected Week: Product / Item Pricing")
st.dataframe(
    style_revenue_table(revenue_summary(selected_df, "Item / Memo").head(75)),
    width='stretch',
    hide_index=True,
)

with st.expander("Selected Week Revenue Detail"):
    st.dataframe(selected_df, width='stretch', hide_index=True)

footer()
