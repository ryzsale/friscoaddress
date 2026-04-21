import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import api_client as api

def render():
    st.title("📊 Dashboard")
    r = api.get("/owners/dashboard")
    if not r.ok:
        st.error("Failed to load dashboard")
        return
    d = r.json()

    # KPI row
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Owners",   f"{d['total']:,}")
    c2.metric("Muslim (auto)",  f"{d['muslim']:,}")
    c3.metric("Non-Muslim",     f"{d['non_muslim']:,}")
    c4.metric("Visited",        f"{d['visited']:,}")
    c5.metric("Ignored",        f"{d['ignored']:,}")

    st.markdown("---")
    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.subheader("Status Breakdown")
        sc = d["status_counts"]
        total = d["total"] or 1
        for label, count in sc.items():
            pct = count / total * 100
            st.markdown(f"**{label}** — {count:,}")
            st.progress(pct / 100)

    with col_right:
        st.subheader("By ZIP Code")
        import pandas as pd
        df = pd.DataFrame(d["zip_stats"])
        if not df.empty:
            df["muslim"] = df["muslim"].astype(int)
            df["total"]  = df["total"].astype(int)
            df["% Muslim"] = (df["muslim"] / df["total"] * 100).round(1)
            df.columns = [c.title() if c != "% Muslim" else c for c in df.columns]
            st.dataframe(df, use_container_width=True, hide_index=True)
