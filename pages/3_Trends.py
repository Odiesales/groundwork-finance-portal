import streamlit as st
import plotly.express as px
from utils.data import load_revenue_history, load_ar_history, monthly_revenue_summary, yoy_revenue_summary
from utils.ui import style_revenue_table, style_money_table, page_header, section, footer, bar_chart, line_chart

page_header('Trends & Analytics', 'MoM, YoY, YTD, and snapshot history. YoY becomes stronger once last-year snapshots are saved.', badge='Historical')

rev = load_revenue_history(include_current=False)
ar = load_ar_history(include_current=False)

if rev.empty and ar.empty:
    st.info('Save snapshots in Admin first. Trends will appear once historical data exists.')
    st.stop()

if not rev.empty:
    section('Revenue Trends')
    monthly = monthly_revenue_summary(rev)

    c1, c2 = st.columns(2)
    with c1:
        section('Monthly Revenue')
        fig = px.bar(monthly, x='Month', y='Revenue', text_auto='.2s')
        st.plotly_chart(fig, width='stretch')
    with c2:
        section('Monthly Weighted $/LB')
        fig = px.line(monthly, x='Month', y='Weighted $/LB', markers=True)
        st.plotly_chart(fig, width='stretch')

    section('MoM Summary')
    st.dataframe(style_revenue_table(monthly), width='stretch', hide_index=True)

    yoy = yoy_revenue_summary(rev)
    section('YoY Revenue by Month')
    if yoy['Year'].nunique() < 2:
        st.info('YoY will populate after snapshots from more than one year are saved.')
    fig = px.bar(yoy, x='Month', y='Revenue', color='Year', barmode='group')
    st.plotly_chart(fig, width='stretch')

    section('YoY Summary')
    st.dataframe(style_revenue_table(yoy), width='stretch', hide_index=True)

if not ar.empty:
    section('AR Trends')
    ar_summary = ar.groupby('Snapshot Date').agg(Open_AR=('Open Balance', 'sum')).reset_index().sort_values('Snapshot Date')
    fig = px.line(ar_summary, x='Snapshot Date', y='Open_AR', markers=True, title='Open AR by Snapshot')
    st.plotly_chart(fig, width='stretch')
    st.dataframe(style_money_table(ar_summary), width='stretch', hide_index=True)

footer()
