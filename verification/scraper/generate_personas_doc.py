"""
verification/scraper/generate_personas_doc.py

Generates verification/PERSONAS.md from role_capability_matrix.py +
test_credentials.csv — a human-readable login/password/role/visibility
table for manual UAT. Complements the automated test suite: hand this to
a second pair of eyes and they can walk every role through every page
without reading code.

Usage:
    python -m verification.scraper.generate_personas_doc
"""
import csv
from pathlib import Path

from verification.docs_data.role_capability_matrix import CAPABILITY_MATRIX

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
CREDENTIALS_CSV = FIXTURES_DIR / "test_credentials.csv"
OUTPUT_PATH = Path(__file__).parent.parent / "PERSONAS.md"

# Dojo assignment per persona (mirrors seed_test_org_data --full)
DOJO_BY_USERNAME = {
    "test_coach_a": "Dojo A (WongTaiSin)",
    "test_coach_b": "Dojo B (TaiPo)",
    "test_member_a1": "Dojo A (WongTaiSin)",
    "test_member_a2": "Dojo A (WongTaiSin)",
    "test_member_b1": "Dojo B (TaiPo)",
    "test_member_suspended": "Dojo A (WongTaiSin) — status=SUSPENDED",
    "test_member_inactive": "Dojo A (WongTaiSin) — status=INACTIVE",
}


def _visibility_summary(role: str) -> str:
    """One-line summary of what this role sees, derived from CAPABILITY_MATRIX."""
    scopes = set()
    for view_name, row in CAPABILITY_MATRIX.items():
        scope = row.get(role)
        if scope:
            scopes.add(scope)
    if not scopes:
        return "No CRM access beyond own dashboard"
    if scopes == {"ALL"}:
        return "Org-wide (ALL) access across accessible features"
    parts = []
    if "ALL" in scopes:
        parts.append("ALL on most features")
    if "DOJO" in scopes:
        parts.append("DOJO-scoped on members/events/activities/skills")
    if "OWN" in scopes:
        parts.append("OWN-record-scoped on skills/dashboard")
    return "; ".join(parts) if parts else "See role_capability_matrix.py"


def load_credentials() -> list[dict]:
    with open(CREDENTIALS_CSV, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def render_markdown(rows: list[dict]) -> str:
    lines = [
        "# Verification Suite — Test Personas",
        "",
        "**Generated — do not hand-edit.** Regenerate via:",
        "```",
        "python -m verification.scraper.generate_personas_doc",
        "```",
        "",
        "Human-readable login table for manual UAT. Load into the dev DB first:",
        "```",
        "python manage.py seed_test_users --settings=config.settings.dev",
        "python manage.py seed_test_org_data --full --settings=config.settings.dev",
        "```",
        "",
        "| Username | Password | Role | Dojo / Notes | Expected Visibility |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        username = row["username"]
        dojo_note = DOJO_BY_USERNAME.get(username, row.get("notes", ""))
        visibility = _visibility_summary(row["role"])
        lines.append(
            f"| `{username}` | `{row['password']}` | {row['role']} | {dojo_note} | {visibility} |"
        )
    lines.append("")
    lines.append(
        "See `verification/docs_data/role_capability_matrix.py` for the full "
        "per-feature matrix, and `verification/reports/matrix_diff_report.md` "
        "for every place this diverges from the original aspirational proposal."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    rows = load_credentials()
    OUTPUT_PATH.write_text(render_markdown(rows), encoding="utf-8")
    print(f"Written {len(rows)} personas → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
