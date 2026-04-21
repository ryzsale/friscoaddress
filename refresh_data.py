#!/usr/bin/env python3
"""Refresh all Frisco zip code data and rebuild the combined Excel."""

import os
import sys
import logging
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

LOG_FILE = os.path.join(BASE_DIR, "refresh.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

ZIPS = ["75033", "75034", "75035", "75036"]

def main():
    log.info("=== Data refresh started ===")

    from extract import extract, write_csv

    for z in ZIPS:
        out = os.path.join(BASE_DIR, f"frisco_{z}.csv")
        try:
            records = extract(z)
            if records:
                write_csv(records, out)
                log.info(f"  {z}: {len(records)} records → {out}")
            else:
                log.warning(f"  {z}: no records returned, keeping existing file")
        except Exception as e:
            log.error(f"  {z}: fetch failed — {e}")

    # Use test_output.csv as alias for 75035 if frisco_75035.csv was written
    frisco_35 = os.path.join(BASE_DIR, "frisco_75035.csv")
    test_out  = os.path.join(BASE_DIR, "test_output.csv")
    if os.path.exists(frisco_35):
        import shutil
        shutil.copy2(frisco_35, test_out)
        log.info("  Synced frisco_75035.csv → test_output.csv")

    log.info("=== Refresh complete ===")

if __name__ == "__main__":
    main()
