from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.data import load_ar_history
from utils.ui import YELLOW, CHARCOAL, MUTED, chart_layout, footer, format_money, kpi_row, page_header, section, sidebar_snapshot


def latest_snapshot(df: pd.DataFrame):
    work = df.copy()
    work['Snapshot Date'] = pd.to_datetime(work.get('Snapshot Date'), errors='coerce')
    dates = work['Snapshot Date'].dropna().dt.normalize()
    if dates.empty:
        return work, None
    as_of = pd.Timestamp(dates.max())
    return work[work['Snapshot Date'].dt.normalize().eq(as_of)].copy(), as_of


def money_series(s):
    return pd.to_numeric(s, errors='coerce').fillna(0)


all_ar = load_ar_history()
df, as_of = latest_snapshot(all_ar)
page_header(
    'Chargebacks by Customer',
    'Open deductions and chargebacks from the selected AR aging snapshot.',
    snapshot_date=as_of,
)

if df.empty:
    st.info('Upload an AR Aging report in Administration to populate Chargebacks.')
    footer(); st.stop()

for col, default in {
    'Reporting Customer':'Unknown', 'Channel Clean':'Unknown', 'Sales Rep: Name':'Unknown',
    'Transaction Type':'Invoice', 'Deduction Type':'', 'Open Balance':0, 'Age':0, 'Bucket':'Unknown',
    'Document Number':'', 'Memo':'', 'Date':pd.NaT,
}.items():
    if col not in df.columns: df[col] = default

df['Open Balance'] = money_series(df['Open Balance'])
df['Age'] = pd.to_numeric(df['Age'], errors='coerce').fillna(0)
df['Bucket'] = df['Bucket'].fillna('Unknown').astype(str).str.strip().replace('', 'Unknown')
df['Transaction Type Normalized'] = df['Transaction Type'].fillna('').astype(str).str.strip().str.casefold()
df['Deduction Type'] = df['Deduction Type'].fillna('').astype(str).str.strip()
df['Deduction Type Normalized'] = df['Deduction Type'].str.casefold()

# Holdbacks remain invoices. They are available in a separate view but never included in chargeback KPIs.
chargebacks = df[df['Transaction Type Normalized'].eq('chargeback')].copy()
holdbacks = df[(df['Transaction Type Normalized'].eq('invoice')) & (df['Deduction Type Normalized'].eq('holdback'))].copy()

sidebar_snapshot(as_of)
st.sidebar.markdown('### Filters')
view = st.sidebar.radio(
    'Record View',
    ['Chargebacks', 'Holdbacks (Invoices)'],
    help='Holdbacks remain invoices and are excluded from chargeback KPIs.',
)
filter_source = holdbacks if view.startswith('Holdbacks') else chargebacks

customers = sorted(filter_source['Reporting Customer'].dropna().astype(str).unique().tolist())
customer = st.sidebar.multiselect('Customer', customers)

deductions = sorted(x for x in filter_source['Deduction Type'].dropna().astype(str).unique() if x)
deduction = st.sidebar.multiselect('Deduction Type', deductions)

channels = sorted(filter_source['Channel Clean'].dropna().astype(str).unique().tolist())
channel = st.sidebar.multiselect('Channel', channels)

reps = sorted(filter_source['Sales Rep: Name'].dropna().astype(str).unique().tolist())
rep = st.sidebar.multiselect('Sales Rep', reps)

buckets = sorted(filter_source['Bucket'].dropna().astype(str).unique().tolist())
bucket = st.sidebar.multiselect('Bucket', buckets)

base = filter_source.copy()
if customer: base = base[base['Reporting Customer'].astype(str).isin(customer)]
if deduction: base = base[base['Deduction Type'].isin(deduction)]
if channel: base = base[base['Channel Clean'].astype(str).isin(channel)]
if rep: base = base[base['Sales Rep: Name'].astype(str).isin(rep)]
if bucket: base = base[base['Bucket'].astype(str).isin(bucket)]

if view.startswith('Holdbacks'):
    section('Open Holdbacks', 'Holdbacks are classified as Invoice with Deduction Type = Holdback and are excluded from chargeback totals.')
else:
    total = base['Open Balance'].sum()
    count = int(base.shape[0])
    avg = total / count if count else 0
    largest_customer = base.groupby('Reporting Customer')['Open Balance'].sum().sort_values(ascending=False)
    largest_type = base.groupby('Deduction Type')['Open Balance'].sum().sort_values(ascending=False)
    avg_age = float(base.loc[base['Open Balance'].ne(0), 'Age'].mean()) if base['Open Balance'].ne(0).any() else 0
    kpi_row([
        {'label':'Open Chargebacks', 'value':format_money(total,2)},
        {'label':'Chargeback Count', 'value':f'{count:,}'},
        {'label':'Average Chargeback', 'value':format_money(avg,2)},
        {'label':'Largest Customer', 'value':largest_customer.index[0] if not largest_customer.empty else '—', 'delta':format_money(largest_customer.iloc[0],2) if not largest_customer.empty else None},
        {'label':'Largest Deduction Type', 'value':largest_type.index[0] if not largest_type.empty else '—', 'delta':format_money(largest_type.iloc[0],2) if not largest_type.empty else None},
        {'label':'Average Age', 'value':f'{avg_age:,.0f} days'},
    ])

if base.empty:
    st.warning('No records match the selected filters.')
    footer(); st.stop()

show_rows = st.selectbox('Chart Rows', ['Top 10', 'Top 25', 'All'], index=0, key='cb_chart_rows')
chart_limit = None if show_rows == 'All' else int(show_rows.split()[-1])
selected_name = ', '.join(customer) if customer else 'All Customers'
section(f'{selected_name} | Open Balance by Deduction Type', f'Balances as of {as_of:%B %d, %Y}' if as_of is not None else 'Current aging snapshot')

# Snapshot matrix. If history exists, display one column per saved snapshot; otherwise current As Of only.
hist = all_ar.copy()
if not hist.empty:
    hist['Snapshot Date'] = pd.to_datetime(hist.get('Snapshot Date'), errors='coerce')
    if 'Deduction Type' not in hist.columns and 'Transaction Reason' in hist.columns:
        hist['Deduction Type'] = hist['Transaction Reason']
    hist['Transaction Type Normalized'] = hist['Transaction Type'].fillna('').astype(str).str.strip().str.casefold()
    hist['Deduction Type'] = hist['Deduction Type'].fillna('').astype(str).str.strip()
    hist['Open Balance'] = money_series(hist['Open Balance'])
    if 'Bucket' not in hist.columns:
        hist['Bucket'] = 'Unknown'
    hist['Bucket'] = hist['Bucket'].fillna('Unknown').astype(str).str.strip().replace('', 'Unknown')
    hist = hist[hist['Transaction Type Normalized'].eq('chargeback')]
    if customer: hist = hist[hist['Reporting Customer'].astype(str).isin(customer)]
    if channel: hist = hist[hist['Channel Clean'].astype(str).isin(channel)]
    if deduction: hist = hist[hist['Deduction Type'].isin(deduction)]
    if rep: hist = hist[hist['Sales Rep: Name'].astype(str).isin(rep)]
    if bucket: hist = hist[hist['Bucket'].astype(str).isin(bucket)]
    hist['As Of'] = hist['Snapshot Date'].dt.strftime('%b-%y')
    matrix = pd.pivot_table(hist, index='Deduction Type', columns='As Of', values='Open Balance', aggfunc='sum', fill_value=0)
else:
    matrix = pd.DataFrame()

if matrix.empty:
    matrix = base.groupby('Deduction Type', dropna=False)['Open Balance'].sum().to_frame('As Of Balance')
# chronological month/snapshot ordering where possible
matrix['As of Total'] = matrix.iloc[:, :].sum(axis=1)
matrix = matrix.sort_values('As of Total', ascending=False)
matrix.loc['Grand Total'] = matrix.sum(axis=0)
st.dataframe(matrix.style.format('${:,.2f}'), width='stretch', height=min(520, 74 + 35*len(matrix)))

c1,c2 = st.columns([1,1], gap='large')
with c1:
    section('Open Chargebacks by Customer', 'Largest customer exposures in the selected aging snapshot.')
    top = base.groupby('Reporting Customer')['Open Balance'].sum().sort_values(ascending=False)
    if chart_limit is not None: top = top.head(chart_limit)
    top = top.sort_values()
    fig = go.Figure(go.Bar(x=top.values, y=top.index, orientation='h', marker_color=YELLOW, text=[format_money(v,2) for v in top.values], textposition='inside', insidetextanchor='middle'))
    fig.update_xaxes(tickformat='$,.2f')
    st.plotly_chart(chart_layout(fig, height=390), width='stretch')
with c2:
    section('Open Balance by Deduction Type', 'Current balance distribution, not YTD activity.')
    by_type = base.groupby('Deduction Type')['Open Balance'].sum().sort_values(ascending=False)
    if chart_limit is not None: by_type = by_type.head(chart_limit)
    by_type = by_type.sort_values()
    fig = go.Figure(go.Bar(x=by_type.values, y=by_type.index, orientation='h', marker_color=YELLOW, text=[format_money(v,2) for v in by_type.values], textposition='inside', insidetextanchor='middle'))
    fig.update_xaxes(tickformat='$,.2f')
    st.plotly_chart(chart_layout(fig, height=390), width='stretch')

st.download_button('⇩ Export Selected Chargebacks', base.to_csv(index=False).encode('utf-8'), f'Chargebacks_{as_of:%Y-%m-%d}.csv' if as_of is not None else 'Chargebacks.csv', 'text/csv')

section('Chargeback Transactions (Detail)' if not view.startswith('Holdbacks') else 'Holdback Transactions (Detail)', 'Sortable detail supporting the balances above.')
show_cols = [c for c in ['Date','Reporting Customer','Channel Clean','Transaction Type','Deduction Type','Document Number','Memo','Open Balance','Age','Bucket','Sales Rep: Name'] if c in base.columns]
detail = base[show_cols].sort_values('Open Balance', ascending=False).rename(columns={'Reporting Customer':'Customer','Channel Clean':'Sales Channel','Document Number':'Invoice #'})
st.dataframe(detail, width='stretch', hide_index=True, height=520, column_config={
    'Open Balance': st.column_config.NumberColumn('Open Balance', format='$%.2f'),
    'Age': st.column_config.NumberColumn('Age (Days)', format='%.0f'),
})
footer()
