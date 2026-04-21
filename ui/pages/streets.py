import streamlit as st
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import api_client as api

API_BASE = "http://127.0.0.1:8000"

def render():
    st.title("🏘 Streets")

    c1, c2, c3 = st.columns(3)
    zips_r = api.get("/owners/zips")
    zips   = [""] + (zips_r.json() if zips_r.ok else [])
    zip_f  = c1.selectbox("ZIP Code", zips, key="streets_zip")
    muslim_f = c2.selectbox("Show", ["yes","","no"],
                            format_func=lambda x: {"yes":"Muslim Only","":"All","no":"Non-Muslim"}[x],
                            key="streets_muslim")
    q      = c3.text_input("Search street", key="streets_q")

    r = api.get("/streets", params={"zip": zip_f, "muslim": muslim_f, "q": q})
    if not r.ok:
        st.error("Failed to load streets")
        return

    streets = r.json()
    if not streets:
        st.info("No streets found.")
        return

    st.caption(f"**{len(streets)}** streets · **{sum(s['muslim'] for s in streets):,}** Muslim homes")

    df = pd.DataFrame(streets)
    df["% Muslim"] = (df["muslim"] / df["total"] * 100).round(1)
    df = df[["street","zip","muslim","total","visited","% Muslim"]]
    df.columns = ["Street","ZIP","Muslim","Total","Visited","% Muslim"]

    # Show table
    event = st.dataframe(df, use_container_width=True, hide_index=True,
                         on_select="rerun", selection_mode="single-row")

    selected = event.selection.get("rows", []) if hasattr(event, "selection") else []

    if selected:
        row = streets[selected[0]]
        st.markdown(f"### {row['street']} ({row['zip']})")
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Muslim Homes", row["muslim"])
        col_b.metric("Total",        row["total"])
        col_c.metric("Visited",      row["visited"])

        if st.button("🗺 Open Google Maps Route", type="primary"):
            r2 = api.get(f"/streets/{row['street']}/route", params={"zip": row["zip"]})
            if r2.ok and r2.json().get("url"):
                url = r2.json()["url"]
                st.markdown(f"[Open Route ({r2.json()['stops']} stops)]({url})")
                st.link_button("Navigate Now →", url)
            else:
                st.warning("No addresses found for this street.")
