"""
verification/checks/test_known_issues_regression.py

Canary tests for known issues / deferred items documented in DEBUGLOG.md.

PATTERN: Each canary asserts that a known gap/fix is STILL in the expected state.
When a canary FAILS (a good thing — it means someone fixed the underlying issue):
  1. Add a DEBUGLOG.md entry describing the fix.
  2. Flip or remove the assertion here.
  NEVER remove a canary without updating DEBUGLOG.md first.

See verification/docs_data/debuglog_known_issues.py for the catalogue.
"""
import csv
from pathlib import Path

import pytest
from django.conf import settings

from apps.dojos.models import DojoEntity, DojoStaff


# ---------------------------------------------------------------------------
# 6. CRM-shell-leak: template inheritance scan (file-system)
#    Checks the ROOT CAUSE (wrong {% extends %}) not just the symptom.
# ---------------------------------------------------------------------------

MUST_USE_PUBLIC_BASE = [
    "accounts/login.html",
    "403.html",
    "404.html",
    "members/onboarding_form.html",
    "members/onboarding_invalid.html",
    "members/onboarding_success.html",
]


@pytest.mark.docs_consistency
def test_crm_shell_not_leaked_in_template_inheritance():
    """
    Canary for DEBUGLOG [2026-06-30] — 'accounts App: Login Page Leaked CRM
    Sidebar to Logged-Out Visitors'. Fixed in v0.3.1.

    Verifies that known public-facing templates extend base_public.html,
    NOT base.html. Catches the root cause (wrong {% extends %} directive)
    rather than only the symptom (sidebar in HTTP response).

    When this test FAILS it means either:
      (a) A public template was accidentally re-based to base.html — fix it, OR
      (b) The template was intentionally restructured — update MUST_USE_PUBLIC_BASE
          and add a DEBUGLOG entry explaining the architectural decision.
    """
    templates_dir = Path(settings.BASE_DIR) / "templates"
    for template_path in MUST_USE_PUBLIC_BASE:
        full_path = templates_dir / template_path
        assert full_path.exists(), (
            f"Expected template not found: {full_path}\n"
            "Update MUST_USE_PUBLIC_BASE if the template was renamed."
        )
        content = full_path.read_text(encoding="utf-8")
        assert 'extends "base.html"' not in content and \
               "extends 'base.html'" not in content, (
            f"{template_path} extends base.html — it must extend base_public.html "
            "because it is reachable by logged-out users. "
            "See DEBUGLOG [2026-06-30] for context."
        )


# ---------------------------------------------------------------------------
# 7. CRM-shell-leak: HTTP response check (complementary to #6)
#    Catches runtime rendering bugs even when {% extends %} is correct.
# ---------------------------------------------------------------------------

@pytest.mark.docs_consistency
@pytest.mark.django_db
def test_crm_sidebar_not_in_public_http_responses(client):
    """
    Complementary HTTP-level canary for the CRM-shell-leak fix (v0.3.1).
    Works together with test_crm_shell_not_leaked_in_template_inheritance
    to provide both template-inheritance and runtime-rendering coverage.
    """
    public_urls = [
        "/",
        "/about/",
        "/instructors/",
        "/our-dojos/",
        "/news/",
        "/showcase/",
        "/enroll/",
        "/accounts/login/",
    ]
    for url in public_urls:
        response = client.get(url)
        assert b'class="sidebar' not in response.content, (
            f"CRM sidebar marker (class=\"sidebar\") found in public route {url}. "
            "A logged-out user should never see CRM chrome. "
            "See DEBUGLOG [2026-06-30]."
        )


# ---------------------------------------------------------------------------
# 8. Dojo schedule fields — canary for missing schedule data
#    References dojo_event.csv explicitly.
# ---------------------------------------------------------------------------

@pytest.mark.docs_consistency
@pytest.mark.django_db
def test_dojo_entity_has_no_schedule_fields():
    """
    Canary: fixtures/legacy_data/dojo_event.csv contains Week/Time/GPS schedule
    data for 24 sessions across 9 legacy location codes. DojoEntity has no fields
    to store this — it only has name, slug, address, district, phone, is_active.

    When this test FAILS (a good thing — means schedule fields were added):
      1. Add a DEBUGLOG entry describing the new fields.
      2. Write a data migration to import dojo_event.csv into DojoEntity.
      3. Update seed_test_org_data --real-data to also seed schedule rows.
      4. Remove or update this canary.

    Ground truth: verification/fixtures/legacy_data/dojo_event.csv
    (pre-supplied, not scraped; richer than scraping: GPS, trilingual names)
    """
    fixture_path = (
        Path(settings.BASE_DIR) / "verification" / "fixtures" / "legacy_data" / "dojo_event.csv"
    )
    if not fixture_path.exists():
        pytest.skip(
            "verification/fixtures/legacy_data/dojo_event.csv is absent "
            "(local-only legacy data; not committed)"
        )
    with open(fixture_path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) > 0, "dojo_event.csv is empty — fixture may be corrupt"

    schedule_field_names = ["week", "day", "time_slot", "schedule",
                            "gps_lat", "gps_lng", "session_time"]
    existing_field_names = {f.name for f in DojoEntity._meta.get_fields()}
    leaked = [fn for fn in schedule_field_names if fn in existing_field_names]
    assert not leaked, (
        f"DojoEntity now has schedule field(s) {leaked}. "
        f"Update DEBUGLOG.md and write a data migration for the "
        f"{len(rows)} rows in dojo_event.csv."
    )


# ---------------------------------------------------------------------------
# 9a. WhatsApp Phase 1 stub — canary for integration status
# ---------------------------------------------------------------------------

@pytest.mark.known_issue
def test_whatsapp_stub_still_failed():
    """
    Canary for DEBUGLOG [2026-06-29] — 'WhatsApp Phase 1 integration is a stub
    marked FAILED. No provider SDK integrated.'

    This test verifies that WhatsApp is NOT silently 'working' without a DEBUGLOG
    update. It passes as long as no WhatsApp SDK import is present in
    apps/communications/.

    When this test FAILS (WhatsApp is now integrated):
      1. Add a DEBUGLOG entry describing the integration.
      2. Remove or update this canary.
    """
    # Check for actual SDK import lines — not enum choice names or comments.
    # 'WHATSAPP' as a TextChoices value (e.g. WHATSAPP = 'WHATSAPP', 'WhatsApp')
    # is expected and is NOT an SDK integration.
    comms_dir = Path(settings.BASE_DIR) / "apps" / "communications"
    sdk_import_patterns = [
        "import twilio",    "from twilio",
        "import vonage",    "from vonage",
        "import messagebird", "from messagebird",
        "import wa_sdk",    "from wa_sdk",
        "whatsapp_client",  "WhatsAppClient",
    ]
    found_in = []
    for py_file in comms_dir.rglob("*.py"):
        source = py_file.read_text(encoding="utf-8")
        for pattern in sdk_import_patterns:
            if pattern in source:
                found_in.append(f"{py_file.name}: {pattern}")
    assert not found_in, (
        f"WhatsApp SDK import(s) found in apps/communications: {found_in}. "
        "If WhatsApp is now integrated, add a DEBUGLOG entry and remove this canary."
    )


# ---------------------------------------------------------------------------
# 9b. Payment screenshots — canary for PRIVATE_STORAGE_ROOT pre-prod gap
# ---------------------------------------------------------------------------

@pytest.mark.known_issue
def test_payment_screenshot_not_yet_private_storage():
    """
    Canary for DEBUGLOG [2026-06-29] — 'Payment screenshots stored at
    MEDIA_ROOT/payment_screenshots/. Must move to PRIVATE_STORAGE_ROOT
    before production.'

    Passes as long as the payment screenshot field still uses the default
    storage (MEDIA_ROOT-based). Fails (a good thing) when private storage is wired up.

    When this test FAILS:
      1. Add a DEBUGLOG entry describing the private storage migration.
      2. Remove this canary.
    """
    payments_models = Path(settings.BASE_DIR) / "apps" / "payments" / "models.py"
    if not payments_models.exists():
        pytest.skip("apps/payments/models.py not found")

    source = payments_models.read_text(encoding="utf-8")
    # Check for actual storage= wiring on ImageField/FileField — NOT comments.
    # 'PRIVATE_STORAGE_ROOT' appearing only in comments (e.g. # move to PRIVATE_STORAGE_ROOT)
    # is expected and correct — it documents the known gap.
    # We only fail when a custom storage backend is actually wired as a field argument.
    private_storage_code_patterns = [
        "PrivateMediaStorage",
        "private_storage=",
        "storage=Private",
        "storage=private",
        "PrivateFileSystemStorage",
    ]
    for indicator in private_storage_code_patterns:
        assert indicator not in source, (
            f"apps/payments/models.py now uses private storage ('{indicator}' found in code). "
            "Add a DEBUGLOG entry and remove this canary."
        )


# ---------------------------------------------------------------------------
# 10. Standard dev seed data produces zero public instructors — by design
# ---------------------------------------------------------------------------

@pytest.mark.known_issue
@pytest.mark.django_db
def test_seed_minimal_and_full_produce_no_public_instructors():
    """
    Canary for DEBUGLOG [2026-08-10] — '/instructors/ Page Renders Empty'.

    seed_test_org_data --minimal and --full deliberately create DojoStaff
    rows with is_public=False for synthetic test personas (only --real-data,
    the legacy-CSV import, sets is_public=True). This test does not run the
    seed command itself (slow); instead it asserts the *default* for
    DojoStaff.is_public is still False, which is the mechanism the seed
    commands rely on to stay private by default.

    When this test FAILS (is_public now defaults True):
      1. Add a DEBUGLOG entry explaining why the default changed.
      2. Confirm this isn't accidentally publishing existing private staff bios.
      3. Update or remove this canary.
    """
    field = DojoStaff._meta.get_field('is_public')
    assert field.default is False, (
        "DojoStaff.is_public no longer defaults to False. If this is intentional, "
        "add a DEBUGLOG entry (see [2026-08-10]) and update this canary — "
        "seed_test_org_data --minimal/--full rely on this default to keep "
        "synthetic test personas off the public /instructors/ page."
    )
