import streamlit as st
import plotly.express as px
from utils.data import load_revenue_history, load_ar_history, monthly_revenue_summary, revenue_summary
from utils.ui import format_money, style_revenue_table, style_money_table

st.set_page_config(page_title='Executive Summary', page_icon='🏠', layout='wide')
st.title('🏠 Executive Summary')
st.caption('High-level revenue, pricing, and AR performance.')

rev = load_revenue_history()
ar = load_ar_history()

if rev.empty and ar.empty:
    st.info('Upload and save at least one AR or Revenue snapshot in Admin first.')
    st.stop()

if not rev.empty:
    revenue = rev['Revenue'].sum()
    lbs = rev['Lbs'].sum()
    weighted = revenue / lbs if lbs else 0
    months = monthly_revenue_summary(rev)
    latest_mom = None
    if len(months) >= 2 and months.iloc[-2]['Revenue']:
        latest_mom = (months.iloc[-1]['Revenue'] / months.iloc[-2]['Revenue']) - 1
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Revenue', format_money(revenue), f'{latest_mom:.1%} MoM' if latest_mom is not None else None)
    c2.metric('Pounds Sold', f'{lbs:,.1f}')
    c3.metric('Weighted $/LB', format_money(weighted))
    c4.metric('Customers', f'{rev["Customer"].nunique():,}')

if not ar.empty:
    total_ar = ar['Open Balance'].sum()
    current_ar = ar.loc[ar['Bucket'].eq('Current'), 'Open Balance'].sum()
    past_due = total_ar - current_ar
    chargebacks = ar.loc[ar['Transaction Type'].eq('Chargeback'), 'Open Balance'].sum()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Open AR', format_money(total_ar))
    c2.metric('Current AR', format_money(current_ar))
    c3.metric('Past Due AR', format_money(past_due))
    c4.metric('Chargebacks', format_money(chargebacks))

st.divider()

if not rev.empty:
    left, right = st.columns(2)
    with left:
        st.subheader('Monthly Revenue')
        monthly = monthly_revenue_summary(rev)
        if not monthly.empty:
            fig = px.bar(monthly, x='Month', y='Revenue', text_auto='.2s')
            st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader('Weighted $/LB')
        if not monthly.empty:
            fig = px.line(monthly, x='Month', y='Weighted $/LB', markers=True)
            st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns(2)
    with left:
        st.subheader('Channel Mix')
        channel = revenue_summary(rev, 'Sales Channel')
        st.dataframe(style_revenue_table(channel.head(10)), use_container_width=True, hide_index=True)
    with right:
        st.subheader('Top Customers')
        customer = revenue_summary(rev, 'Customer')
        st.dataframe(style_revenue_table(customer.head(10)), use_container_width=True, hide_index=True)

if not ar.empty:
    st.subheader('AR by Aging Bucket')
    ar_bucket = ar.groupby('Bucket', dropna=False)['Open Balance'].sum().reset_index().sort_values('Open Balance', ascending=False)
    st.dataframe(style_money_table(ar_bucket), use_container_width=True, hide_index=True)
