import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import api_client as api

API_BASE = "http://127.0.0.1:8000"

def render():
    st.title("🔗 Shared Links")

    r = api.get("/shares")
    if not r.ok:
        st.error("Failed to load share links")
        return

    tokens = r.json()
    if not tokens:
        st.info("No share links yet. Use the Share button on the Owners page.")
        return

    for t in tokens:
        status = "🔴 Expired" if t["expired"] else "🟢 Active"
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            c1.markdown(f"**{t['label'] or '(no label)'}** &nbsp; {status}")
            c2.caption(f"Created: {t['created_at'][:10]}")
            c3.caption(f"Expires: {t['expires_at'][:10]}")

            if not t["expired"]:
                link = f"{API_BASE}/shares/{t['token']}/data"
                csv_link  = f"{API_BASE}/shares/{t['token']}/download/csv"
                xlsx_link = f"{API_BASE}/shares/{t['token']}/download/xlsx"
                st.code(link, language=None)
                lc1, lc2, lc3 = st.columns([2,1,1])
                lc2.link_button("⬇ CSV",   csv_link,  use_container_width=True)
                lc3.link_button("⬇ Excel", xlsx_link, use_container_width=True)

            if c4.button("Delete", key=f"del_{t['token']}"):
                api.delete(f"/shares/{t['token']}")
                st.rerun()
