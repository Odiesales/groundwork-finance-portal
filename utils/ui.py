import pandas as pd
import streamlit as st


def format_money(value):
    try:
        return '${:,.2f}'.format(float(value))
    except Exception:
        return '$0.00'


def metric_row(metrics):
    cols = st.columns(len(metrics))
    for col, (label, value, delta) in zip(cols, metrics):
        col.metric(label, value, delta=delta)


def apply_multiselect_filter(df, label, column, sidebar=True):
    if column not in df.columns:
        return df
    target = st.sidebar if sidebar else st
    values = sorted(df[column].fillna('Unknown').astype(str).unique())
    selected = target.multiselect(label, values, key=f'filter_{label}_{column}')
    if selected:
        return df[df[column].fillna('Unknown').astype(str).isin(selected)]
    return df


def style_revenue_table(df):
    formats = {
        'Revenue': '${:,.0f}',
        'Lbs': '{:,.1f}',
        'Weighted $/LB': '${:,.2f}',
        'Avg $/LB': '${:,.2f}',
        'Mix %': '{:.1%}',
        'MoM Revenue %': '{:.1%}',
        'YoY Revenue %': '{:.1%}',
        'MoM $/LB %': '{:.1%}',
        'YoY $/LB %': '{:.1%}',
    }
    valid = {k: v for k, v in formats.items() if k in df.columns}
    return df.style.format(valid)


def style_money_table(df):
    money_cols = [c for c in df.columns if any(x in c.lower() for x in ['balance', 'revenue', 'amount', 'open_ar'])]
    fmt = {c: '${:,.0f}' for c in money_cols}
    return df.style.format(fmt)
