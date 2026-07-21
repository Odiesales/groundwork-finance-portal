import pandas as pd
import streamlit as st

from utils.paths import CURRENT_AR_PATH
from utils.data import ar_snapshot_files
from utils.ui import inject_global_css, sidebar_snapshot

st.set_page_config(
    page_title="Groundwork Coffee Roasters Finance Portal",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded",
)

def current_snapshot_date():
    snapshots = ar_snapshot_files()
    if snapshots:
        return snapshots[0][0]
    try:
        if CURRENT_AR_PATH.exists():
            df = pd.read_csv(CURRENT_AR_PATH, usecols=lambda c: c == "Snapshot Date")
            dates = pd.to_datetime(df.get("Snapshot Date"), errors="coerce").dropna()
            if not dates.empty:
                return dates.max()
    except Exception:
        pass
    return None

inject_global_css()

pages = [
    st.Page("pages/0_Executive_Scorecard.py", title="Executive Scorecard", icon="🏠", default=True),
    st.Page("pages/1_Accounts_Receivable.py", title="Accounts Receivable", icon="💰"),
    st.Page("pages/2_Chargebacks.py", title="Chargebacks", icon="🏷️"),
    st.Page("pages/2_Revenue.py", title="Weekly Revenue Report", icon="📈"),
    st.Page("pages/3_Trends.py", title="Trends", icon="📊"),
    st.Page("pages/99_Admin.py", title="Administration", icon="⚙️"),
]

nav = st.navigation(pages, position="sidebar")
sidebar_snapshot(current_snapshot_date())
nav.run()
