"""
verification/reporting/plugin.py

pytest plugin that writes a deterministic results report after every run:
  verification/reports/results_latest.json
  verification/reports/results_latest.csv

Schema:
  {
    "run_at": "<ISO8601 UTC>",
    "summary": {"pass": N, "fail": N, "warn": N, "error": N},
    "checks": [{"id", "category", "status", "message"}, ...]
  }

warn entries come from assert_or_warn() in reporting/models.py.
pass/fail/error entries come from pytest's own outcome tracking.
"""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from verification.reporting.models import clear_warnings, get_warnings

REPORTS_DIR = Path(__file__).parent.parent / "reports"


class VerificationReportPlugin:
    def __init__(self):
        self._results: list[dict] = []

    def pytest_runtest_logreport(self, report):
        if report.when != "call":
            return
        if report.passed:
            status = "pass"
            message = ""
        elif report.failed:
            status = "fail"
            message = str(report.longrepr).splitlines()[-1] if report.longrepr else ""
        else:
            status = "error"
            message = str(report.longrepr).splitlines()[-1] if report.longrepr else ""

        # Extract category from markers
        category = ""
        for marker in ("docs_consistency", "rbac", "legacy_fixture", "known_issue"):
            if marker in str(getattr(report, "keywords", {})):
                category = marker
                break

        self._results.append({
            "id":       report.nodeid,
            "category": category,
            "status":   status,
            "message":  message,
        })

    def pytest_sessionfinish(self, session, exitstatus):
        # Merge warn entries from assert_or_warn()
        for w in get_warnings():
            self._results.append({
                "id":       w.test_id or "warn",
                "category": w.category,
                "status":   "warn",
                "message":  w.message,
            })
        clear_warnings()

        summary = {"pass": 0, "fail": 0, "warn": 0, "error": 0}
        for r in self._results:
            summary[r["status"]] = summary.get(r["status"], 0) + 1

        report = {
            "run_at":  datetime.now(timezone.utc).isoformat(),
            "summary": summary,
            "checks":  self._results,
        }

        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        json_path = REPORTS_DIR / "results_latest.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        csv_path = REPORTS_DIR / "results_latest.csv"
        fieldnames = ["id", "category", "status", "message"]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self._results)


def pytest_configure(config):
    config.pluginmanager.register(VerificationReportPlugin(), "verification_report")
