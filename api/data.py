"""Data loading and filtering — loaded once at startup."""
import hashlib
import re
import sys
from pathlib import Path
from functools import lru_cache

import pandas as pd

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))
from muslim_filter import is_muslim_name

CSV_FILES = [
    BASE_DIR / "frisco_75033.csv",
    BASE_DIR / "frisco_75034.csv",
    BASE_DIR / "frisco_75035.csv",
    BASE_DIR / "frisco_75036.csv",
]

def _record_id(rec) -> str:
    key = f"{str(rec.get('last_name','')).lower()}|{str(rec.get('first_name','')).lower()}|{str(rec.get('address','')).strip().upper()}"
    return hashlib.md5(key.encode()).hexdigest()[:16]

def _extract_street(address: str) -> str:
    m = re.match(r'^\d+\s+(.*)', address.strip().upper())
    return m.group(1) if m else address.strip().upper()

@lru_cache(maxsize=1)
def get_dataframe() -> pd.DataFrame:
    frames = [pd.read_csv(p, dtype=str).fillna("") for p in CSV_FILES if p.exists()]
    if not frames:
        return pd.DataFrame(columns=["last_name","first_name","address","city_state_zip"])
    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(subset=["address","last_name","first_name"])
    df["is_muslim"] = df.apply(lambda r: is_muslim_name(r["last_name"], r["first_name"]), axis=1)
    df["zip"]       = df["city_state_zip"].str.extract(r'(\d{5})')
    df["street"]    = df["address"].apply(_extract_street)
    df["rid"]       = df.apply(_record_id, axis=1)
    return df

def record_id_for(last: str, first: str, address: str) -> str:
    return _record_id({"last_name": last, "first_name": first, "address": address})
