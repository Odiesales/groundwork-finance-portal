import streamlit as st
import plotly.express as px
from utils.data import load_revenue_history, revenue_summary, monthly_revenue_summary
from utils.ui import format_money, apply_multiselect_filter, style_revenue_table

st.set_page_config(page_title='Revenue', page_icon='💰', layout='wide')
st.title('💰 Revenue & Pricing')
st.caption('Revenue, pounds sold, weighted $/LB, channel mix, customer pricing, and package-size analysis.')

df = load_revenue_history()
if df.empty:
    st.info('Upload and save a Revenue snapshot in Admin first.')
    st.stop()

st.sidebar.markdown('## Filters')
for label, col in [
    ('Channel', 'Sales Channel'),
    ('Customer', 'Customer'),
    ('Sales Rep', 'Sales Rep'),
    ('Item Class', 'Item Class'),
    ('Coffee Size', 'Coffee Size'),
]:
    df = apply_multiselect_filter(df, label, col)

if df['Trend Date'].notna().any():
    min_date = df['Trend Date'].min().date()
    max_date = df['Trend Date'].max().date()
    date_range = st.sidebar.date_input('Date Range', value=(min_date, max_date), min_value=min_date, max_value=max_date)
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = date_range
        df = df[(df['Trend Date'].dt.date >= start) & (df['Trend Date'].dt.date <= end)]

search = st.sidebar.text_input('Search customer / item')
if search:
    s = search.lower()
    df = df[
        df['Customer'].str.lower().str.contains(s, na=False)
        | df['Item / Memo'].str.lower().str.contains(s, na=False)
    ]

revenue = df['Revenue'].sum()
lbs = df['Lbs'].sum()
weighted = revenue / lbs if lbs else 0
avg_lb = df.loc[df['$/LB'].ne(0), '$/LB'].mean() if not df.empty else 0
rows = len(df)
customers = df['Customer'].nunique()

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric('Revenue', format_money(revenue))
c2.metric('Pounds', f'{lbs:,.1f}')
c3.metric('Weighted $/LB', format_money(weighted))
c4.metric('Avg $/LB', format_money(avg_lb))
c5.metric('Rows', f'{rows:,}')
c6.metric('Customers', f'{customers:,}')

st.divider()
monthly = monthly_revenue_summary(df)
left, right = st.columns(2)
with left:
    st.subheader('Revenue Trend')
    if monthly.empty:
        st.info('No date available for trend chart.')
    else:
        fig = px.bar(monthly, x='Month', y='Revenue', text_auto='.2s')
        st.plotly_chart(fig, use_container_width=True)
with right:
    st.subheader('Weighted $/LB Trend')
    if not monthly.empty:
        fig = px.line(monthly, x='Month', y='Weighted $/LB', markers=True)
        st.plotly_chart(fig, use_container_width=True)

st.subheader('Channel Analysis')
channel = revenue_summary(df, 'Sales Channel')
st.dataframe(style_revenue_table(channel), use_container_width=True, hide_index=True)

left, right = st.columns(2)
with left:
    st.subheader('Coffee Size Analysis')
    st.dataframe(style_revenue_table(revenue_summary(df, 'Coffee Size').head(50)), use_container_width=True, hide_index=True)
with right:
    st.subheader('Sales Rep Performance')
    st.dataframe(style_revenue_table(revenue_summary(df, 'Sales Rep').head(50)), use_container_width=True, hide_index=True)

st.subheader('Top Customers by Revenue')
st.dataframe(style_revenue_table(revenue_summary(df, 'Customer').head(25)), use_container_width=True, hide_index=True)

st.subheader('Product / Item Pricing')
st.dataframe(style_revenue_table(revenue_summary(df, 'Item / Memo').head(50)), use_container_width=True, hide_index=True)

with st.expander('Cleaned Revenue Detail'):
    st.dataframe(df, use_container_width=True, hide_index=True)
