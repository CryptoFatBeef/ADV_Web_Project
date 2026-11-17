"""
verification/docs_data/debuglog_known_issues.py

Ground truth: known issues / deferred items from DEBUGLOG.md.
Each entry maps to one or more canary tests in test_known_issues_regression.py.

When a known issue is fixed:
  1. Add a DEBUGLOG.md entry describing the fix.
  2. Flip or remove the corresponding canary test.
  3. Remove the entry from this module.
  NEVER remove without updating DEBUGLOG first.
"""

KNOWN_ISSUES = [
    {
        "id":          "SHELL_LEAK_FIXED_V031",
        "debuglog_ref": "[2026-06-30]",
        "description": "Login/403/404 pages previously extended base.html (CRM shell). "
                       "Fixed in v0.3.1 by re-basing to base_public.html.",
        "status":      "FIXED",
        "canary_test": "test_crm_shell_not_leaked_in_template_inheritance + "
                       "test_crm_sidebar_not_in_public_http_responses",
        "note":        "Canary verifies the fix stays fixed (both template-inheritance "
                       "and HTTP-response levels).",
    },
    {
        "id":          "WHATSAPP_PHASE1_STUB_FAILED",
        "debuglog_ref": "[2026-06-29]",
        "description": "WhatsApp Phase 1 integration is a stub marked FAILED. "
                       "No provider SDK is integrated.",
        "status":      "OPEN_DEFERRED",
        "canary_test": "test_whatsapp_stub_still_failed",
        "note":        "Canary fails (good) when WhatsApp is actually integrated, "
                       "prompting a DEBUGLOG update.",
    },
    {
        "id":          "PAYMENT_SCREENSHOT_PRIVATE_STORAGE",
        "debuglog_ref": "[2026-06-29]",
        "description": "Payment screenshots stored at MEDIA_ROOT/payment_screenshots/. "
                       "Must move to PRIVATE_STORAGE_ROOT before production.",
        "status":      "OPEN_PRE_PROD",
        "canary_test": "test_payment_screenshot_not_yet_private_storage",
        "note":        "Canary fails (good) when PRIVATE_STORAGE_ROOT is wired up.",
    },
    {
        "id":          "DOJO_SCHEDULE_FIELDS_MISSING",
        "debuglog_ref": "[2026-06-29]",
        "description": "DojoEntity has no per-class schedule fields (week/time/GPS). "
                       "dojo_event.csv holds 24 sessions that cannot yet be imported.",
        "status":      "OPEN_DEFERRED",
        "canary_test": "test_dojo_entity_has_no_schedule_fields",
        "note":        "Canary fails (good) when schedule fields are added to DojoEntity, "
                       "triggering a data migration from dojo_event.csv.",
    },
    {
        "id":          "PARENT_CONSENT_DEFERRED",
        "debuglog_ref": "[2026-06-30]",
        "description": "public_showcase_consent is staff-set only. Full MemberGuardian "
                       "model with self-service parent consent deferred to v0.4.0+.",
        "status":      "OPEN_DEFERRED",
        "canary_test": None,
        "note":        "No automated canary; this is a feature-scope decision.",
    },
]
