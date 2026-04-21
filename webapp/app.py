#!/usr/bin/env python3
"""Frisco Address Admin — Flask web backend."""

import csv
import io
import os
import sys

import pandas as pd
from flask import (Flask, render_template, request, redirect,
                   url_for, session, send_file, flash)
from flask_login import (LoginManager, UserMixin, login_user,
                         logout_user, login_required, current_user)
from werkzeug.security import generate_password_hash, check_password_hash

# ── Path setup ────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from muslim_filter import is_muslim_name

app = Flask(__name__)
app.secret_key = "frisco-admin-secret-2024"

# ── Auth ──────────────────────────────────────────────────────────────────────
login_manager = LoginManager(app)
login_manager.login_view = "login"

USERS = {
    "admin": generate_password_hash("admin123"),
}

class User(UserMixin):
    def __init__(self, username):
        self.id = username

@login_manager.user_loader
def load_user(user_id):
    if user_id in USERS:
        return User(user_id)
    return None

# ── Data loading ──────────────────────────────────────────────────────────────
def load_all_data():
    zip_files = [
        os.path.join(BASE_DIR, "frisco_75033.csv"),
        os.path.join(BASE_DIR, "frisco_75034.csv"),
        os.path.join(BASE_DIR, "frisco_75036.csv"),
        os.path.join(BASE_DIR, "test_output.csv"),
    ]
    frames = []
    for path in zip_files:
        if os.path.exists(path):
            frames.append(pd.read_csv(path, dtype=str).fillna(""))
    if not frames:
        return pd.DataFrame(columns=["last_name","first_name","address","city_state_zip"])
    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(subset=["address","last_name","first_name"])
    df["is_muslim"] = df.apply(
        lambda r: is_muslim_name(r["last_name"], r["first_name"]), axis=1
    )
    df["zip"] = df["city_state_zip"].str.extract(r'(\d{5})')
    return df

DF = load_all_data()

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
@login_required
def index():
    return redirect(url_for("owners"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if username in USERS and check_password_hash(USERS[username], password):
            login_user(User(username))
            return redirect(url_for("owners"))
        flash("Invalid username or password.")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/owners")
@login_required
def owners():
    df = DF.copy()

    q        = request.args.get("q", "").strip()
    zip_f    = request.args.get("zip", "").strip()
    muslim_f = request.args.get("muslim", "").strip()   # "yes" | "no" | ""
    page     = max(1, int(request.args.get("page", 1)))
    per_page = 50

    if q:
        mask = (
            df["last_name"].str.contains(q, case=False, na=False) |
            df["first_name"].str.contains(q, case=False, na=False) |
            df["address"].str.contains(q, case=False, na=False)
        )
        df = df[mask]
    if zip_f:
        df = df[df["zip"] == zip_f]
    if muslim_f == "yes":
        df = df[df["is_muslim"]]
    elif muslim_f == "no":
        df = df[~df["is_muslim"]]

    total   = len(df)
    pages   = max(1, (total + per_page - 1) // per_page)
    page    = min(page, pages)
    start   = (page - 1) * per_page
    records = df.iloc[start:start + per_page].to_dict("records")

    zip_options = sorted(DF["zip"].dropna().unique())

    return render_template(
        "owners.html",
        records=records,
        total=total,
        page=page,
        pages=pages,
        per_page=per_page,
        q=q,
        zip_f=zip_f,
        muslim_f=muslim_f,
        zip_options=zip_options,
    )


@app.route("/export")
@login_required
def export():
    df = DF.copy()

    q        = request.args.get("q", "").strip()
    zip_f    = request.args.get("zip", "").strip()
    muslim_f = request.args.get("muslim", "").strip()

    if q:
        mask = (
            df["last_name"].str.contains(q, case=False, na=False) |
            df["first_name"].str.contains(q, case=False, na=False) |
            df["address"].str.contains(q, case=False, na=False)
        )
        df = df[mask]
    if zip_f:
        df = df[df["zip"] == zip_f]
    if muslim_f == "yes":
        df = df[df["is_muslim"]]
    elif muslim_f == "no":
        df = df[~df["is_muslim"]]

    out = df[["last_name","first_name","address","city_state_zip","is_muslim"]].copy()
    out.columns = ["Last Name","First Name","Address","City/State/ZIP","Muslim"]

    buf = io.StringIO()
    out.to_csv(buf, index=False)
    buf.seek(0)

    fname = "frisco_export.csv"
    return send_file(
        io.BytesIO(buf.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name=fname,
    )


if __name__ == "__main__":
    print("Starting Frisco Admin at http://127.0.0.1:5000")
    print("Login: admin / admin123")
    app.run(debug=True, port=5000)
