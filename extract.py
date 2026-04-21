#!/usr/bin/env python3
"""Extract Frisco property owner names and addresses by zip code."""

import csv
import re
import sys
import argparse
import requests

BASE_URL = (
    "https://maps.friscotexas.gov/gis/rest/services/Public"
    "/NotificationParcels/MapServer/2/query"
)
PAGE_SIZE = 2000

ENTITY_KEYWORDS = re.compile(
    r"\b(TRUST|LLC|INC|CORP|LP|LLP|LTD|ASSOC|ASSOCIATION|PARTNERSHIP|"
    r"HOLDINGS|PROPERTIES|REALTY|BANK|FUND|INVESTMENT|GROUP|COMPANY)\b",
    re.IGNORECASE,
)


def fetch_page(zip_code: str, offset: int) -> dict:
    params = {
        "where": f"OWNER_CITY_ST_ZIP LIKE '%{zip_code}%'",
        "outFields": "OWNER_NAME,OWNER_ADDR_LINE1,OWNER_ADDR_LINE2,OWNER_ADDR_LINE3,OWNER_CITY_ST_ZIP",
        "resultRecordCount": PAGE_SIZE,
        "resultOffset": offset,
        "f": "json",
    }
    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def parse_name(raw: str) -> tuple[str, str] | None:
    """Return (last_name, first_name) or None if it looks like an entity."""
    if not raw:
        return None
    raw = raw.strip()
    if ENTITY_KEYWORDS.search(raw):
        return None
    # Take the primary owner (before "&")
    primary = raw.split("&")[0].strip()
    parts = primary.split()
    if not parts:
        return None
    last = parts[0].title()
    first = " ".join(parts[1:]).title() if len(parts) > 1 else ""
    return last, first


def build_address(attrs: dict) -> str:
    line1 = (attrs.get("OWNER_ADDR_LINE1") or "").strip()
    line2 = (attrs.get("OWNER_ADDR_LINE2") or "").strip()
    # LINE1 is sometimes a second owner name — skip if it looks like a name
    # (no digits = likely a name continuation, not an address)
    street = line2 if line2 else line1
    if not street and line1 and any(c.isdigit() for c in line1):
        street = line1
    return street


def extract(zip_code: str, include_entities: bool = False) -> list[dict]:
    records = []
    offset = 0
    print(f"Fetching records for zip {zip_code}...")

    while True:
        data = fetch_page(zip_code, offset)

        if "error" in data:
            print(f"API error: {data['error']}", file=sys.stderr)
            break

        features = data.get("features", [])
        if not features:
            break

        for feat in features:
            attrs = feat.get("attributes", {})
            raw_name = attrs.get("OWNER_NAME", "")
            parsed = parse_name(raw_name)

            if parsed is None:
                if include_entities:
                    records.append({
                        "last_name": raw_name,
                        "first_name": "",
                        "address": build_address(attrs),
                        "city_state_zip": attrs.get("OWNER_CITY_ST_ZIP", ""),
                    })
                continue

            last, first = parsed
            records.append({
                "last_name": last,
                "first_name": first,
                "address": build_address(attrs),
                "city_state_zip": attrs.get("OWNER_CITY_ST_ZIP", ""),
            })

        print(f"  fetched {offset + len(features)} records so far...")

        if len(features) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    return records


def write_csv(records: list[dict], path: str) -> None:
    fields = ["last_name", "first_name", "address", "city_state_zip"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    print(f"Wrote {len(records)} records to {path}")


def main():
    parser = argparse.ArgumentParser(description="Extract Frisco property owner data by zip code.")
    parser.add_argument("zip", help="Zip code to filter by (e.g. 75035)")
    parser.add_argument("-o", "--output", help="Output CSV file (default: frisco_<zip>.csv)")
    parser.add_argument(
        "--include-entities",
        action="store_true",
        help="Include trusts, LLCs, and other non-person entities",
    )
    args = parser.parse_args()

    output = args.output or f"frisco_{args.zip}.csv"
    records = extract(args.zip, include_entities=args.include_entities)

    if not records:
        print("No records found.")
        return

    write_csv(records, output)


if __name__ == "__main__":
    main()
