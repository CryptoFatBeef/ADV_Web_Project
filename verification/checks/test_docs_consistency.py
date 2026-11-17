"""
verification/checks/test_docs_consistency.py

Documentation-vs-code consistency checks.
These assert that the running codebase matches what README.md / DEBUGLOG.md /
Blueprint v0.7.1 claim. All tests are @pytest.mark.docs_consistency.

IMPORTANT: 'warn' outcomes use assert_or_warn() from reporting/models.py.
They record a warning without failing the test, since some checks (tier pricing)
can only compare comment text, not real model data.
"""
import re
from pathlib import Path

import pytest
import django.apps as _django_apps_module
from django.apps import apps as django_apps
from django.urls import NoReverseMatch, reverse

from apps.accounts.models import User
from apps.dojos.models import DojoEntity
from apps.members.models import MemberTier

from verification.docs_data import blueprint_districts, readme_member_tiers, readme_roles, readme_url_structure
from verification.reporting.models import assert_or_warn

# ---------------------------------------------------------------------------
# 1. App count — FIRST test in the file (pins the authoritative 14-app count)
# ---------------------------------------------------------------------------

EXPECTED_PROJECT_APPS = {
    "accounts", "members", "dojos", "events", "activities",
    "skills", "fees", "payments", "communications", "cms",
    "matches", "chatbot", "public", "enrollment",
}


@pytest.mark.docs_consistency
@pytest.mark.django_db
def test_installed_app_count_matches_docs():
    """
    Verifies installed project apps (under apps/) match EXPECTED_PROJECT_APPS (14).

    Fails if:
      - an app is added to INSTALLED_APPS without updating README.md and this list
      - an app is removed without updating this list

    NOTE: README.md Changelog says "12 apps" — that figure is the pre-v0.3.1 scope
    (before public + enrollment were added in v0.3.1). The authoritative current count
    is 14 per the Architecture tree in README.md.

    NOTE: 'activities' is intentionally included even though it is missing from
    README.md's Django Apps responsibility table — that omission is a known README
    inconsistency. This test surfaces it explicitly.
    """
    installed = {
        cfg.label
        for cfg in django_apps.get_app_configs()
        if cfg.name.startswith("apps.")
    }
    assert installed == EXPECTED_PROJECT_APPS, (
        f"Installed project apps don't match docs (expected 14).\n"
        f"  Extra (in code, not in docs):    {sorted(installed - EXPECTED_PROJECT_APPS)}\n"
        f"  Missing (in docs, not installed): {sorted(EXPECTED_PROJECT_APPS - installed)}\n"
        "Update EXPECTED_PROJECT_APPS and README.md's Architecture tree together."
    )


# ---------------------------------------------------------------------------
# 2. Role list
# ---------------------------------------------------------------------------

@pytest.mark.docs_consistency
@pytest.mark.django_db
def test_user_roles_match_docs():
    """User.Role enum values match the roles documented in README.md."""
    code_roles = set(User.Role.values)
    doc_roles = set(readme_roles.ROLES)
    assert code_roles == doc_roles, (
        f"User.Role mismatch.\n"
        f"  In code, not in docs: {code_roles - doc_roles}\n"
        f"  In docs, not in code: {doc_roles - code_roles}\n"
        "Update verification/docs_data/readme_roles.py to match apps/accounts/models.py."
    )


# ---------------------------------------------------------------------------
# 3. District enum
# ---------------------------------------------------------------------------

@pytest.mark.docs_consistency
@pytest.mark.django_db
def test_dojo_district_enum_matches_model():
    """
    DojoEntity.District values match blueprint_districts.DISTRICTS.
    SOURCE: apps/dojos/models.py (not the Blueprint PDF — that doc doesn't list them).
    """
    code_districts = set(DojoEntity.District.values)
    doc_districts = set(blueprint_districts.DISTRICTS)
    assert code_districts == doc_districts, (
        f"DojoEntity.District mismatch.\n"
        f"  In code, not in docs_data: {code_districts - doc_districts}\n"
        f"  In docs_data, not in code: {doc_districts - code_districts}\n"
        "Update verification/docs_data/blueprint_districts.py to match apps/dojos/models.py."
    )


# ---------------------------------------------------------------------------
# 4. URL structure
# ---------------------------------------------------------------------------

@pytest.mark.docs_consistency
@pytest.mark.django_db
def test_public_url_structure_matches_docs():
    """Public URLs documented in README.md resolve correctly via Django's reverse()."""
    errors = []
    for url_name, expected_path in readme_url_structure.PUBLIC_URLS:
        try:
            actual = reverse(url_name)
        except NoReverseMatch as e:
            errors.append(f"  {url_name}: NoReverseMatch — {e}")
            continue
        if actual != expected_path:
            errors.append(f"  {url_name}: expected '{expected_path}', got '{actual}'")
    assert not errors, "Public URL structure diverged from README.md:\n" + "\n".join(errors)


@pytest.mark.docs_consistency
@pytest.mark.django_db
def test_auth_url_structure_matches_docs():
    """Auth URLs documented in README.md resolve correctly via Django's reverse()."""
    errors = []
    for url_name, expected_path in readme_url_structure.AUTH_URLS:
        try:
            actual = reverse(url_name)
        except NoReverseMatch as e:
            errors.append(f"  {url_name}: NoReverseMatch — {e}")
            continue
        if actual != expected_path:
            errors.append(f"  {url_name}: expected '{expected_path}', got '{actual}'")
    assert not errors, "Auth URL structure diverged from README.md:\n" + "\n".join(errors)


# ---------------------------------------------------------------------------
# 5. Member tier pricing — WARN-LEVEL only
# ---------------------------------------------------------------------------

@pytest.mark.docs_consistency
def test_member_tier_pricing_comment_matches_docs():
    """
    WARN-LEVEL: MemberTier prices exist only as Python comments in
    apps/members/models.py, not as queryable model data. No FeeSchedule table.

    NOTE: apps/fees/models.py has AnnualFee with tier_at_billing (v0.2.0).
    To promote this check from warn to fail: add a tier→amount mapping constant
    to apps/fees/models.py — no separate FeeSchedule table needed.

    This check regex-matches the comment text in members/models.py against
    docs_data/readme_member_tiers.COMMENT_PATTERNS. Mismatch = advisory warn only.
    """
    members_model_path = Path(__file__).resolve().parent.parent.parent / "apps" / "members" / "models.py"
    source = members_model_path.read_text(encoding="utf-8")

    for tier_code, expected_comment in readme_member_tiers.COMMENT_PATTERNS.items():
        found = expected_comment in source
        assert_or_warn(
            found,
            message=(
                f"MemberTier.{tier_code}: comment '{expected_comment}' not found in "
                f"apps/members/models.py. Either the price changed or the comment was removed. "
                f"Update verification/docs_data/readme_member_tiers.py and README.md."
            ),
            test_id=f"test_member_tier_pricing_comment_matches_docs[{tier_code}]",
            category="docs_consistency",
        )


# ---------------------------------------------------------------------------
# 6. MemberTier enum values present
# ---------------------------------------------------------------------------

@pytest.mark.docs_consistency
@pytest.mark.django_db
def test_member_tier_values_match_docs():
    """MemberTier enum values in code match the tiers documented in README.md."""
    code_tiers = set(MemberTier.values)
    doc_tiers = set(readme_member_tiers.PRICES.keys())
    assert code_tiers == doc_tiers, (
        f"MemberTier mismatch.\n"
        f"  In code, not in docs: {code_tiers - doc_tiers}\n"
        f"  In docs, not in code: {doc_tiers - code_tiers}"
    )
