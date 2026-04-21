"""HTTP client for the FastAPI backend."""
import requests
import streamlit as st

API_BASE = "http://127.0.0.1:8000"

def _headers():
    token = st.session_state.get("token", "")
    return {"Authorization": f"Bearer {token}"} if token else {}

def post(path, **kwargs):
    return requests.post(f"{API_BASE}{path}", headers=_headers(), **kwargs)

def get(path, **kwargs):
    return requests.get(f"{API_BASE}{path}", headers=_headers(), **kwargs)

def patch(path, **kwargs):
    return requests.patch(f"{API_BASE}{path}", headers=_headers(), **kwargs)

def delete(path, **kwargs):
    return requests.delete(f"{API_BASE}{path}", headers=_headers(), **kwargs)

def login(username: str, password: str) -> bool:
    r = requests.post(f"{API_BASE}/auth/token", json={"username": username, "password": password})
    if r.ok:
        st.session_state["token"]    = r.json()["access_token"]
        st.session_state["username"] = username
        return True
    return False

def is_logged_in() -> bool:
    return bool(st.session_state.get("token"))

def logout():
    st.session_state.pop("token", None)
    st.session_state.pop("username", None)
