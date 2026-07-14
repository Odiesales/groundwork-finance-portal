import streamlit as st
import pandas as pd
from datetime import date
from utils.cleaner import clean_uploaded_ar_report, clean_uploaded_revenue_report, convert_df_to_excel
from utils.paths import CURRENT_AR_PATH, CURRENT_REVENUE_PATH, AR_SNAPSHOT_DIR, REVENUE_SNAPSHOT_DIR
from utils.ui import format_money, page_header, section, footer

st.set_page_config(page_title='Admin', page_icon='⚙️', layout='wide')
page_header('Administration', 'Upload weekly NetSuite exports, validate cleaned data, and save dated snapshots for historical reporting.', badge='Data Ops')

snapshot_date = st.date_input('Snapshot / Week Ending Date', value=date.today())

section('Upload Center', 'Choose the week-ending date first, then upload the AR and/or Revenue export.')
left, right = st.columns(2)

with left:
    st.subheader('AR Aging Upload')
    ar_file = st.file_uploader('Upload AR Aging export', type=['xlsx', 'xls', 'csv'], key='ar_upload')
    if ar_file:
        try:
            ar_df = clean_uploaded_ar_report(ar_file)
            ar_df['Snapshot Date'] = snapshot_date.isoformat()
            st.success('AR file cleaned successfully.')
            c1, c2, c3 = st.columns(3)
            c1.metric('Rows', f'{len(ar_df):,}')
            c2.metric('Customers', f'{ar_df["Reporting Customer"].nunique():,}' if 'Reporting Customer' in ar_df else '0')
            c3.metric('Open AR', format_money(ar_df['Open Balance'].sum()) if 'Open Balance' in ar_df else '$0.00')
            if st.button('Save AR Snapshot', type='primary'):
                CURRENT_AR_PATH.parent.mkdir(parents=True, exist_ok=True)
                AR_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
                ar_df.to_csv(CURRENT_AR_PATH, index=False)
                ar_df.to_csv(AR_SNAPSHOT_DIR / f'ar_{snapshot_date:%Y-%m-%d}.csv', index=False)
                st.success('AR snapshot saved.')
            st.download_button('Download Cleaned AR Excel', convert_df_to_excel(ar_df), 'cleaned_ar_report.xlsx')
            st.dataframe(ar_df.head(200), use_container_width=True, hide_index=True)
        except Exception as exc:
            st.error(f'Could not process AR file: {exc}')

with right:
    st.subheader('Revenue Upload')
    rev_file = st.file_uploader('Upload Revenue export', type=['xlsx', 'xls', 'csv'], key='rev_upload')
    if rev_file:
        try:
            rev_df = clean_uploaded_revenue_report(rev_file)
            rev_df['Snapshot Date'] = snapshot_date.isoformat()
            st.success('Revenue file cleaned successfully.')
            revenue = rev_df['Revenue'].sum()
            lbs = rev_df['Lbs'].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric('Rows', f'{len(rev_df):,}')
            c2.metric('Revenue', format_money(revenue))
            c3.metric('Weighted $/LB', format_money(revenue / lbs if lbs else 0))
            if st.button('Save Revenue Snapshot', type='primary'):
                CURRENT_REVENUE_PATH.parent.mkdir(parents=True, exist_ok=True)
                REVENUE_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
                rev_df.to_csv(CURRENT_REVENUE_PATH, index=False)
                rev_df.to_csv(REVENUE_SNAPSHOT_DIR / f'revenue_{snapshot_date:%Y-%m-%d}.csv', index=False)
                st.success('Revenue snapshot saved.')
            st.download_button('Download Cleaned Revenue Excel', convert_df_to_excel(rev_df), 'cleaned_revenue_report.xlsx')
            st.dataframe(rev_df.head(200), use_container_width=True, hide_index=True)
        except Exception as exc:
            st.error(f'Could not process Revenue file: {exc}')

st.divider()
section('Saved Snapshots')
a = pd.DataFrame({'AR Snapshots': [p.name for p in sorted(AR_SNAPSHOT_DIR.glob('ar_*.csv'), reverse=True)]})
r = pd.DataFrame({'Revenue Snapshots': [p.name for p in sorted(REVENUE_SNAPSHOT_DIR.glob('revenue_*.csv'), reverse=True)]})
c1, c2 = st.columns(2)
c1.dataframe(a, use_container_width=True, hide_index=True)
c2.dataframe(r, use_container_width=True, hide_index=True)

footer()
