import streamlit as st
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import api_client as api

STATUS_OPTIONS = ["", "Muslim", "Non-Muslim", "Not to Visit"]
API_BASE = "http://127.0.0.1:8000"

def render():
    st.title("👥 Owners")

    # ── Filters ────────────────────────────────────────────────────────────────
    with st.expander("🔍 Filters", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        q        = c1.text_input("Search name / address", key="owners_q")
        zips_r   = api.get("/owners/zips")
        zips     = [""] + (zips_r.json() if zips_r.ok else [])
        zip_f    = c2.selectbox("ZIP Code", zips, key="owners_zip")
        muslim_f = c3.selectbox("Auto-Detect", ["", "yes", "no"],
                                format_func=lambda x: {"":"All","yes":"Muslim","no":"Non-Muslim"}[x],
                                key="owners_muslim")
        status_f = c4.selectbox("Status", STATUS_OPTIONS, key="owners_status")

        c5, c6, c7 = st.columns([2,1,1])
        street_f     = c5.text_input("Street filter", key="owners_street")
        show_ignored = c6.checkbox("Show Ignored", key="owners_ignored")
        per_page     = c7.selectbox("Per page", [25, 50, 100], index=1, key="owners_per_page")

    if "owners_page" not in st.session_state:
        st.session_state.owners_page = 1

    # ── Fetch data ─────────────────────────────────────────────────────────────
    r = api.get("/owners", params={
        "q": q, "zip": zip_f, "muslim": muslim_f, "status": status_f,
        "street": street_f, "show_ignored": show_ignored,
        "page": st.session_state.owners_page, "per_page": per_page,
    })
    if not r.ok:
        st.error("Failed to load owners")
        return
    data    = r.json()
    records = data["records"]
    total   = data["total"]
    pages   = data["pages"]
    page    = data["page"]

    st.caption(f"**{total:,}** records · Page {page} of {pages}")

    # ── Export & Share buttons ─────────────────────────────────────────────────
    ecol1, ecol2, ecol3 = st.columns([1, 1, 4])
    params = f"?q={q}&zip={zip_f}&muslim={muslim_f}&status={status_f}&street={street_f}"
    ecol1.link_button("⬇ CSV",   f"{API_BASE}/export/csv{params}")
    ecol2.link_button("⬇ Excel", f"{API_BASE}/export/xlsx{params}")
    with ecol3:
        with st.popover("🔗 Share"):
            share_label = st.text_input("Label", key="share_label")
            share_days  = st.selectbox("Expires in", [1,7,30,90], index=1, key="share_days")
            if st.button("Generate Link", key="gen_share"):
                sr = api.post("/shares", json={
                    "filters": {"q":q,"zip":zip_f,"muslim":muslim_f,"status":status_f,"street":street_f},
                    "label": share_label, "days": share_days,
                })
                if sr.ok:
                    token = sr.json()["token"]
                    st.code(f"{API_BASE}/shares/{token}/data", language=None)
                    st.success("Link created! Share the token above.")
                else:
                    st.error("Failed to create share link")

    # ── Data editor ────────────────────────────────────────────────────────────
    if not records:
        st.info("No records found.")
        return

    df = pd.DataFrame(records)
    df["Auto"] = df["is_muslim"].map({True: "Muslim", False: "Not Confirmed"})

    # pandas 3+ returns datetime64[us]; Streamlit DateColumn requires datetime64[ns]
    df["last_visited"] = pd.to_datetime(df["last_visited"], errors="coerce").astype("datetime64[ns]")

    display_cols = ["last_name","first_name","address","city_state_zip","Auto","status","last_visited","comments","ignored"]
    col_config = {
        "last_name":      st.column_config.TextColumn("Last Name",    disabled=True),
        "first_name":     st.column_config.TextColumn("First Name",   disabled=True),
        "address":        st.column_config.TextColumn("Address",      disabled=True, width="large"),
        "city_state_zip": st.column_config.TextColumn("City/ZIP",     disabled=True),
        "Auto":           st.column_config.TextColumn("Auto",         disabled=True),
        "status":         st.column_config.SelectboxColumn("Status",  options=STATUS_OPTIONS),
        "last_visited":   st.column_config.DateColumn("Last Visited"),
        "comments":       st.column_config.TextColumn("Comments",     width="medium"),
        "ignored":        st.column_config.CheckboxColumn("Ignore"),
    }

    edited = st.data_editor(
        df[display_cols], column_config=col_config,
        use_container_width=True, hide_index=True, key="owners_editor",
    )

    # Save changes — convert date back to ISO string for the API
    changed = df[display_cols].compare(edited, result_names=("orig","new"))
    if not changed.empty:
        for idx in changed.index.get_level_values(0).unique():
            rid = df.loc[idx, "rid"]
            row = edited.loc[idx]
            lv  = row["last_visited"].isoformat() if pd.notna(row["last_visited"]) else ""
            r2  = api.patch(f"/annotations/{rid}", json={
                "status":       row["status"] or "",
                "last_visited": lv,
                "comments":     row["comments"] or "",
                "ignored":      int(row["ignored"]),
            })
            if r2.ok:
                st.toast(f"Saved {df.loc[idx,'last_name']}", icon="✅")

    # Google Maps links
    st.markdown("**Navigate:**")
    for rec in records[:10]:
        addr = f"{rec['address']}, {rec['city_state_zip']}"
        from urllib.parse import quote_plus
        url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(addr)}"
        st.markdown(f"📍 [{rec['address']}]({url})")

    # ── Pagination ─────────────────────────────────────────────────────────────
    pc1, pc2, pc3 = st.columns([1,2,1])
    if pc1.button("◀ Prev", disabled=(page<=1)):
        st.session_state.owners_page = max(1, page - 1)
        st.rerun()
    pc2.markdown(f"<div style='text-align:center;padding-top:8px'>Page {page} of {pages}</div>", unsafe_allow_html=True)
    if pc3.button("Next ▶", disabled=(page>=pages)):
        st.session_state.owners_page = page + 1
        st.rerun()
