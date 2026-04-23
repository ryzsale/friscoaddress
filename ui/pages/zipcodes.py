import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import api_client as api


def render():
    st.title("📍 ZIP Code Management")

    # ── Current ZIPs ───────────────────────────────────────────────────────────
    r = api.get("/zipcodes")
    if r.ok:
        zips = r.json()
    else:
        st.error("Failed to load ZIP codes")
        zips = []

    st.subheader("Loaded ZIP Codes")
    if zips:
        total_records = sum(z["records"] for z in zips)
        st.caption(f"**{len(zips)}** ZIP codes · **{total_records:,}** total records")
        for z in zips:
            col1, col2, col3 = st.columns([2, 2, 1])
            col1.markdown(f"**{z['zip']}**")
            col2.caption(f"{z['records']:,} records — `{z['file']}`")
            if col3.button("Remove", key=f"del_{z['zip']}", type="secondary"):
                dr = api.delete(f"/zipcodes/{z['zip']}")
                if dr.ok:
                    st.success(f"Removed ZIP {z['zip']}")
                    st.rerun()
                else:
                    st.error(f"Failed to remove {z['zip']}")
    else:
        st.info("No ZIP code data loaded yet.")

    st.markdown("---")

    # ── Add new ZIP ────────────────────────────────────────────────────────────
    st.subheader("Add ZIP Code")
    st.caption("If data for the ZIP is not already downloaded, it will be fetched automatically from the Frisco GIS API (may take 1–2 minutes).")

    col_a, col_b = st.columns([2, 1])
    new_zip = col_a.text_input("Enter ZIP Code", placeholder="e.g. 75035", max_chars=5, key="new_zip_input")

    already_loaded = {z["zip"] for z in zips}

    if col_b.button("Save / Download", type="primary", use_container_width=True):
        if not new_zip or not new_zip.isdigit() or len(new_zip) != 5:
            st.error("Please enter a valid 5-digit ZIP code.")
        elif new_zip in already_loaded:
            st.warning(f"ZIP {new_zip} is already loaded ({next(z['records'] for z in zips if z['zip'] == new_zip):,} records).")
        else:
            with st.spinner(f"Downloading data for ZIP {new_zip} — this may take a minute..."):
                pr = api.post(f"/zipcodes/{new_zip}", json={})
            if pr.ok:
                result = pr.json()
                st.success(f"ZIP {new_zip} added — **{result['records']:,}** records loaded.")
                st.rerun()
            else:
                try:
                    detail = pr.json().get("detail", pr.text)
                except Exception:
                    detail = pr.text
                st.error(f"Failed: {detail}")
