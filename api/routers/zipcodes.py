import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import get_current_user
from ..data import BASE_DIR, get_csv_files, get_dataframe, reload_dataframe

router = APIRouter(prefix="/zipcodes", tags=["zipcodes"])


class ZipStatus(BaseModel):
    zip: str
    file: str
    records: int
    loaded: bool


@router.get("", response_model=list[ZipStatus])
def list_zipcodes(_: str = Depends(get_current_user)):
    """Return all ZIP codes that have a downloaded CSV, with record counts."""
    df = get_dataframe()
    counts = df.groupby("zip").size().to_dict() if not df.empty else {}
    result = []
    for p in get_csv_files():
        zip_code = p.stem.replace("frisco_", "")
        result.append(ZipStatus(
            zip=zip_code,
            file=p.name,
            records=int(counts.get(zip_code, 0)),
            loaded=True,
        ))
    return result


@router.post("/reload")
def reload_data(_: str = Depends(get_current_user)):
    """Force a full reload of all CSV data into the in-memory cache."""
    df = reload_dataframe()
    counts = df.groupby("zip").size().to_dict() if not df.empty else {}
    return {"ok": True, "total": len(df), "by_zip": counts}


@router.post("/{zip_code}")
def add_zipcode(zip_code: str, _: str = Depends(get_current_user)):
    """Download data for a ZIP code if not already present, then reload."""
    if not zip_code.isdigit() or len(zip_code) != 5:
        raise HTTPException(400, "ZIP code must be exactly 5 digits")

    csv_path = BASE_DIR / f"frisco_{zip_code}.csv"

    if not csv_path.exists():
        extract_script = BASE_DIR / "extract.py"
        result = subprocess.run(
            [sys.executable, str(extract_script), zip_code, "-o", str(csv_path)],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            raise HTTPException(500, f"Download failed: {result.stderr.strip()}")
        if not csv_path.exists():
            raise HTTPException(500, "Download completed but file not found")

    df = reload_dataframe()
    counts = df.groupby("zip").size().to_dict() if not df.empty else {}
    records = int(counts.get(zip_code, 0))
    return {"ok": True, "zip": zip_code, "records": records, "already_existed": csv_path.exists()}


@router.delete("/{zip_code}")
def remove_zipcode(zip_code: str, _: str = Depends(get_current_user)):
    """Delete a ZIP code's CSV and reload the dataset."""
    if not zip_code.isdigit() or len(zip_code) != 5:
        raise HTTPException(400, "ZIP code must be exactly 5 digits")

    csv_path = BASE_DIR / f"frisco_{zip_code}.csv"
    if not csv_path.exists():
        raise HTTPException(404, "ZIP code data not found")

    csv_path.unlink()
    reload_dataframe()
    return {"ok": True, "zip": zip_code, "removed": True}
