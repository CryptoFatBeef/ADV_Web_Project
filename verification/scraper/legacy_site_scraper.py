"""
verification/scraper/legacy_site_scraper.py

One-time CLI script — scrapes ONE URL from the legacy site:
  http://www.advancedtkd.net/Public/Intro_adv  →  fixtures/legacy_org_intro.csv

NEVER invoked by the pytest test suite. Run manually when you need to
refresh the org-intro fixture (rarely — the org description changes infrequently).

TLS NOTE: The legacy host (www.advancedtkd.net) has a cert mismatch —
the cert is issued for dadmin.n2-tech.com, not for advancedtkd.net.
All requests use verify=False with InsecureRequestWarning suppressed.
This is intentional and documented here; do NOT copy this pattern elsewhere.

Usage:
    python -m verification.scraper.legacy_site_scraper [--xlsx]

Flags:
    --xlsx   Also emit fixtures/legacy_org_intro.xlsx alongside the CSV.
"""
import argparse
import csv
import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import requests
import urllib3

from verification.scraper.parsers import (
    parse_founding_year,
    parse_nav_links,
    parse_org_description,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

INTRO_URL = "http://www.advancedtkd.net/Public/Intro_adv"

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
LEGACY_DATA_DIR = FIXTURES_DIR / "legacy_data"
INTRO_CSV = FIXTURES_DIR / "legacy_org_intro.csv"
MANIFEST = FIXTURES_DIR / "_scrape_manifest.json"

PRE_SUPPLIED_FILES = {
    "memebers.csv": None,
    "dojo_event.csv": None,
    "dojo_location.csv": 9,
    "dojo_area.csv": 2,
    "goals.csv": None,
}


def fetch(url: str) -> str:
    print(
        f"\n[WARN] Fetching {url} with SSL verification DISABLED.\n"
        "       Reason: cert is issued for dadmin.n2-tech.com, not advancedtkd.net.\n"
        "       This is a known quirk of this specific legacy host only.\n"
    )
    resp = requests.get(url, verify=False, timeout=30)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text


def scrape_intro() -> list[dict]:
    html = fetch(INTRO_URL)
    now = datetime.now(timezone.utc).isoformat()
    rows = [
        {"field": "founding_year",    "value": parse_founding_year(html) or "NOT FOUND",
         "scraped_at_utc": now, "source_url": INTRO_URL},
        {"field": "org_description",  "value": parse_org_description(html),
         "scraped_at_utc": now, "source_url": INTRO_URL},
    ]
    for link in parse_nav_links(html):
        rows.append({
            "field": f"nav_link:{link['text']}",
            "value": link["href"],
            "scraped_at_utc": now,
            "source_url": INTRO_URL,
        })
    return rows


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["field", "value", "scraped_at_utc", "source_url"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Written {len(rows)} rows → {path}")


def write_xlsx(rows: list[dict], path: Path) -> None:
    try:
        import openpyxl
    except ImportError:
        print("[WARN] openpyxl not installed — skipping .xlsx output")
        return
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "legacy_org_intro"
    headers = ["field", "value", "scraped_at_utc", "source_url"]
    ws.append(headers)
    for row in rows:
        ws.append([row.get(h, "") for h in headers])
    xlsx_path = path.with_suffix(".xlsx")
    wb.save(xlsx_path)
    print(f"  Written {len(rows)} rows → {xlsx_path}")


def build_manifest(rows: list[dict]) -> dict:
    pre_supplied = {}
    for filename, expected_count in PRE_SUPPLIED_FILES.items():
        file_path = LEGACY_DATA_DIR / filename
        actual_count = None
        if file_path.exists():
            with open(file_path, encoding="utf-8-sig") as f:
                actual_count = sum(1 for _ in f) - 1  # subtract header
        pre_supplied[filename] = {
            "source": "Testing Data/legacy_data",
            "row_count": expected_count if expected_count is not None else actual_count,
        }

    scraped_at = next((r["scraped_at_utc"] for r in rows), "")
    return {
        "scraped": {
            "legacy_org_intro.csv": {
                "url": INTRO_URL,
                "scraped_at_utc": scraped_at,
                "row_count": len(rows),
            }
        },
        "pre_supplied": pre_supplied,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape legacy advancedtkd.net intro page")
    parser.add_argument("--xlsx", action="store_true", help="Also write .xlsx mirror")
    args = parser.parse_args()

    print("=== Legacy Site Scraper ===")
    print(f"Target: {INTRO_URL}")

    rows = scrape_intro()
    # Sort for determinism (scraped_at is the only non-deterministic column)
    rows.sort(key=lambda r: r["field"])

    write_csv(rows, INTRO_CSV)
    if args.xlsx:
        write_xlsx(rows, INTRO_CSV)

    manifest = build_manifest(rows)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"  Written manifest → {MANIFEST}")

    print("\nDone. Fixture ready for test suite.")


if __name__ == "__main__":
    main()
