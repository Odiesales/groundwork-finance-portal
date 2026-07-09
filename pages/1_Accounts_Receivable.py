import streamlit as st
import pandas as pd
import plotly.express as px
from utils.paths import CURRENT_AR_PATH, AR_SNAPSHOT_DIR
from utils.data import prep_ar
from utils.ui import format_money, apply_multiselect_filter, style_money_table

st.set_page_config(page_title='Accounts Receivable', page_icon='📊', layout='wide')
st.title('📊 Accounts Receivable')


def snapshot_options():
    options = {}
    if CURRENT_AR_PATH.exists():
        options['Current'] = CURRENT_AR_PATH
    for path in sorted(AR_SNAPSHOT_DIR.glob('ar_*.csv'), reverse=True):
        options[path.stem.replace('ar_', '')] = path
    return options

options = snapshot_options()
if not options:
    st.info('Upload and save an AR snapshot in Admin first.')
    st.stop()

selected = st.sidebar.selectbox('As of Date', list(options.keys()))
df = prep_ar(pd.read_csv(options[selected]))
channel_col = 'Channel Clean' if 'Channel Clean' in df.columns else 'Sales Channel: Name'

st.sidebar.markdown('## Filters')
for label, col in [
    ('Customer', 'Reporting Customer'),
    ('Channel', channel_col),
    ('Sales Rep', 'Sales Rep: Name'),
    ('Terms', 'Terms: Name'),
    ('Bucket', 'Bucket'),
    ('Transaction Type', 'Transaction Type'),
    ('Transaction Reason', 'Transaction Reason'),
]:
    df = apply_multiselect_filter(df, label, col)

search = st.sidebar.text_input('Search customer / memo / document')
if search:
    s = search.lower()
    cols = [c for c in ['Reporting Customer', 'Memo', 'Document Number', 'P.O. No.'] if c in df.columns]
    mask = False
    for col in cols:
        mask = mask | df[col].fillna('').astype(str).str.lower().str.contains(s, na=False)
    df = df[mask]

total_ar = df['Open Balance'].sum()
current_ar = df.loc[df['Bucket'].eq('Current'), 'Open Balance'].sum()
past_due = total_ar - current_ar
over_91 = df.loc[df['Bucket'].eq('91+'), 'Open Balance'].sum()
chargebacks = df.loc[df['Transaction Type'].eq('Chargeback'), 'Open Balance'].sum()
holdbacks = df.loc[df['Transaction Reason'].eq('Holdback'), 'Open Balance'].sum()

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric('Total AR', format_money(total_ar))
c2.metric('Current', format_money(current_ar))
c3.metric('Past Due', format_money(past_due))
c4.metric('91+', format_money(over_91))
c5.metric('Chargebacks', format_money(chargebacks))
c6.metric('Holdbacks', format_money(holdbacks))

st.divider()
left, right = st.columns(2)
with left:
    st.subheader('Aging by Bucket')
    order = ['Current', '1-14', '15-30', '31-60', '61-90', '91+']
    bucket = df.groupby('Bucket', dropna=False)['Open Balance'].sum().reindex(order).fillna(0).reset_index()
    fig = px.bar(bucket, x='Bucket', y='Open Balance', text_auto='.2s')
    st.plotly_chart(fig, use_container_width=True)
with right:
    st.subheader('Top Customers by Open AR')
    top = df.groupby('Reporting Customer', dropna=False)['Open Balance'].sum().sort_values(ascending=False).head(15).reset_index()
    fig = px.bar(top, x='Open Balance', y='Reporting Customer', orientation='h', text_auto='.2s')
    fig.update_layout(yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig, use_container_width=True)

st.subheader('Aging Matrix by Channel')
mat = pd.pivot_table(df, index=channel_col, columns='Bucket', values='Open Balance', aggfunc='sum', fill_value=0)
for bucket in ['Current', '1-14', '15-30', '31-60', '61-90', '91+']:
    if bucket not in mat.columns:
        mat[bucket] = 0
mat = mat[['Current', '1-14', '15-30', '31-60', '61-90', '91+']]
mat['Grand Total'] = mat.sum(axis=1)
st.dataframe(mat.sort_values('Grand Total', ascending=False).style.format('${:,.0f}'), use_container_width=True)

st.subheader('Chargeback Detail')
cb = df[df['Transaction Type'].eq('Chargeback')]
if cb.empty:
    st.info('No chargebacks found for the current filters.')
else:
    by_reason = cb.groupby('Transaction Reason', dropna=False)['Open Balance'].sum().sort_values(ascending=False).reset_index()
    st.dataframe(style_money_table(by_reason), use_container_width=True, hide_index=True)
    st.dataframe(cb, use_container_width=True, hide_index=True)

st.subheader('Transaction Detail')
st.dataframe(df, use_container_width=True, hide_index=True)
