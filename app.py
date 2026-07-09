import streamlit as st
import pandas as pd
from utils.paths import CURRENT_AR_PATH, CURRENT_REVENUE_PATH, AR_SNAPSHOT_DIR, REVENUE_SNAPSHOT_DIR
from utils.data import load_revenue_history, load_ar_history, monthly_revenue_summary
from utils.ui import format_money

st.set_page_config(page_title='Groundwork Finance Portal', page_icon='☕', layout='wide')

st.title('☕ Groundwork Finance Portal')
st.caption('Executive finance dashboards for revenue, pricing, AR, chargebacks, and trends.')

rev = load_revenue_history()
ar = load_ar_history()

ar_snapshots = sorted(AR_SNAPSHOT_DIR.glob('ar_*.csv'), reverse=True)
rev_snapshots = sorted(REVENUE_SNAPSHOT_DIR.glob('revenue_*.csv'), reverse=True)

c1, c2, c3, c4 = st.columns(4)
c1.metric('AR Data', 'Ready' if CURRENT_AR_PATH.exists() or ar_snapshots else 'Not loaded')
c2.metric('Revenue Data', 'Ready' if CURRENT_REVENUE_PATH.exists() or rev_snapshots else 'Not loaded')
c3.metric('AR Snapshots', f'{len(ar_snapshots):,}')
c4.metric('Revenue Snapshots', f'{len(rev_snapshots):,}')

st.divider()

if not rev.empty:
    revenue = rev['Revenue'].sum()
    lbs = rev['Lbs'].sum()
    weighted = revenue / lbs if lbs else 0
    months = monthly_revenue_summary(rev)
    mom = None
    if len(months) >= 2 and months.iloc[-2]['Revenue']:
        mom = (months.iloc[-1]['Revenue'] / months.iloc[-2]['Revenue']) - 1
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Revenue', format_money(revenue), f'{mom:.1%} MoM' if mom is not None else None)
    c2.metric('Pounds Sold', f'{lbs:,.1f}')
    c3.metric('Weighted $/LB', format_money(weighted))
    c4.metric('Customers', f'{rev["Customer"].nunique():,}')
else:
    st.info('Revenue data has not been uploaded yet.')

if not ar.empty:
    total_ar = ar['Open Balance'].sum()
    chargebacks = ar.loc[ar['Transaction Type'].eq('Chargeback'), 'Open Balance'].sum()
    past_due = ar.loc[~ar['Bucket'].eq('Current'), 'Open Balance'].sum()
    c1, c2, c3 = st.columns(3)
    c1.metric('Open AR', format_money(total_ar))
    c2.metric('Past Due AR', format_money(past_due))
    c3.metric('Chargebacks', format_money(chargebacks))
else:
    st.info('AR data has not been uploaded yet.')

st.markdown('### Weekend build workflow')
st.write('1. Upload NetSuite exports in Admin. 2. Save snapshots by week-ending date. 3. Review Revenue, AR, Trends, and Executive views.')
