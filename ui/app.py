"""Frisco Address Admin — Streamlit UI (pure Python, no HTML templates)."""
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import api_client as api

st.set_page_config(
    page_title="Frisco Admin",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Auth gate ──────────────────────────────────────────────────────────────────
if not api.is_logged_in():
    st.markdown("## 🏠 Frisco Address Admin")
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.form("login_form"):
            st.subheader("Sign In")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login", use_container_width=True):
                if api.login(username, password):
                    st.rerun()
                else:
                    st.error("Invalid username or password")
    st.stop()

# ── Sidebar nav ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏠 Frisco Admin")
    st.markdown(f"Logged in as **{st.session_state.get('username')}**")
    st.markdown("---")
    page = st.radio("Navigate", ["📊 Dashboard", "👥 Owners", "🏘 Streets", "🔗 Shared Links"], label_visibility="collapsed")
    st.markdown("---")
    if st.button("Logout", use_container_width=True):
        api.logout()
        st.rerun()

# ── Pages ──────────────────────────────────────────────────────────────────────
if page == "📊 Dashboard":
    import pages.dashboard as pg
elif page == "👥 Owners":
    import pages.owners as pg
elif page == "🏘 Streets":
    import pages.streets as pg
elif page == "🔗 Shared Links":
    import pages.shares as pg

pg.render()
