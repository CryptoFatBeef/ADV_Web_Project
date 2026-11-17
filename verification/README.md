# Verification Suite

Automated documentation-vs-reality checks for `ADV_Web_Project`.

Verifies that the running Django site is consistent with:
- `README.md` (architecture, roles, URLs, member tiers)
- `DEBUGLOG.md` (version history, known issues, canary tests)
- `Blueprint v0.7.1` (district list, member data)
- Legacy site fixture data (org intro, dojos, timetable, members)

---

## Quick Start

```bash
# 1. Install test dependencies
pip install -r requirements/test.txt

# 2. Generate test credentials CSV (one-time, or after role changes)
python -m verification.scraper.generate_credentials

# 3. Seed dev DB
python manage.py seed_test_users --settings=config.settings.dev
python manage.py seed_test_org_data --minimal --settings=config.settings.dev
python manage.py seed_test_org_data --full --settings=config.settings.dev

# 4. Run all checks
pytest verification/checks --settings=config.settings.dev -v

# Results written to:
#   verification/reports/results_latest.json
#   verification/reports/results_latest.csv
```

---

## Full Setup (first time)

### Step 1 — Legacy site scraper (rare/manual)

Scrapes one URL from the legacy site to refresh `legacy_org_intro.csv`:

```bash
python -m verification.scraper.legacy_site_scraper
# Optional: also write .xlsx mirror
python -m verification.scraper.legacy_site_scraper --xlsx
```

**TLS note**: the legacy host (`www.advancedtkd.net`) has a cert mismatch
(`dadmin.n2-tech.com`). The scraper uses `verify=False` with a suppressed
`InsecureRequestWarning`. This is documented intentionally; do not copy this
pattern elsewhere.

The scraper writes `verification/fixtures/legacy_org_intro.csv` and updates
`verification/fixtures/_scrape_manifest.json`.

### Step 2 — Seed management commands

```bash
# Load 7 test users (one per role)
python manage.py seed_test_users --settings=config.settings.dev

# Optional: purge existing test_* users first
python manage.py seed_test_users --purge --settings=config.settings.dev

# Minimal seed (for RBAC tests — fast, no file I/O)
python manage.py seed_test_org_data --settings=config.settings.dev

# Full legacy data seed (for public content tests — 161 members)
python manage.py seed_test_org_data --real-data --settings=config.settings.dev

# Full state-coverage seed (t0.2.0 — every enum/FSM state, 2 real dojos)
python manage.py seed_test_org_data --full --settings=config.settings.dev
```

**IMPORTANT**: These commands are **dev-only**. They raise `CommandError` if
`DEBUG=False`. Never run against a production database. (Test runs override
`DEBUG=True` for the duration of the `seed_full_dataset_in_db` pytest fixture
only — see `verification/conftest.py` for why this is safe.)

### Step 3 — Run checks

```bash
# All checks
pytest verification/checks --settings=config.settings.dev -v

# By marker
pytest verification/checks -m docs_consistency -v
pytest verification/checks -m rbac -v
pytest verification/checks -m legacy_fixture -v
pytest verification/checks -m known_issue -v

# Determinism test: run twice and diff (run_at excluded)
pytest verification/checks -q
pytest verification/checks -q
# Compare: reports/results_latest.json should be identical except "run_at"
```

---

## Legacy Data Fixtures

`verification/fixtures/legacy_data/` is **local-only**. It holds pre-supplied CSV
files and portrait photos from the legacy PHP site (advancedtkd.net). These are
**not scraped** by the test suite and are **not in git** (member roster and photos).
Copy them into that folder on a machine that already has them. On a fresh clone the
folder is absent: legacy fixture tests skip, and
`seed_test_org_data --real-data` is unavailable.

| File | Source | Used by |
|---|---|---|
| `memebers.csv` | Legacy member roster (utf-8-sig BOM) | `seed_test_org_data --real-data` |
| `dojo_event.csv` | Legacy timetable, 24 sessions | `test_dojo_entity_has_no_schedule_fields` canary |
| `dojo_location.csv` | 9 legacy district codes | `legacy_district_crosswalk.py`, Phase 5 tests |
| `dojo_area.csv` | KLN/NT area groupings | Reference only |
| `goals.csv` | Member credentials (utf-8-sig BOM) | `seed_test_org_data --real-data` |
| `members_images/` | 148 portrait photos | `seed_test_org_data --real-data` (DojoStaff.photo) |

### images/ folder (NOT a fixture)

`Testing Data/legacy_data/images/` (Banner/, Belt/, index/, Warmup/) = legacy static
assets. NOT used by this suite. Content migration material for the `public` app —
a separate task.

### memebers.csv Level field

`Level` (1–9) = HKTKD (中國香港跆拳道協會) Dan grade for black belts.

`DojoStaff.certifications` stores this as a synthesised entry **prepended** before
`goals.csv` entries:
```json
{"org_en": "Hong Kong, China Taekwondo Association", "level_en": "Xth Dan Black Belt", ...}
```

`MemberProfile.current_belt` = `BeltLevel.BLACK` for all rows (the `BeltLevel` enum
has no Dan-grade distinction — this is a known data model limitation, see DEBUGLOG).

Tier heuristic: Level 1–3 → `STUDENT_BLACK`, Level 4–9 → `ADULT_BLACK`.
The seeder prints per-row `[INFO]` notices so you can review and override individually.

---

## Canary Tests (IMPORTANT — Read Before Modifying)

Some tests in `test_known_issues_regression.py` are **intentional canaries** —
they assert that a known gap or fix is **still in the expected state**.

A canary test **failing is a good thing** when the underlying issue has been fixed.

**When a canary fails:**
1. **Add a `DEBUGLOG.md` entry** describing the fix or change.
2. Update or remove the canary assertion.
3. Update `verification/docs_data/debuglog_known_issues.py`.

**Never remove a canary without updating `DEBUGLOG.md` first.**

Current canaries:

| Test | Status | Condition |
|---|---|---|
| `test_crm_shell_not_leaked_in_template_inheritance` | FIXED (v0.3.1) | login/403/404 extend `base_public.html` |
| `test_crm_sidebar_not_in_public_http_responses` | FIXED (v0.3.1) | public routes have no sidebar marker |
| `test_dojo_entity_has_no_schedule_fields` | OPEN_DEFERRED | `DojoEntity` still lacks Week/Time/GPS fields |
| `test_whatsapp_stub_still_failed` | OPEN_DEFERRED | No WhatsApp SDK in `apps/communications` |
| `test_payment_screenshot_not_yet_private_storage` | OPEN_PRE_PROD | Screenshots still at `MEDIA_ROOT/` |

---

## docs_data/ — Manual Sync Required

`verification/docs_data/` contains Python literals hand-transcribed from README.md,
DEBUGLOG.md, and `apps/dojos/models.py`. They are reviewed like code.

**Update these files whenever their source changes:**

| File | Source |
|---|---|
| `readme_roles.py` | README.md role table |
| `readme_url_structure.py` | README.md URL structure table |
| `readme_member_tiers.py` | README.md member tier pricing |
| `blueprint_districts.py` | `apps/dojos/models.py` `DojoEntity.District` |
| `legacy_district_crosswalk.py` | Manual mapping (review when district list changes) |
| `debuglog_known_issues.py` | DEBUGLOG.md known issues section |

**Note on app count**: `readme_url_structure.py` notes that README Changelog
references "12 apps" (the pre-v0.3.1 scope). The authoritative current count is
**14 apps** per the Architecture tree in README.md. The Changelog figure is
historical, not the current total.

---

## Test Credentials

`verification/fixtures/test_credentials.csv` is generated locally and gitignored.
Do not commit it. Passwords are deterministically derived from a fixed dev-only
salt documented in `verification/scraper/generate_credentials.py`, and the
accounts are for a local DEBUG database only, never prod.

To regenerate (e.g. after adding a new persona):
```bash
python -m verification.scraper.generate_credentials
python manage.py seed_test_users --settings=config.settings.dev
```

---

## t0.2.0 — Role Capability Matrix, Full Dataset, Object-Level Access (v0.2.0)

Extends t0.1.0 with the two foundations write-path tests depend on:

### Role Capability Matrix

`verification/docs_data/role_capability_matrix.py` — the single source of truth
for what each of the 7 roles can View/Create/Update/Delete per feature, **after**
the dojo/owner-scoping fixes below (records actual code behavior, not the
original aspirational proposal).

`verification/reports/matrix_diff_report.md` (generated from
`docs_data/matrix_diff_report.py`) — every place the original aspirational
proposal still diverges from code (missing Delete views anywhere, fees/payments
being ADMIN-only, matches being Tournament- not member-scoped, etc.). Regenerate via:
```bash
python -m verification.docs_data.matrix_diff_report
```

### 12-persona test_credentials.csv (v2)

Extended from t0.1.0's 7 rows (1 per role) to 12 personas — two COACH personas
at two different dojos (`test_coach_a`/`test_coach_b`), three peer MEMBER
personas plus two edge-case MEMBER personas (`test_member_suspended`,
`test_member_inactive`), and a bare `test_parent_a` (no `MemberProfile` —
`MemberGuardian` doesn't exist yet). Needed for object-level scoping tests
that require *different* users at *different* dojos, not just different roles.

### `seed_test_org_data --full`

State-coverage dataset across all 14 apps — every enum value, every FSM
state, every role-visible branch gets at least one row. 2 real dojos
(WongTaiSin, TaiPo). See the command's docstring for the exact per-app
row design. Writes `verification/fixtures/full_dataset_manifest.json`.

**FSM note**: `ActivityApplication.state` is `FSMField(protected=True)` —
direct assignment is blocked, so all 7 state-coverage rows are built by
calling the real `@transition`-decorated methods (`submit()`, `recommend()`,
`approve()`, `reject()`, `confirm_payment()`, `complete()`) in sequence,
never by setting `.state` directly.

### PERSONAS.md

`verification/PERSONAS.md` — generated login/role/visibility table for local
manual UAT, derived from the capability matrix. It is gitignored. Do not commit
it. Regenerate via:
```bash
python -m verification.scraper.generate_personas_doc
```

### New test files + markers

- `test_rbac_write_matrix.py` (`rbac`) — POSTs to the 3 real write views
  (`events:event_create`, `members:member_edit`, `cms:page_edit`). Every
  DENY case asserts **both** 403 **and** the database is unchanged.
- `test_object_level_access.py` (`rbac`) — proves the dojo/owner-scoping
  fixes actually isolate data (`test_coach_a` cannot see Dojo B's
  members/events/activities/skills; `test_member_a1` cannot see peers'
  skill records).
- `test_public_forms.py` (`write_path`, new marker) — POSTs to
  `enrollment:lead_create`, the only fully-public CreateView in the codebase.
- `test_activity_fsm_transitions.py` (`fsm`, new marker) — valid chains
  succeed, terminal states reject further transitions, skipping steps raises
  `TransitionNotAllowed`, direct `.state =` assignment raises `AttributeError`.

Run all t0.2.0-specific tests: `pytest verification/checks -m "rbac or write_path or fsm"`.
