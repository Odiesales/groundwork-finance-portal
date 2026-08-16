import streamlit as st

from utils.ui import inject_global_css
from utils.google_drive import sync_from_drive

st.set_page_config(
    page_title="Groundwork Sales Revenue Portal",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_css()

if "drive_initial_sync_complete" not in st.session_state:
    try:
        sync_from_drive()
        st.session_state["drive_initial_sync_complete"] = True
        st.session_state.pop("drive_initial_sync_error", None)
    except Exception as exc:
        st.session_state["drive_initial_sync_error"] = str(exc)

pages = [
    st.Page("pages/2_Revenue.py", title="Weekly Revenue Report", icon="📈", default=True),
    st.Page("pages/99_Admin.py", title="Administration", icon="⚙️"),
]

nav = st.navigation(pages, position="sidebar")
_ = nav.run()
