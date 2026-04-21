#!/usr/bin/env python3
"""Frisco Address Admin — Flask web backend."""

import csv
import hashlib
import io
import os
import sqlite3
import sys

import pandas as pd
from flask import (Flask, render_template, request, redirect,
                   url_for, send_file, flash, jsonify)
from flask_login import (LoginManager, UserMixin, login_user,
                         logout_user, login_required, current_user)
from werkzeug.security import generate_password_hash, check_password_hash
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

# ── Path setup ────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "annotations.db")
sys.path.insert(0, BASE_DIR)
from muslim_filter import is_muslim_name

from urllib.parse import quote_plus

app = Flask(__name__)
app.secret_key = "frisco-admin-secret-2024"
app.jinja_env.filters["urlencode"] = quote_plus

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

# ── SQLite annotations ────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS annotations (
                rid          TEXT PRIMARY KEY,
                last_visited TEXT DEFAULT '',
                comments     TEXT DEFAULT '',
                status       TEXT DEFAULT '',
                ignored      INTEGER DEFAULT 0
            )
        """)
        conn.commit()

def record_id(rec):
    key = f"{str(rec.get('last_name','')).lower()}|{str(rec.get('first_name','')).lower()}|{str(rec.get('address','')).strip().upper()}"
    return hashlib.md5(key.encode()).hexdigest()[:16]

def get_annotations(rids: list[str]) -> dict:
    if not rids:
        return {}
    with get_db() as conn:
        placeholders = ",".join("?" * len(rids))
        rows = conn.execute(
            f"SELECT * FROM annotations WHERE rid IN ({placeholders})", rids
        ).fetchall()
    return {r["rid"]: dict(r) for r in rows}

def upsert_annotation(rid, field, value):
    allowed = {"last_visited", "comments", "status", "ignored"}
    if field not in allowed:
        return
    with get_db() as conn:
        conn.execute(f"""
            INSERT INTO annotations (rid, {field}) VALUES (?, ?)
            ON CONFLICT(rid) DO UPDATE SET {field}=excluded.{field}
        """, (rid, value))
        conn.commit()

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
        return pd.DataFrame(columns=["last_name", "first_name", "address", "city_state_zip"])
    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(subset=["address", "last_name", "first_name"])
    df["is_muslim"] = df.apply(lambda r: is_muslim_name(r["last_name"], r["first_name"]), axis=1)
    df["zip"] = df["city_state_zip"].str.extract(r'(\d{5})')
    df["rid"] = df.apply(record_id, axis=1)
    return df

init_db()
DF = load_all_data()

# ── Helpers ───────────────────────────────────────────────────────────────────
STATUS_OPTIONS = ["", "Muslim", "Non-Muslim", "Not to Visit"]

def apply_filters(df, q, zip_f, muslim_f, status_f, show_ignored):
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
    if status_f:
        rids = df["rid"].tolist()
        ann  = get_annotations(rids)
        df = df[df["rid"].apply(lambda r: ann.get(r, {}).get("status", "") == status_f)]
    if not show_ignored:
        rids = df["rid"].tolist()
        ann  = get_annotations(rids)
        df = df[df["rid"].apply(lambda r: not ann.get(r, {}).get("ignored", 0))]
    return df

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
    q            = request.args.get("q", "").strip()
    zip_f        = request.args.get("zip", "").strip()
    muslim_f     = request.args.get("muslim", "").strip()
    status_f     = request.args.get("status", "").strip()
    show_ignored = request.args.get("show_ignored", "") == "1"
    page         = max(1, int(request.args.get("page", 1)))
    per_page     = 50

    df    = apply_filters(DF.copy(), q, zip_f, muslim_f, status_f, show_ignored)
    total = len(df)
    pages = max(1, (total + per_page - 1) // per_page)
    page  = min(page, pages)
    start = (page - 1) * per_page
    slice_df = df.iloc[start:start + per_page]

    rids = slice_df["rid"].tolist()
    ann  = get_annotations(rids)
    records = []
    for rec in slice_df.to_dict("records"):
        a = ann.get(rec["rid"], {})
        rec["last_visited"] = a.get("last_visited", "")
        rec["comments"]     = a.get("comments", "")
        rec["status"]       = a.get("status", "")
        rec["ignored"]      = bool(a.get("ignored", 0))
        records.append(rec)

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
        status_f=status_f,
        show_ignored=show_ignored,
        zip_options=sorted(DF["zip"].dropna().unique()),
        status_options=STATUS_OPTIONS,
    )


@app.route("/annotate/<rid>", methods=["POST"])
@login_required
def annotate(rid):
    data = request.get_json(force=True)
    for field, value in data.items():
        upsert_annotation(rid, field, value)
    return jsonify(ok=True)


@app.route("/export")
@login_required
def export():
    q            = request.args.get("q", "").strip()
    zip_f        = request.args.get("zip", "").strip()
    muslim_f     = request.args.get("muslim", "").strip()
    status_f     = request.args.get("status", "").strip()
    fmt          = request.args.get("fmt", "csv")

    # Ignored records are always excluded from exports
    df = apply_filters(DF.copy(), q, zip_f, muslim_f, status_f, show_ignored=False)

    rids = df["rid"].tolist()
    ann  = get_annotations(rids)

    rows = []
    for rec in df.to_dict("records"):
        a = ann.get(rec["rid"], {})
        rows.append({
            "Last Name":       rec["last_name"],
            "First Name":      rec["first_name"],
            "Address":         rec["address"],
            "City/State/ZIP":  rec["city_state_zip"],
            "Auto-Detected":   "Muslim" if rec["is_muslim"] else "Other",
            "Status":          a.get("status", ""),
            "Last Visited":    a.get("last_visited", ""),
            "Comments":        a.get("comments", ""),
        })

    if fmt == "xlsx":
        return export_xlsx(rows)

    out_df = pd.DataFrame(rows)
    buf = io.StringIO()
    out_df.to_csv(buf, index=False)
    buf.seek(0)
    return send_file(
        io.BytesIO(buf.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="frisco_export.csv",
    )


def export_xlsx(rows):
    HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
    HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
    ALT_FILL    = PatternFill("solid", fgColor="D6E4F0")

    wb = Workbook()
    ws = wb.active
    ws.title = "Frisco Export"

    headers = ["Last Name","First Name","Address","City/State/ZIP",
               "Auto-Detected","Status","Last Visited","Comments"]
    widths  = [20, 22, 36, 26, 14, 16, 16, 40]

    ws.append(headers)
    for col_idx, (h, w) in enumerate(zip(headers, widths), start=1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center")
        ws.column_dimensions[get_column_letter(col_idx)].width = w

    for row_num, r in enumerate(rows, start=2):
        ws.append([r[h] for h in headers])
        if row_num % 2 == 0:
            for cell in ws[row_num]:
                cell.fill = ALT_FILL

    ws.auto_filter.ref = ws.dimensions
    ws.freeze_panes = "A2"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     as_attachment=True, download_name="frisco_export.xlsx")


if __name__ == "__main__":
    print("Starting Frisco Admin at http://127.0.0.1:5000")
    print("Login: admin / admin123")
    app.run(debug=True, port=5000)
