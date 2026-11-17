"""
verification/scraper/generate_credentials.py

Deterministic credential generator for the 12-persona test fixture (t0.2.0 v2 —
extended from t0.1.0's 7-row, 1-persona-per-role scheme to support object-level
scoping tests: multiple COACH/MEMBER personas at different dojos).
Writes verification/fixtures/test_credentials.csv (and optionally .xlsx).

Passwords are derived from a fixed, non-secret, dev-only SALT so the CSV
is reproducible byte-for-byte. The generated CSV is local-only and gitignored:
do not commit verification/fixtures/test_credentials.csv (or PERSONAS.md).
  - The accounts only belong in a local DEBUG database, never prod.
  - Usernames are clearly prefixed with "test_".
  - The SALT is not a production secret; it is documented here so the file
    can be regenerated instead of being stored in git.

Usage:
    python -m verification.scraper.generate_credentials [--xlsx]
"""
import argparse
import csv
import hashlib
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
CREDENTIALS_CSV = FIXTURES_DIR / "test_credentials.csv"

# Fixed dev-only salt — NOT a secret, documented intentionally.
_SALT = "adv-tkd-dev-fixture-2026"

# (role, username_suffix, notes) — 12 personas. Username is NOT derived purely
# from role anymore, since COACH/MEMBER have multiple personas at different
# dojos (needed for object-level scoping tests in test_object_level_access.py).
PERSONAS = [
    ("GRANDMASTER",        "grandmaster",        "global"),
    ("DEPUTY_GRANDMASTER", "deputy_grandmaster",  "global"),
    ("ADMIN",              "admin",               "global"),
    ("EDITOR",              "editor",              "cms/chatbot only"),
    ("COACH",               "coach_a",             "HEAD_COACH @ Dojo A (WongTaiSin) — dojo-scoping test persona"),
    ("COACH",               "coach_b",             "HEAD_COACH @ Dojo B (TaiPo) — dojo-scoping test persona"),
    ("MEMBER",              "member_a1",           "MemberProfile @ Dojo A"),
    ("MEMBER",              "member_a2",           "MemberProfile @ Dojo A (peer of a1, for isolation tests)"),
    ("MEMBER",              "member_b1",           "MemberProfile @ Dojo B"),
    ("MEMBER",              "member_suspended",    "status=SUSPENDED — access-denial-edge canary persona"),
    ("MEMBER",              "member_inactive",     "status=INACTIVE — login/visibility-edge canary persona"),
    ("PARENT",              "parent_a",            "no MemberProfile — linkage pending MemberGuardian model"),
]


def _make_password(role: str, username: str) -> str:
    # Digest derived from username (not role alone) so personas sharing a
    # role (the two COACHes, the five MEMBERs) get distinct passwords.
    digest = hashlib.sha256(f"{_SALT}:{username}".encode()).hexdigest()[:12]
    # Format satisfies Django's MinimumLengthValidator (>= 8) and
    # CommonPasswordValidator (not a dictionary word).
    return f"Test-{role[:4]}-{digest}"


def generate_rows() -> list[dict]:
    rows = []
    for role, suffix, notes in PERSONAS:
        username = f"test_{suffix}"
        rows.append({
            "role":      role,
            "username":  username,
            "email":     f"{username}@example.invalid",
            "password":  _make_password(role, username),
            "is_active": "TRUE",
            "notes":     notes,
        })
    return rows


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["role", "username", "email", "password", "is_active", "notes"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Written {len(rows)} credential rows → {path}")


def write_xlsx(rows: list[dict], path: Path) -> None:
    try:
        import openpyxl
    except ImportError:
        print("[WARN] openpyxl not installed — skipping .xlsx output")
        return
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "test_credentials"
    headers = ["role", "username", "email", "password", "is_active", "notes"]
    ws.append(headers)
    for row in rows:
        ws.append([row.get(h, "") for h in headers])
    xlsx_path = path.with_suffix(".xlsx")
    wb.save(xlsx_path)
    print(f"Written {len(rows)} credential rows → {xlsx_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate test_credentials.csv")
    parser.add_argument("--xlsx", action="store_true", help="Also write .xlsx mirror")
    args = parser.parse_args()

    rows = generate_rows()
    write_csv(rows, CREDENTIALS_CSV)
    if args.xlsx:
        write_xlsx(rows, CREDENTIALS_CSV)

    print("\nCredentials generated. Load into dev DB with:")
    print("  python manage.py seed_test_users --settings=config.settings.dev")


if __name__ == "__main__":
    main()
