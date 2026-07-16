from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.data import load_ar_history
from utils.ui import YELLOW, CHARCOAL, MUTED, chart_layout, footer, format_money, kpi_row, page_header, section


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
    'Transaction Type':'Invoice', 'Deduction Type':'', 'Open Balance':0, 'Age':0,
    'Document Number':'', 'Memo':'', 'Date':pd.NaT,
}.items():
    if col not in df.columns: df[col] = default

df['Open Balance'] = money_series(df['Open Balance'])
df['Age'] = pd.to_numeric(df['Age'], errors='coerce').fillna(0)
df['Transaction Type Normalized'] = df['Transaction Type'].fillna('').astype(str).str.strip().str.casefold()
df['Deduction Type'] = df['Deduction Type'].fillna('').astype(str).str.strip()
df['Deduction Type Normalized'] = df['Deduction Type'].str.casefold()

# Holdbacks remain invoices. They are available in a separate view but never included in chargeback KPIs.
chargebacks = df[df['Transaction Type Normalized'].eq('chargeback')].copy()
holdbacks = df[(df['Transaction Type Normalized'].eq('invoice')) & (df['Deduction Type Normalized'].eq('holdback'))].copy()

st.markdown('<div class="gw-filter-panel">', unsafe_allow_html=True)
f1,f2,f3,f4,f5 = st.columns([1.35,1,1,1,1])
with f1:
    customers = ['All Customers'] + sorted(chargebacks['Reporting Customer'].dropna().astype(str).unique().tolist())
    customer = st.selectbox('Customer', customers)
with f2:
    channels = ['All Channels'] + sorted(chargebacks['Channel Clean'].dropna().astype(str).unique().tolist())
    channel = st.selectbox('Sales Channel', channels)
with f3:
    deductions = ['All Deduction Types'] + sorted(x for x in chargebacks['Deduction Type'].dropna().astype(str).unique() if x)
    deduction = st.selectbox('Deduction Type', deductions)
with f4:
    reps = ['All Sales Reps'] + sorted(chargebacks['Sales Rep: Name'].dropna().astype(str).unique().tolist())
    rep = st.selectbox('Sales Rep', reps)
with f5:
    view = st.selectbox('View', ['Chargebacks', 'Holdbacks (Invoices)'])
st.markdown('</div>', unsafe_allow_html=True)

base = holdbacks.copy() if view.startswith('Holdbacks') else chargebacks.copy()
if customer != 'All Customers': base = base[base['Reporting Customer'].astype(str).eq(customer)]
if channel != 'All Channels': base = base[base['Channel Clean'].astype(str).eq(channel)]
if deduction != 'All Deduction Types' and not view.startswith('Holdbacks'): base = base[base['Deduction Type'].eq(deduction)]
if rep != 'All Sales Reps': base = base[base['Sales Rep: Name'].astype(str).eq(rep)]

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

selected_name = customer if customer != 'All Customers' else 'All Customers'
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
    hist = hist[hist['Transaction Type Normalized'].eq('chargeback')]
    if customer != 'All Customers': hist = hist[hist['Reporting Customer'].astype(str).eq(customer)]
    if channel != 'All Channels': hist = hist[hist['Channel Clean'].astype(str).eq(channel)]
    if deduction != 'All Deduction Types': hist = hist[hist['Deduction Type'].eq(deduction)]
    if rep != 'All Sales Reps': hist = hist[hist['Sales Rep: Name'].astype(str).eq(rep)]
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
    top = base.groupby('Reporting Customer')['Open Balance'].sum().sort_values(ascending=False).head(10).sort_values()
    fig = go.Figure(go.Bar(x=top.values, y=top.index, orientation='h', marker_color=YELLOW, text=[format_money(v,0) for v in top.values], textposition='outside'))
    fig.update_xaxes(tickformat='$,.0f')
    st.plotly_chart(chart_layout(fig, height=390), width='stretch')
with c2:
    section('Open Balance by Deduction Type', 'Current balance distribution, not YTD activity.')
    by_type = base.groupby('Deduction Type')['Open Balance'].sum().sort_values(ascending=False).head(12).sort_values()
    fig = go.Figure(go.Bar(x=by_type.values, y=by_type.index, orientation='h', marker_color=YELLOW, text=[format_money(v,0) for v in by_type.values], textposition='outside'))
    fig.update_xaxes(tickformat='$,.0f')
    st.plotly_chart(chart_layout(fig, height=390), width='stretch')

section('Chargeback Transactions (Detail)' if not view.startswith('Holdbacks') else 'Holdback Transactions (Detail)', 'Sortable detail supporting the balances above.')
show_cols = [c for c in ['Date','Reporting Customer','Channel Clean','Transaction Type','Deduction Type','Document Number','Memo','Open Balance','Age','Bucket','Sales Rep: Name'] if c in base.columns]
detail = base[show_cols].sort_values('Open Balance', ascending=False).rename(columns={'Reporting Customer':'Customer','Channel Clean':'Sales Channel','Document Number':'Invoice #'})
st.dataframe(detail, width='stretch', hide_index=True, height=520, column_config={
    'Open Balance': st.column_config.NumberColumn('Open Balance', format='$%.2f'),
    'Age': st.column_config.NumberColumn('Age (Days)', format='%.0f'),
})
footer()
