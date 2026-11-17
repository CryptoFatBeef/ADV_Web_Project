"""
verification/conftest.py

Session-wide fixtures:
  - Manifest validation: fail loudly if any pre_supplied legacy fixture file is missing/empty.
  - Network block: disable all live network calls inside the check suite.
  - seed_test_users_in_db: create the 7 role test users directly in the test DB so RBAC
    matrix tests don't depend on a pre-seeded external dev DB.
  - Django settings are wired via pytest.ini (DJANGO_SETTINGS_MODULE = config.settings.dev).

Register the reporting plugin so results_latest.{json,csv} are written on every run.
"""
import csv
import json
from pathlib import Path

import pytest

# Register the reporting plugin so it is active without needing -p on the CLI.
pytest_plugins = ["verification.reporting.plugin"]

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_FIXTURES_DIR = Path(__file__).parent / "fixtures"
_LEGACY_DATA_DIR = _FIXTURES_DIR / "legacy_data"
_MANIFEST = _FIXTURES_DIR / "_scrape_manifest.json"

_PRE_SUPPLIED_FILES = [
    "memebers.csv",
    "dojo_event.csv",
    "dojo_location.csv",
    "dojo_area.csv",
    "goals.csv",
]

_CREDENTIALS_CSV = _FIXTURES_DIR / "test_credentials.csv"


# ---------------------------------------------------------------------------
# Manifest + pre_supplied fixture validation (session-scoped, autouse)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def validate_legacy_fixtures():
    """
    Fail loudly (not silently) if a present legacy_data directory is incomplete.
    A missing directory is expected on a fresh clone: those CSVs and photos are
    local-only member data and are not in git. Tests that need them skip.
    """
    if not _LEGACY_DATA_DIR.is_dir():
        return

    missing = []
    empty = []
    for filename in _PRE_SUPPLIED_FILES:
        path = _LEGACY_DATA_DIR / filename
        if not path.exists():
            missing.append(str(path))
        elif path.stat().st_size == 0:
            empty.append(str(path))

    if missing:
        pytest.fail(
            "Pre-supplied legacy fixture files are missing — copy them from "
            "'Testing Data/legacy_data/' into 'verification/fixtures/legacy_data/'.\n"
            "Missing:\n" + "\n".join(f"  {p}" for p in missing)
        )
    if empty:
        pytest.fail(
            "Pre-supplied legacy fixture files exist but are empty — "
            "they may be corrupt copies.\n"
            "Empty:\n" + "\n".join(f"  {p}" for p in empty)
        )


# ---------------------------------------------------------------------------
# Test-DB user seeding (session-scoped)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def django_db_setup(django_test_environment, django_db_blocker):
    """
    Override to keep default DB setup; seed_test_users_in_db handles user creation.
    """
    pass


@pytest.fixture(scope="session")
def seed_test_users_in_db(django_db_setup, django_db_blocker):
    """
    Create the 7 role test users in the pytest test DB (not the dev db.sqlite3).
    pytest-django uses a separate test database; seeding the dev DB via management
    commands does not carry over to test runs. This fixture creates the users once
    per session from test_credentials.csv.
    """
    if not _CREDENTIALS_CSV.exists():
        return {}

    with django_db_blocker.unblock():
        from apps.accounts.models import User
        from apps.dojos.models import DojoEntity
        from apps.members.models import BeltLevel, MemberProfile, MemberStatus, MemberTier
        from datetime import date

        # One placeholder dojo for FK requirements
        dojo, _ = DojoEntity.objects.get_or_create(
            slug="verify-test-dojo",
            defaults={
                "name": "Verification Test Dojo",
                "address": "N/A",
                "district": DojoEntity.District.TAI_PO,
                "is_active": True,
            },
        )

        with open(_CREDENTIALS_CSV, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        COACH_ROLES = {"GRANDMASTER", "DEPUTY_GRANDMASTER", "ADMIN", "EDITOR", "COACH"}
        MEMBER_ROLES = {"MEMBER", "PARENT"}

        created = {}
        for row in rows:
            user, _ = User.objects.update_or_create(
                username=row["username"],
                defaults={
                    "email":     row["email"],
                    "role":      row["role"],
                    "is_active": True,
                },
            )
            user.set_password(row["password"])
            user.save(update_fields=["password"])
            created[row["role"]] = user

            if row["role"] in COACH_ROLES:
                from apps.dojos.models import DojoStaff
                DojoStaff.objects.get_or_create(
                    user=user, dojo=dojo,
                    defaults={
                        "role": "HEAD_COACH" if row["role"] == "GRANDMASTER" else "ASSISTANT_COACH",
                        "joined_date": date(2024, 1, 1),
                        "is_active": True,
                        "is_public": False,
                    },
                )
            if row["role"] in MEMBER_ROLES:
                if not MemberProfile.objects.filter(user=user).exists():
                    # member_id keyed by username, not role: v2 credentials have
                    # multiple personas per role (test_member_a1/a2/b1/...), and
                    # deriving from role alone collides on the unique constraint.
                    member_id_suffix = row["username"].removeprefix("test_").upper()
                    MemberProfile.objects.create(
                        user=user,
                        member_id=f"TEST-{member_id_suffix}"[:30],
                        date_of_birth=date(1990, 1, 1),
                        gender="OTHER",
                        emergency_contact_name="N/G",
                        emergency_contact_phone="N/G",
                        current_belt=BeltLevel.WHITE,
                        tier=MemberTier.COLOUR_BELT,
                        status=MemberStatus.ACTIVE,
                        primary_dojo=dojo,
                        joined_date=date(2024, 1, 1),
                    )
        return created


# ---------------------------------------------------------------------------
# Full state-coverage dataset (session-scoped) — t0.2.0
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def seed_full_dataset_in_db(django_db_setup, django_db_blocker):
    """
    Seed the full 14-app state-coverage dataset (2 dojos, 12 personas, every
    enum/FSM state) directly in the pytest test DB, by calling the real
    management commands rather than duplicating their seeding logic.
    Independent of seed_test_users_in_db (left untouched for the original
    135 tests) — tests needing object-level scoping/dojo isolation depend
    on this fixture instead.

    NOTE: pytest-django forces settings.DEBUG=False during test runs (a
    deliberate Django testing best practice — it catches template errors
    that only surface with DEBUG=False). Both management commands guard
    against production use with `if not settings.DEBUG: raise CommandError`.
    That guard's purpose is to stop someone running these against a real
    dev/prod database from the CLI — it says nothing about the isolated,
    throwaway pytest test DB, so it's safe to override DEBUG=True for the
    duration of these two calls only.

    The credential CSV is generated locally and gitignored. A fresh clone
    does not have it; skip the tests that need this dataset instead of
    failing in seed_test_users.
    """
    if not _CREDENTIALS_CSV.is_file():
        pytest.skip(
            "verification/fixtures/test_credentials.csv is absent "
            "(generate it locally with python -m verification.scraper.generate_credentials; "
            "do not commit it)"
        )
    with django_db_blocker.unblock():
        from django.core.management import call_command
        from django.test import override_settings
        with override_settings(DEBUG=True):
            call_command("seed_test_users")
            call_command("seed_test_org_data", "--full")


# ---------------------------------------------------------------------------
# Network block (pytest-socket)
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def block_network(socket_disabled):  # noqa: F811
    """
    Disable all socket access during the check suite.
    Any accidental live-network call inside a check will fail immediately
    rather than causing flaky network-dependent results.
    Provided by pytest-socket; this fixture just makes the disable autouse.
    """
    pass
