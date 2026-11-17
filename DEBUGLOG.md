# DEBUGLOG — 技擊跆拳道會 CRM System

This file tracks all significant bugs, errors, and fixes encountered during development. Log every non-trivial issue — the goal is a searchable institutional memory for this project.

---

## How to Use This Log

**When to log:**

- Any bug that took more than 5 minutes to diagnose  
- Unexpected Django / library behaviour  
- Environment / config issues  
- Migration conflicts or data integrity problems  
- Third-party API integration errors (Stripe, PayMe, WhatsApp, Claude)  
- Security issues (always log, always fix before merging)

**How to add an entry:** Copy the template below, paste at the TOP of the Entries section (newest first), fill in all fields.

---

## Entry Template

```
---

### [YYYY-MM-DD] — <Short Title>

**Status:** Open / Resolved / Won't Fix
**Severity:** Low / Medium / High / Critical
**App / Module:** <e.g. members, payments, events>
**Environment:** Dev / Staging / Production

**Symptom:**
What was observed — exact error message, traceback, or unexpected behaviour.

**Root Cause:**
Why it happened. Be specific.

**Fix Applied:**
What was changed to resolve it. Include file paths and line numbers if relevant.

**Prevention / Notes:**
What can be done to avoid this class of problem in future.
Any related docs, Stack Overflow links, or Django docs sections worth bookmarking.

---
```

---

## Entries

---

### [2026-08-12] — Member CRM Module Overhaul: Full Profile, Belt/Certificate History, Payments Tab, Guardian Self-Service Onboarding

**Status:** Resolved
**Severity:** Medium
**App / Module:** apps/members, apps/fees, apps/payments (read-only), templates/members
**Environment:** Dev

**Symptom:**
The Member CRM module was a thin shell: the detail page showed only 6 of `MemberProfile`'s fields, the edit view exposed only 5 (`fields = ['status', 'current_belt', 'tier', 'primary_dojo', 'public_showcase_consent']`), there was no belt-promotion history, no certificate-expiry tracking, no payment visibility on the member page, and no way to onboard a new member (especially a minor) without going through Django Admin by hand.

**Root Cause:**
Feature gap — this functionality was never built, not a regression. Notably, `DEBUGLOG.md` [2026-06-30] (Parent Consent Deferred) had already recorded a deliberate decision to defer a Parent↔Member guardian model "pending a decision on legal guardianship vs. enrollment-contact semantics" — resolved in this pass per an explicit product decision: build a real linked `User` account (role=PARENT) with no legal-authority enforcement, just accurate contact/relationship data.

**Fix Applied:**
- `MemberProfile` gained `chinese_name`, `height_cm`, `weight_kg` (contact phone/email and registration date already existed via `user.phone`/`user.email`/`joined_date`, just weren't displayed/editable).
- New models (`apps/members/models.py`): `BeltPromotionRecord` (belt-achievement history, manually maintained — no automated derivation from `SkillRecord`, matching the rest of the codebase's manual-step convention), `MemberCertificate` (general certificate name/issuing body/acquired/valid-until, distinct from the coach-exam-specific `CoachCertificationRecord`), `MemberGuardian` (many-to-many member↔guardian-User link with `relationship`/`is_primary`, no legal enforcement — `MemberProfile.is_minor` is a plain computed property, and a missing guardian on a minor is a non-blocking warning banner, not a hard save-time constraint), `RegistrationInvitation` (UUID-token, 7-day-expiring, PENDING/COMPLETED/EXPIRED/REVOKED).
- `MemberDetailView`/`member_detail.html` rewritten as Bootstrap 5 tabs (new pattern for this project — nothing existing to reuse): Profile / Guardians / Belt & Certifications / Payments. The Payments tab (`annual_fees` + `payment_records`, reached via the `annual_fee__member` traversal since neither `Invoice` nor `PaymentRecord` has a direct FK to `MemberProfile`) is gated to `ADMIN_ROLES` only — `COACH` does not gain new visibility into financial data, matching the existing `apps/fees`/`apps/payments` access boundary.
- `MemberUpdateView` replaced the single auto-generated `ModelForm` with two explicit forms (`MemberContactForm` over `accounts.User`, `MemberProfileForm` over `MemberProfile`, both in new `apps/members/forms.py`), saved together in one `transaction.atomic()` block.
- New coach/admin-initiated, parent-self-service onboarding flow: `MemberInvitationCreateView` (dojo-scoped the same way `DojoScopedQuerysetMixin` already scopes elsewhere — a `COACH` can only invite for their own `DojoStaff` dojo(s)) creates a `RegistrationInvitation` and emails a magic link (`apps/members/services.py::send_invitation_email` — a new small function, since the only existing `send_mail()` call site in `apps/communications/services.py` is hard-coupled to an existing `MemberProfile` recipient and can't address an unregistered invitee). `MemberOnboardingView` is a genuinely public, no-login view reached via that link; on submit it creates the guardian `User` (role=PARENT, real password they set), the child `User`+`MemberProfile` (role=MEMBER, unusable password — not expected to log in independently), and the `MemberGuardian` link, all in one transaction, then marks the invitation `COMPLETED`.
- Per the CRM-shell-leak precedent ([2026-06-30]), the three new public templates (`onboarding_form.html`, `onboarding_invalid.html`, `onboarding_success.html`) extend `public/base_public.html` and were added to `test_known_issues_regression.py`'s `MUST_USE_PUBLIC_BASE` list.
- Explicitly out of scope (flagged, not silently dropped): CAPTCHA/anti-bot protection (no infra exists anywhere in the project; email-gated + expiring single-use token is the accepted trade-off for a small club's internal tool), adult self-registration via the same link (always creates a guardian+child pair), and a password-reset flow for the guardian account (they set their password directly during onboarding, so it's not a hard dependency, but there's still no recovery path if forgotten — Django's built-in `PasswordReset*` views aren't wired up anywhere in this project).
- Updated `verification/checks/test_rbac_write_matrix.py::test_member_edit_rbac` — its POST payload only had the 5 old fields, so the new required `MemberProfileForm` fields (`date_of_birth`, `gender`, `emergency_contact_*`) failed validation silently (200, not saved). Fixed to submit both forms' full field set.

**Prevention / Notes:**
When splitting one `ModelForm`-backed view into two forms, audit every existing test that POSTs to that URL — a stricter/expanded required-field set makes old partial payloads fail validation without necessarily changing the HTTP status code (still 200, just re-rendering with errors), which a status-code-only assertion won't catch. `test_member_edit_rbac`'s stronger DB-state assertion (not just status code) is exactly what caught this here.

---

### [2026-08-10] — CRM Member Detail Page Didn't Surface Coach Roles / Certifications

**Status:** Resolved
**Severity:** Low
**App / Module:** apps/members, templates/members
**Environment:** Dev

**Symptom:**
A member who is also a registered coach (has a `DojoStaff` row and/or a passed `CoachCertificationRecord`) showed none of that on their CRM `/members/<pk>/` page — only belt/tier/status/dojo/joined date. Staff had to cross-reference Django admin to see someone's coaching qualifications. Caught while reviewing the two entries below: two demo "coach" test users existed as `DojoStaff` but had no `MemberProfile`, so they were invisible on `/members/` even though every real coach is expected to be a club member first.

**Root Cause:**
`MemberDetailView` (`apps/members/views.py`) never queried `DojoStaff` or `CoachCertificationRecord` for the member being viewed — `member_detail.html` only ever had fields from `MemberProfile` itself.

**Fix Applied:**
- `MemberDetailView.get_context_data` now adds `dojo_staff_roles` (`DojoStaff.objects.filter(user=member.user)`) and `coach_certifications` (`CoachCertificationRecord` via `activity_application__member`) to context.
- `templates/members/member_detail.html` renders both as new sections (role/tier per dojo, and a course/certifying-body/exam-date/result table), only when present.
- Added `test_member_detail_shows_coach_role_and_certification` to `verification/checks/test_object_level_access.py`.

**Prevention / Notes:**
`MemberProfile` and `DojoStaff` are still two independent tables both pointing at `accounts.User` (see the `DojoStaff.role` vs `accounts.User.role` note earlier in this log) — nothing enforces that a `DojoStaff.user` also has a `MemberProfile`. That's fine for the schema, but keep dev/demo data consistent with the real world (a coach is a member first) to avoid confusing gaps like this one.

---

### [2026-08-10] — `/instructors/` Redesigned: Grouped by HKTKDA Coach Tier + Detail Pages

**Status:** Resolved
**Severity:** Low
**App / Module:** apps/dojos, apps/public, templates/public, static/css
**Environment:** Dev

**Symptom:**
Follow-up to the same-day entry below. Once `/instructors/` could show public coaches at all, the flat single-list layout didn't match the club's real structure: HKTKDA certifies coaches at three tiers (高級教練 Senior / 中級教練 Intermediate / 初級教練 Elementary), and each coach's name needed to link somewhere.

**Root Cause:**
N/A (feature request, not a defect) — `DojoStaff` had no field capturing which HKTKDA tier a coach holds, and there was no per-coach detail page to link to.

**Fix Applied:**
- Added `DojoStaff.CoachLevel` choices (`SENIOR`/`INTERMEDIATE`/`ELEMENTARY`) and a new `coach_level` field (`apps/dojos/models.py`, migration `0003_dojostaff_coach_level.py`) — blank by default, set manually by a GM in `DojoStaffAdmin`/`DojoStaffInline` (`apps/dojos/admin.py`) once a member's `CoachCertificationRecord` shows a pass. Manual step by design, same as everywhere else in this app.
- `InstructorListView` (`apps/public/views.py`) now groups the queryset into `instructor_groups` (one list per `CoachLevel`, in Senior → Intermediate → Elementary order) instead of returning a flat list.
- Added `InstructorDetailView` + `public:instructor_detail` URL (`/instructors/<slug>/`) so each coach's name links to a full bio page (`templates/public/instructor_detail.html`) showing tier badge, bio, and certifications.
- Rewrote `templates/public/instructors.html` into three tier sections; added supporting styles (card hover, tier-heading underline, tier badge) to `static/css/public.css`.
- Updated `test_public_instructors_shows_public_coach` to set `coach_level` (otherwise it wouldn't render under any tier section) and added `test_public_instructor_detail_returns_200`.

**Prevention / Notes:**
`DojoStaff.certifications` (free-form JSON, used for the bulleted cert list) and `DojoStaff.coach_level` (structured, drives the tier grouping) are two different fields serving different purposes — don't conflate them when extending this page further.

---

### [2026-08-10] — Public `/instructors/` Page Renders Empty; No In-System Coach Certification Tracking

**Status:** Resolved
**Severity:** Medium
**App / Module:** apps/public, apps/dojos, apps/activities, templates/public
**Environment:** Dev

**Symptom:**
`/instructors/` always rendered "暫無公開教練資料" (no public instructor data), even for members who are actually qualified/registered coaches.

**Root Cause:**
1. `InstructorListView` (`apps/public/views.py`) correctly queries `DojoStaff.objects.filter(is_public=True, is_active=True)` — the query itself was never the bug. `DojoStaff.is_public` (`apps/dojos/models.py`) defaults to `False`, and nothing in the codebase ever set it `True` except the `--real-data` legacy-CSV seed mode. The standard dev seed modes (`seed_test_org_data --minimal` / `--full`) deliberately create `DojoStaff` rows with `is_public=False` for synthetic test personas — this is intentional, not a bug.
2. There was no in-system record at all of the real qualification path: a member applies for the HKTKDA Elementary Coach Course, passes the assessment, and becomes the club's registered coach (本會註冊教練). `apps/activities/models.py` had no `ActivityType` for this and `ActivityApplication` had no exam-result fields.
3. Secondary bug: `templates/public/instructors.html` read `cert.org` / `cert.rank`, but the only JSON keys ever written to `DojoStaff.certifications` are `org_en`/`org_zh`/`level_en`/`level_zh`/`year` — certification bullets would have rendered blank even once real `is_public=True` coaches existed.
4. `verification/checks/test_public_routes.py`'s `test_public_instructors_returns_200` only asserted HTTP 200, never that any instructor content rendered — so the empty page was never caught by the verification suite.

**Fix Applied:**
- Added `ActivityType.COACH_CERTIFICATION` and a new `CoachCertificationRecord` model (`apps/activities/models.py`, one-to-one with `ActivityApplication`: `certifying_body`, `course_name`, `exam_date`, `result` (reuses `apps.skills.models.SkillResult`), `certificate_number`, `notes`) so the HKTKDA course application/exam result can be tracked in-system, following the same `ActivityApplication` FSM workflow already used for belt grading and referee promotion. Migration: `apps/activities/migrations/0002_alter_activitytemplate_activity_type_and_more.py`.
- Registered `CoachCertificationRecord` as an inline on `ActivityApplicationAdmin` (`apps/activities/admin.py`).
- **Turning a passed exam into a public `DojoStaff` row (and setting `is_public=True`) remains a manual admin step**, done via the existing `DojoStaffAdmin`/`DojoStaffInline` (`apps/dojos/admin.py`) — this matches the existing architecture, where no `ActivityApplication` FSM transition anywhere has automated cross-model side effects (every transition body is empty except for timestamps). Deliberately not automated.
- Fixed `templates/public/instructors.html` to read `org_zh`/`org_en`/`level_zh`/`level_en`/`year` (with `zh`→`en` fallback) instead of the nonexistent `org`/`rank` keys.
- Added `test_public_instructors_shows_public_coach` to `verification/checks/test_public_routes.py` — creates its own `is_public=True` `DojoStaff` row and asserts the coach's name renders, independent of any seed command.
- Added a canary in `verification/checks/test_known_issues_regression.py` documenting that `seed_test_org_data --minimal`/`--full` intentionally produce zero public instructors, so this isn't mistaken for a regression later.

**Prevention / Notes:**
Route-level tests that only assert HTTP 200 do not catch "page loads but is empty" bugs — pair every public content page's 200-check with at least one test that seeds real data and asserts specific content renders.

---

### [2026-07-06] — Verification Suite: Role Capability Matrix + Full Dataset (v0.2.0)

**Status:** Resolved  
**Severity:** Low  
**App / Module:** verification/ (extends v0.1.0), apps/members, apps/events, apps/activities, apps/skills  
**Environment:** Dev

**Symptom:**  
No state-coverage test dataset existed across the 14 apps (every enum value,
every FSM state, every role branch). No single source of truth existed for
what each of the 7 roles can View/Create/Update/Delete per feature — a
Blueprint-derived proposal existed but had never been checked against code.

**Root Cause:**  
Exhaustive exploration of all 14 apps' `views.py` files found the real
codebase far more limited than the aspirational proposal assumed: zero
`DeleteView`s exist anywhere; only 2 `CreateView`s (`EventCreateView`,
`EnrollmentCreateView`) and 2 `UpdateView`s (`MemberUpdateView`,
`CMSPageEditView`) exist total; zero `get_queryset()` overrides existed for
dojo/owner-scoping in any real List/DetailView — a COACH viewing
`MemberListView` saw *all* members org-wide, not just their own dojo's.

**Fix Applied:**  
- `verification/docs_data/role_capability_matrix.py` — records ACTUAL code
  behavior (post-fix), not the aspirational proposal. `matrix_diff_report.py`
  (→ `reports/matrix_diff_report.md`) logs every remaining divergence
  explicitly (fees/payments ADMIN-only, matches Tournament-not-member-scoped,
  communications/chatbot are stubs, `MemberProfile.status` has no access
  enforcement anywhere) as accepted/future-work, never silently resolved.
- **Dojo/owner scoping added** to `apps/members/views.py`
  (`MemberListView`/`MemberDetailView`), `apps/events/views.py`
  (`EventListView`/`EventDetailView`), `apps/activities/views.py`
  (`ActivityListView`/`ActivityDetailView`), `apps/skills/views.py`
  (`SkillListView`, both COACH-dojo and MEMBER/PARENT-own branches). All
  filters end in `.distinct()` (reverse-FK joins through
  `enrollments__dojo_id__in=...` can duplicate rows). `apps/matches/views.py`
  deliberately left unchanged — confirmed `model = Tournament` on both views,
  not member-owned, documented as an accepted gap.
- `test_credentials.csv` extended 7→12 personas: `test_coach_a`/`test_coach_b`
  at two real dojos (WongTaiSin/TaiPo), `test_member_a1`/`a2`/`b1`,
  `test_member_suspended`/`test_member_inactive` (edge-case personas),
  `test_parent_a` (bare `User`, no `MemberProfile` — `MemberGuardian` doesn't
  exist yet). `generate_credentials.py` password derivation keyed by username,
  not role, so personas sharing a role get distinct passwords.
- `seed_test_org_data --full` (new third flag) — state-coverage dataset:
  8 Events (4 EventType × past/upcoming, all 4 EventStatus), 3 AttendanceLog
  (all 3 CheckInMethod — not "both", there are 3), 7 ActivityApplication
  (one per FSM state, built via real `@transition` chains since
  `state = FSMField(protected=True)` blocks direct assignment), 7 SkillRecord
  (all 7 SkillCategory), 5 AnnualFee (all 5 FeeStatus), 6 PaymentRecord (all
  6 PaymentStatus — not 5), 5 Notification (all 5 NotificationStatus, one
  WHATSAPP+FAILED cross-referencing the v0.1.0 canary), 7 ContentBlock (all 7
  PageSection — uncovered in the original ask), 2 Tournaments + 7 MatchEntry
  split 4+3 (only 5 MemberProfiles exist and `unique_member_per_tournament`
  caps one tournament at 5 entries, so 7 entries covering 6 MatchResult
  values + 1 blank/pending state need 2 tournaments), 6 FAQEntry (all 6
  FAQCategory — not 4), 2 EnrollmentLead. Writes
  `verification/fixtures/full_dataset_manifest.json`.
- `verification/PERSONAS.md` — generated login/visibility table for manual UAT.
- New tests: `test_rbac_write_matrix.py` (POST to the 3 real write views;
  every DENY case asserts 403 **and** DB-unchanged), `test_object_level_access.py`
  (proves the scoping fixes actually isolate dojo/owner data),
  `test_public_forms.py` (`enrollment:lead_create`, the only fully-public
  CreateView), `test_activity_fsm_transitions.py` (valid/invalid FSM chains,
  direct `.state =` assignment raises `AttributeError`). New pytest markers:
  `write_path`, `fsm`.
- `verification/conftest.py`: new `seed_full_dataset_in_db` session fixture
  calls the real management commands via `call_command()` inside
  `override_settings(DEBUG=True)` — pytest-django forces `DEBUG=False` during
  test runs (a deliberate Django testing best practice), which would otherwise
  trip the commands' `if not settings.DEBUG: raise CommandError` production
  guard even though the pytest test DB is fully isolated and throwaway.

**Prevention / Notes:**  
- 173 tests total (135 from v0.1.0 + 38 new), all passing.
- `seed_test_org_data --full` re-run twice against the dev DB produces a
  byte-identical `full_dataset_manifest.json` (anchored dates, no
  `date.today()` in seeded values) — confirmed deterministic.
- When closing any gap logged in `matrix_diff_report.md` (e.g. adding
  MEMBER/PARENT access to fees/payments, or a MatchEntry-level view), update
  the diff report AND `role_capability_matrix.py` together — never silently.

---

### [2026-07-02] — Verification Suite Added (v0.1.0)

**Status:** Resolved  
**Severity:** Low  
**App / Module:** verification/ (new top-level package)  
**Environment:** Dev

**Symptom:**  
No automated way to check that the running site matched what README.md / DEBUGLOG.md /
Blueprint v0.7.1 described. All `apps/*/tests.py` were empty boilerplate. No seed data,
no fixtures, no role-based login tests.

**Root Cause:**  
The project reached v0.3.1 (frontend complete) without a cross-cutting verification layer.
Unit-test stubs in individual apps are insufficient for doc-vs-reality checks that span
roles, routes, legacy data, and known-issue regressions.

**Fix Applied:**  
Created `verification/` package (pytest-based, separate from `apps/*/tests.py`) with:

- `verification/fixtures/legacy_data/` — pre-supplied legacy CSVs (161 members, 24 dojo
  sessions, 9 district codes, 2 area groups, member credentials) + 148 portrait photos.
- `verification/scraper/legacy_site_scraper.py` — scrapes one URL (`/Public/Intro_adv`)
  to produce `legacy_org_intro.csv`. TLS cert mismatch on advancedtkd.net → `verify=False`,
  documented. District/timetable data replaced by pre-supplied CSVs (richer).
- `verification/scraper/generate_credentials.py` — deterministic 7-role credential CSV.
- `apps/accounts/management/commands/seed_test_users.py` — idempotent, DEBUG-guarded loader.
- `apps/accounts/management/commands/seed_test_org_data.py` — `--minimal` (RBAC tests) and
  `--real-data` (161 members from memebers.csv + goals.csv + photos) modes.
  CRITICAL fix: `DojoEntity` has `unique_head_coach_per_dojo` constraint → only Level 9
  (Chairman) gets `HEAD_COACH`; Level 7-8 (President/VP) get `ASSISTANT_COACH`.
  Tier heuristic: Level 1-3 → `STUDENT_BLACK`, Level 4-9 → `ADULT_BLACK`.
- `verification/docs_data/` — hand-transcribed ground truth (roles, URLs, tiers, districts,
  district crosswalk, known-issues catalogue).
- `verification/checks/`:
  - `test_docs_consistency.py` — 14-app count, roles, district enum, URL structure, tier prices.
  - `test_known_issues_regression.py` — canary tests for DEBUGLOG gaps (shell-leak, WhatsApp
    stub, payment screenshot storage, dojo schedule fields).
  - `test_public_routes.py` — public route 200s, founding-year warn check.
  - `test_legacy_fixture_consistency.py` — district crosswalk (DIRECT/APPROXIMATE/UNMAPPABLE),
    fixture row-count sanity.
  - `test_rbac_matrix.py` — 7 roles × 14 CRM routes → 200/403/302 matrix.
- `verification/reporting/` — pytest plugin writing `results_latest.{json,csv}` after every run.
- `requirements/test.txt` — adds requests, beautifulsoup4, lxml, openpyxl, pytest-socket,
  freezegun on top of `requirements/dev.txt`.
- `verification/README.md` — full setup, scraper, seed, run, canary-test convention.

**Prevention / Notes:**  
- Run `pytest verification/checks -v` before merging any
  structural change (new app, new role, route rename, district addition).
- When a DEBUGLOG known-issue is fixed, update the canary in
  `test_known_issues_regression.py` + `docs_data/debuglog_known_issues.py` first.
- `docs_data/` modules are **manual sync points** — update them whenever README or
  DEBUGLOG changes, as they are not auto-parsed from prose.
- `blueprint_districts.py` sources from `apps/dojos/models.py` (not the Blueprint PDF).
- `memebers.csv` Level field = HKTKD Dan grade (1-9段), NOT Django BeltLevel — Dan grade
  is stored in `DojoStaff.certifications` JSON as a synthesised entry.

---

### [2026-06-30] — accounts App: Login Page Leaked CRM Sidebar to Logged-Out Visitors

**Status:** Resolved
**Severity:** Medium
**App / Module:** accounts, templates
**Environment:** Dev

**Symptom:**
`templates/accounts/login.html` extended `base.html` (the authenticated CRM shell). Verified
via `grep -i sidebar` on rendered HTML output — a logged-out visitor hitting the login page saw
the full CRM sidebar markup (nav items gated by `{% has_role %}` correctly returned empty for
an anonymous user, but the sidebar container itself, "All authenticated" nav items like
Dashboard/Events/Activities/Matches/Chatbot, and the overall CRM shell structure rendered
unconditionally). Same bug class as the root `/` → DashboardView issue that prompted v0.3.1,
but on a different template, not caught during the original v0.3.0 review.

**Root Cause:**
`base.html` was designed under the assumption it would only ever be rendered for authenticated
users (access enforced via `LoginRequiredMixin` at the view layer). `LoginView` is, by
necessity, accessible to logged-out users — so any template extending `base.html` for the login
page inherently breaks that assumption. The 403/404 error pages had the identical problem for
the same reason.

**Fix Applied:**
- `templates/accounts/login.html` re-based to extend `templates/public/base_public.html`
  instead of `base.html`.
- `templates/403.html` and `templates/404.html` also re-based to `base_public.html` (discovered
  during the same audit — see v0.3.1 entry below for full context), with the back-link made
  conditional: authenticated users get "Back to Dashboard", logged-out get "Back to Home".
- Post-fix audit: `grep -r 'extends "base.html"' templates/` returns zero hits outside
  authenticated-only template directories.

**Prevention / Notes:**
- Standing rule going forward: any template reachable by a logged-out user must never extend
  `base.html`. `base.html` is reserved exclusively for views wrapped in `LoginRequiredMixin`.
- Add this check to the pre-merge checklist for any future template work: if a new view is NOT
  behind `LoginRequiredMixin`, manually confirm its template extends `base_public.html`.
- This bug class (CRM shell leaking to public pages) was the entire motivation for the v0.3.1
  milestone — see that entry for full architectural context.

---

### [2026-06-30] — Public Website Split: apps.public, apps.enrollment, SEO Foundation

**Status:** Resolved
**Severity:** N/A
**App / Module:** public (new), enrollment (new), accounts, cms, dojos, members
**Environment:** Dev

**Symptom:** N/A — architectural correction. v0.3.0 routed `/` directly to the authenticated
`DashboardView`, meaning prospective members, parents, and search engine crawlers hit a login
wall instead of a public-facing site. Discovered post-v0.3.0 ship during manual review, not
during the original build.

**Root Cause:** The v0.3.0 milestone brief never separated "public marketing site" from "CRM
shell" as distinct concerns — both were assumed to live under the same `base.html` /
`/` root. No public-facing requirement had been scoped into that milestone.

**Fix Applied:**
- Routing: `/` now serves `apps.public.views.HomeView` (no auth). CRM root moved to
  `/accounts/dashboard/`. `LOGIN_URL`, `LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL` updated in
  `config/settings/base.py` accordingly.
- New public-only URL prefixes: `/about/`, `/instructors/`, `/our-dojos/` (and
  `/our-dojos/<slug>/`), `/news/` (and `/news/<slug>/`), `/showcase/`, `/enroll/`, `/robots.txt`.
  CRM `/dojos/` and `/members/` are untouched and remain role-gated — `/our-dojos/` was chosen
  as a distinct prefix specifically to avoid URL-prefix collision with the CRM's `/dojos/`,
  which would otherwise complicate `robots.txt` rules and routing logic.
- New app `apps.public` — views + templates only, no models. Reads `DojoEntity` (dojos),
  `NewsPost` (cms, new model), `DojoStaff` (dojos, extended with public bio fields), and
  `MemberProfile` (members, filtered to black-belt tiers + explicit consent) to render public
  pages.
- New app `apps.enrollment` — `EnrollmentLead` model for public lead capture. Includes a
  mandatory `consent_pdpo` boolean field (Hong Kong Personal Data (Privacy) Ordinance requires
  explicit consent for public personal-data collection forms), enforced at both form and model
  level, with the privacy notice displayed inline on the form page (not just linked).
- New template tree: `templates/base_public.html` — simple top navbar, no sidebar, structurally
  incapable of leaking CRM nav structure. Used by every public-facing template, including
  `accounts/login.html`, `403.html`, and `404.html` (see separate entry above for that specific
  leak fix).
- New fields: `DojoStaff.bio_zh`, `bio_en`, `photo`, `certifications` (JSONField), `is_public`,
  `slug`, `display_order` — public instructor bios sourced from real Blueprint V0.7.1 content
  (黎銳金, 陳景年, 高民, 鄭偉雄, 鄔竣傑, 馮家輝 credentials), not placeholder text.
  `MemberProfile.public_showcase_consent` (boolean, default False) — staff-set only via the
  existing `MemberUpdateView` (already role-gated to admin roles); no parent self-service
  consent model built this milestone (see Key Decisions).
- SEO foundation: `robots.txt` (allows public paths, disallows all CRM/admin paths), JSON-LD
  `SportsOrganization`/`SportsActivityLocation` structured data, Open Graph meta tags, bilingual
  (繁中/English) page titles and meta descriptions targeting real search terms
  ("香港跆拳道班", "Taekwondo Hong Kong", district-specific dojo terms).
- `SITE_DOMAIN`, `SITE_FACEBOOK_URL`, `SITE_INSTAGRAM_URL` added as env-configurable settings
  (all default to empty/placeholder — no domain or social handles were finalized at build time,
  see Key Decisions) exposed to all templates via a new context processor
  (`apps.public.context_processors.site_settings`).

**Key Decisions:**
- **Parent consent deferred:** building a full parent-authority model (which `Parent` account
  can consent for which specific `Member`) was scoped out of this milestone — the codebase has
  no `Parent`↔`Member` relationship model at all (`User.role='PARENT'` is just a role tag, no
  linkage). `public_showcase_consent` is staff-set only for now. A proper `MemberGuardian`
  model with self-service parent consent is deferred to v0.4.0+, pending a decision on legal
  guardianship vs. enrollment-contact semantics (relevant for divorced parents / foster
  guardianship cases) — do not build this without that decision made first.
- **Domain and social handles not finalized:** rather than hardcode `www.advancedtkd.net` (only
  referenced in an old marketing PDF, not confirmed as the production domain) or fabricate
  Facebook/Instagram URLs, both are env-var-driven and empty by default. JSON-LD and footer
  social links are `{% if %}`-gated and simply omitted until real values are confirmed and set.
- **`/our-dojos/` and `/showcase/` as distinct prefixes from `/dojos/` and `/members/`:** chosen
  specifically so CRM and public routes never share a path prefix — keeps `robots.txt`
  unambiguous and avoids any risk of a public view accidentally being reachable under a
  CRM-protected prefix or vice versa.
- **`apps.public` carries no models of its own** — deliberately thin, only views/templates,
  reading data owned by `dojos`/`cms`/`members`. Avoids duplicating relationships that already
  exist elsewhere.

**Prevention / Notes:**
- Not yet built (tracked as follow-up, not blocking): `sitemap.xml` via
  `django.contrib.sitemaps`; Editor-role CRUD views for `NewsPost` under `/cms/` (only the
  public read-only views exist so far — Editors currently need Django admin to publish news).
- Showcase listing (`/showcase/`) must only ever query name/belt/dojo — verify any future
  changes to `ShowcaseListView` don't accidentally select contact info, attendance, fees, or
  exam data.
- Any new public-facing view must use `apps.public` or extend `base_public.html` directly —
  never reuse `base.html`.

---

### [2026-06-29] — Project: v0.3.0 Frontend Layer Complete (Retroactive Entry)

**Status:** Resolved
**Severity:** N/A
**App / Module:** accounts, all 12 apps (views/urls/templates)
**Environment:** Dev

**Symptom:** N/A — scheduled milestone, logged retroactively (this entry was missed at the time
v0.3.0 shipped; added during the v0.3.1 documentation catch-up pass).

**Root Cause:** N/A

**Fix Applied:**
- `apps/accounts/templatetags/rbac_tags.py` — custom `{% has_role %}` / `{% end_has_role %}`
  block tag; all role-based nav visibility logic lives here, never as inline `{% if %}` role
  comparisons in templates.
- `apps/accounts/mixins.py` — `RoleRequiredMixin(AccessMixin)`: unauthenticated users hit
  `handle_no_permission()` (login redirect); authenticated users with the wrong role hit
  `raise PermissionDenied` (403), not a redirect — these are distinct states and must not be
  conflated.
- `templates/base.html` — full two-column sidebar layout (fixed 240px desktop sidebar,
  collapsing hamburger nav on mobile), role-gated nav links via `{% has_role %}`.
- `static/css/main.css` — design tokens (`--color-primary`, `--color-accent`,
  `--color-sidebar-bg`, etc.), sidebar/navbar styling, Noto Sans TC for Chinese character
  support.
- All 12 apps: CBVs following `LoginRequiredMixin` → `RoleRequiredMixin` → Django generic view
  pattern; Phase 1 URL patterns wired in each app's `urls.py`, included from `config/urls.py`.
- Role-scoped `DashboardView`: Grandmaster/Deputy GM/Admin see global aggregates; Coach sees
  only their own dojo's members/events via `DojoStaff` filtering; Member/Parent see only their
  own data.
- `templates/403.html`, `templates/404.html` created.

**Key Decisions:**
- CMS URL pattern uses `<int:pk>/edit/` instead of the originally planned `<slug:slug>/edit/`
  — `ContentBlock` has no slug field; the slug-based route would have raised `FieldError` at
  runtime. Caught during Claude Code's plan review before execution.
- CBV-only convention for all Phase 1 views — no function-based views, for consistency.

**Prevention / Notes:**
- v0.3.0 routed `/` directly to the authenticated `DashboardView` with no public-facing
  alternative — this was corrected in v0.3.1 (see entry above). Flagging here for historical
  accuracy: the gap existed from this milestone onward until the v0.3.1 fix.
- v0.3.1 refactor candidate identified but not yet done: duplicate nav-link HTML between the
  desktop sidebar and mobile hamburger collapse — extract into
  `templates/partials/nav_links.html` and `{% include %}` from both, so future nav changes
  don't require editing two places.

---

### [2026-06-29] — Project: v0.2.0 Commit Checkpoint

**Status:** Resolved **Severity:** N/A **App / Module:** Project **Environment:** Dev

**Symptom:** N/A — scheduled commit checkpoint.

**Root Cause:** N/A

**Fix Applied:**
- Committed v0.2.0 data layer (9 apps: activities, skills, fees, payments, communications, cms, matches, chatbot, events)
- Commit hash: `56e744ea9fb8f2726a097529285666a93c8e5ead`
- Files changed: 37 files, 2111 insertions(+), 6 deletions(-)

**Prevention / Notes:**
- Next milestone: v0.3.0 frontend views + URL routing
- Versioning standard: 0.1.x = scaffold, 0.2.x = data layer, 0.3.x = frontend, 1.0.0 = production deploy

---

### [2026-06-29] — chatbot App: FAQEntry, ChatSession & ChatMessage Models, OpenRouter Service & Admin

**Status:** Resolved **Severity:** N/A **App / Module:** chatbot **Environment:** Dev

**Symptom:** N/A — planned build step.

**Root Cause:** N/A

**Fix Applied:**
- `apps/chatbot/models.py`: Added `FAQCategory` module-level TextChoices (MEMBERSHIP / FEES / TRAINING / EXAMS / TOURNAMENTS / GENERAL). Three models: `FAQEntry` (category, question CharField max_length=500, answer TextField, is_active bool default True, order PositiveIntegerField default 0, created_by FK→AUTH_USER_MODEL PROTECT, auto timestamps; ordering `['category', 'order', 'question']`); `ChatSession` (session_key unique CharField, member FK→members.MemberProfile SET_NULL nullable — anonymous sessions allowed, started_at auto_now_add, last_active auto_now, is_closed bool; ordering `['-last_active']`); `ChatMessage` (inner `Role` TextChoices USER/ASSISTANT, session FK→ChatSession CASCADE, role, content TextField, created_at auto_now_add, input_tokens + output_tokens PositiveIntegerField default 0; ordering `['created_at']`).
- `apps/chatbot/services.py`: New file. `build_faq_context()` — lazy-loads active FAQEntry rows ordered by category/order, formats as system prompt with `## Category` headers; returns fallback string if no entries. `get_chat_response(session, user_message)` — saves user ChatMessage, fetches full session history, prepends system prompt message, calls OpenRouter via `openai.OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)` using `chat.completions.create(model=OPENROUTER_MODEL, max_tokens=1000, messages=[...])`, saves assistant ChatMessage with `prompt_tokens` / `completion_tokens`, returns reply text.
- `apps/chatbot/admin.py`: `FAQEntryAdmin` — `question_preview` display method (truncated to 80 chars), activate/deactivate bulk actions. `ChatMessageInline` (TabularInline, all fields readonly, `has_add_permission` → False, `can_delete` → False — append-only enforced). `ChatSessionAdmin` — `get_queryset` annotates `_msg_count=Count('messages')`, `message_count` display method with ordering, ChatMessageInline embedded.
- `requirements/base.txt`: Replaced `anthropic==0.34.2` with `openai==1.35.0`.
- `.env.example`: Replaced `ANTHROPIC_API_KEY` with `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OPENROUTER_MODEL`.
- `config/settings/base.py`: Replaced `ANTHROPIC_API_KEY` setting with three `OPENROUTER_*` settings read via `decouple.config`.
- `apps/chatbot/migrations/0001_initial.py`: Generated and applied cleanly; FK deps on `members.0001_initial` and `accounts.0001_initial` resolved automatically.

**Key Decisions:**
- OpenRouter replaces direct Anthropic SDK — `openai.OpenAI` client with `base_url` pointed at `https://openrouter.ai/api/v1`. Model is switchable via `OPENROUTER_MODEL` env var without code changes.
- Token fields are `response.usage.prompt_tokens` / `completion_tokens` (OpenAI-compatible schema, not Anthropic `input_tokens` / `output_tokens`).
- `build_faq_context()` queries DB on every API call — no caching in Phase 1; add `django.core.cache` in Phase 2 if latency becomes an issue.
- `ChatSession.member` nullable — FAQ bot is public-facing; anonymous sessions are first-class.
- `ChatMessage` append-only — `can_delete=False` enforced in admin inline; no delete endpoint planned.
- No views or URL routing in this phase — data + service layer only.

**Prevention / Notes:**
- Set `OPENROUTER_API_KEY` in `.env` before calling `get_chat_response()`.
- OpenRouter passes through to the upstream model unchanged — error codes follow OpenAI schema (not Anthropic). Catch `openai.APIError` in the view layer when views are wired in Phase 2.
- **Phase 2 TODO:** Add caching for `build_faq_context()`, streaming response support, and view/URL routing for the frontend widget.

---

### [2026-06-29] — matches App: Tournament, MatchEntry & KPNPDevice Models & Admin

**Status:** Resolved **Severity:** N/A **App / Module:** matches **Environment:** Dev

**Symptom:** N/A — planned build step.

**Root Cause:** N/A

**Fix Applied:**
- `apps/matches/models.py`: Added five module-level TextChoices: `MatchType` (SPARRING 搏擊 / POOMSAE 品勢 / BREAKING 破板 / OTHER 其他), `MatchResult` (WIN / LOSS / DRAW / DISQUALIFIED / WITHDREW / BYE), `WeightClass` (FINWEIGHT / FLYWEIGHT / BANTAMWEIGHT / FEATHERWEIGHT / LIGHTWEIGHT / WELTERWEIGHT / MIDDLEWEIGHT / HEAVYWEIGHT / OPEN), `Medal` (GOLD / SILVER / BRONZE / NONE), `DeviceType` (VEST / RECEIVER / HEADGUARD). Three models: `Tournament` (name, event FK→events.Event PROTECT, match_type, organised_by, location, is_international bool, notes, auto timestamps; ordering: `['-event__start_datetime', 'name']`); `MatchEntry` (tournament FK CASCADE, member FK→members.MemberProfile PROTECT, belt_at_match snapshot from BeltLevel, weight_class, result, medal default NONE, placement PositiveSmallIntegerField nullable, opponent_name, score CharField max_length=50, notes, auto timestamps; UniqueConstraint on tournament+member; verbose_name_plural 'Match Entries'); `KPNPDevice` — **stub, no logic** (device_type, serial_number unique, tournament FK→Tournament SET_NULL nullable, notes, auto timestamps; verbose_name 'KP&P Device').
- `apps/matches/admin.py`: `MatchEntryInline` (TabularInline, extra=1) with `get_readonly_fields` locking `belt_at_match` once Tournament is saved (`obj` truthy = Tournament persisted); `KPNPDeviceInline` (TabularInline, extra=0) on `TournamentAdmin`; `TournamentAdmin` — `get_queryset` annotates `_entry_count=Count('entries')` with `select_related('event')`; `@admin.display(ordering='_entry_count')` on `entry_count` column; `list_filter` on `match_type`/`is_international`. `MatchEntryAdmin` — `get_queryset` with `select_related('member__user', 'tournament')`; `search_fields` follows `member__member_id`/`member__user__last_name` project convention; `list_filter` includes cross-app `tournament__match_type`.
- `apps/matches/migrations/0001_initial.py`: Generated and applied cleanly; FK deps on `events.0001_initial` and `members.0001_initial` resolved automatically.

**Key Decisions:**
- `MatchEntry.member` uses `on_delete=PROTECT` — match history is immutable audit data; a member deletion must not silently cascade away competition records.
- `MatchEntry.tournament` uses `on_delete=CASCADE` — entries have no independent meaning without their parent tournament.
- `KPNPDevice.tournament` uses `on_delete=SET_NULL` — devices are physical assets that outlive any single tournament; unassignment (NULL) is the correct state when a tournament is removed.
- `belt_at_match` has no default — forces explicit snapshot assignment at entry creation so accidental NULL snapshots are caught at the form/API layer, not silently stored.
- `result` and `weight_class` are `blank=True` so entries can be created at registration time before the bout is fought.
- `score` is a free-text `CharField(max_length=50)` — handles both sparring point scores ("12-8") and poomsae decimal scores ("7.82"); no parsing or validation enforced at the model layer.
- `UniqueConstraint(fields=['tournament', 'member'])` enforces one entry per member per tournament at DB level, consistent with `unique_member_per_event` (events) and `unique_member_activity_event` (activities).
- `MatchEntryInline.get_readonly_fields`: `obj` is the parent Tournament in inline context — lock fires once Tournament is persisted, same snapshot-lock pattern as `SkillRecordAdmin` in `apps/skills/admin.py`.

**Prevention / Notes:**
- When creating a `MatchEntry` programmatically, always snapshot `member.current_belt` into `belt_at_match` at save time — do not derive it later at query time (same pattern as `SkillRecord.belt_level_at_assessment`).
- `score` is deliberately unvalidated free text — if structured scoring is needed in future, migrate to separate `SparringScore` / `PoomsaeScore` child models rather than adding parse logic here.
- **Phase 2 TODO:** `KPNPDevice` intentionally has no `assigned_to` (MemberProfile) field — Phase 1 is hardware inventory only. Competitor-to-device pairing, KPNP API/Bluetooth integration, and live electronic scoring are deferred to Phase 2. When implementing Phase 2, add a `MatchEntry` FK or M2M to `KPNPDevice` and a separate `KPNPSession` model for live score streaming.

---

### [2026-06-29] — cms App: ContentBlock, Announcement Models & Admin

**Status:** Resolved **Severity:** N/A **App / Module:** cms **Environment:** Dev

**Symptom:** N/A — planned build step.

**Root Cause:** N/A

**Fix Applied:**
- `apps/cms/models.py`: Added `PageSection` (HOME / ABOUT / COACHES / SCHEDULE / NEWS / CONTACT / OTHER) and `ContentStatus` (DRAFT / PUBLISHED / ARCHIVED) module-level TextChoices; `ContentBlock` (title, section, status default DRAFT, order PositiveIntegerField default 0, body TextField, image ImageField upload_to='cms/' blank=True, is_featured bool default False, published_at nullable DateTimeField, created_by FK→AUTH_USER_MODEL PROTECT, auto timestamps; ordering: `['section', 'order', '-published_at']`); `Announcement` (title, body, status default DRAFT, is_pinned bool default False, published_at/expires_at nullable DateTimeFields, created_by FK→AUTH_USER_MODEL PROTECT, auto timestamps; ordering: `['-is_pinned', '-published_at']`); `is_active` computed property on `Announcement`.
- `apps/cms/admin.py`: `ContentBlockAdmin` with section/status/is_featured filters, `action_publish` and `action_archive` bulk actions; `AnnouncementAdmin` with `is_active` display column (`@admin.display(boolean=True)`), `action_publish` bulk action.
- `apps/cms/migrations/0001_initial.py`: Generated and applied cleanly; no cross-app FK dependencies.

**Key Decisions:**
- Ordering is soft (`Meta.ordering`) — not DB-enforced; a `UniqueConstraint` on `(section, order)` was considered and dropped: Django admin saves objects individually, making same-transaction order swaps impossible and reordering impractical in practice.
- `published_at` set via bulk `.update()` in admin action — acceptable for CMS use case; individual model `save()` not required here.
- `is_active` is a computed property — never stored, always derived at query time from `status` and `expires_at`.
- No slug/URL routing yet — public views deferred to frontend phase.

**Prevention / Notes:**
- **Security TODO:** `ContentBlock.body` accepts raw HTML — sanitisation required in frontend phase before rendering (e.g., server-side `bleach` or client-side `DOMPurify`). Do not render this field unsanitised in any public template.
- `image` is stored in `MEDIA_ROOT/cms/` — acceptable for public website content; ensure `MEDIA_ROOT` is excluded from version control.

---

### [2026-06-29] — communications App: NotificationTemplate, Notification, Services & Celery Task

**Status:** Resolved **Severity:** N/A **App / Module:** communications **Environment:** Dev

**Symptom:** N/A — planned build step.

**Root Cause:** N/A

**Fix Applied:**
- `apps/communications/models.py`: Added `NotificationChannel` (IN_APP / EMAIL / WHATSAPP) and `NotificationStatus` (PENDING / SENT / DELIVERED / FAILED / READ) TextChoices; `NotificationTemplate` (name unique, channel, subject blank=True, body_template, is_active, auto timestamps); `Notification` (recipient FK→members.MemberProfile CASCADE, template FK→NotificationTemplate PROTECT nullable, channel, subject, body, status default PENDING, sent_at/read_at nullable DateTimeFields, failure_reason CharField 500, created_at auto; ordering: `-created_at`)
- `apps/communications/services.py` (new): Pure Python dispatch module — `render_body(template_str, context)` renders a Django template string; `send_notification(notification)` dispatches by channel, mutates status/sent_at/failure_reason in place; caller must call `.save()` after. No admin or Celery imports (separation of concerns).
- `apps/communications/tasks.py` (new): `dispatch_pending_notifications` `@shared_task`; lazy imports inside task body; uses `select_related('recipient__user', 'template')` to avoid N+1 on email dispatch; calls `save(update_fields=[...])` per notification; returns a summary string.
- `config/settings/base.py`: Added `dispatch-pending-notifications-every-5-min` (300 s) to `CELERY_BEAT_SCHEDULE`.
- `apps/communications/admin.py`: `NotificationTemplateAdmin` with channel/is_active filters; `NotificationAdmin` with `action_retry_failed` — resets status to PENDING and **clears `failure_reason = ''`** before retry so stale error messages do not persist.
- `apps/communications/migrations/0001_initial.py`: Generated and applied cleanly; FK dep on `members.0001_initial` resolved automatically.

**Key Decisions:**
- `body` on `Notification` is a snapshot stored at creation time — template body may change after send, but the rendered text is immutable evidence of what was sent.
- WhatsApp channel is a Phase 1 stub — `send_notification` marks WhatsApp notifications as FAILED with a human-readable reason; no provider SDK integrated yet.
- `failure_reason` is a `CharField(max_length=500)` — truncation to 500 chars applied in `send_notification` via `str(e)[:500]` before assignment.
- `NotificationTemplate` FK on `Notification` is nullable (`null=True, blank=True`) to support ad-hoc notifications created without a template.
- `on_delete=PROTECT` on template FK — prevents accidental template deletion while notifications reference it.

**Prevention / Notes:**
- When sending notifications in code, always call `render_body()` first and store the result in `Notification.body` before saving — the task does not re-render from the template.
- `select_related('recipient__user')` is mandatory in any queryset that dispatches EMAIL notifications; without it, each `notification.recipient.user.email` access is a separate query.

---

### [2026-06-29] — payments App: PaymentRecord, FPSQRCode Models, Celery Stub & Admin

**Status:** Resolved **Severity:** N/A **App / Module:** payments **Environment:** Dev

**Symptom:** N/A — planned build step.

**Root Cause:** N/A

**Fix Applied:**
- Defined `PaymentMethod` and `PaymentStatus` TextChoices and `PaymentRecord`, `FPSQRCode` models in `apps/payments/models.py`.
- `annual_fee` FK uses `on_delete=PROTECT` — payment records are audit evidence and must survive fee record changes; string reference `'fees.AnnualFee'` avoids circular imports.
- `confirmed_by` FK uses `on_delete=SET_NULL` — staff accounts can be deactivated without destroying payment records.
- `FPSQRCode.generate_qr()` builds an EMVCo-format FPS payload (TLV encoding, tag `26` for merchant account info under `hk.fps` GUID).
- CRC-16/CCITT-FALSE implemented as a manual byte loop (poly `0x1021`, init `0xFFFF`, no reflection). **CRC-16 not validated against official HKMA/FPS test vectors** — flagged with TODO comment referencing HKMA FPS QR Code Specification v1.x, Section 4.11.
- `apps/payments/tasks.py` created with `reconcile_fps_payments` `@shared_task` stub; queries `SCREENSHOT_UPLOADED` records and returns a count string; no IMAP logic.
- `CELERY_BEAT_SCHEDULE` in `config/settings/base.py` updated with a 15-minute schedule for `reconcile_fps_payments`.
- `apps/payments/migrations/0001_initial.py` generated and applied; FK deps on `fees.0001_initial` and `accounts.0001_initial` resolved automatically.
- `apps/payments/admin.py`: `FPSQRCodeInline` (StackedInline) inside `PaymentRecordAdmin`; `action_manually_confirm` uses `confirmed_by_id=request.user.pk` (not `confirmed_by=request.user`) for correct ORM bulk `.update()` behaviour; queryset filtered to `SCREENSHOT_UPLOADED` / `EMAIL_MATCHED` before update.

**Prevention / Notes:**
- `screenshot` and `qr_image` ImageFields stored in public `MEDIA_ROOT` for dev convenience. Must be moved to `PRIVATE_STORAGE_ROOT` (served via Django `FileResponse` with RBAC check) before production deployment.
- No `django-fsm` for `PaymentStatus` — plain `CharField` with `TextChoices`; status transitions enforced at the action/task layer.
- No Stripe views or webhook handlers in this phase — `reference_id` field stores the PaymentIntent ID only; Stripe webhooks deferred to a later milestone.
- When implementing real IMAP reconciliation, track processed email UIDs to prevent double-reconciliation on Celery retry.

---

### [2026-06-28] — skills App: SkillRecord Model & Admin

**Status:** Resolved **Severity:** N/A **App / Module:** skills **Environment:** Dev

**Symptom:** N/A — planned build step.

**Root Cause:** N/A

**Fix Applied:**
- Defined `SkillCategory` and `SkillResult` TextChoices and `SkillRecord` model in `apps/skills/models.py`.
- `belt_level_at_assessment` imports `BeltLevel` from `apps.members.models` — stored as a snapshot at assessment time; never derived at query time.
- `activity_application` FK uses `on_delete=PROTECT` so exam records cannot be silently deleted.
- `assessed_by` FK points to `settings.AUTH_USER_MODEL` (coach user), not `MemberProfile`.
- `UniqueConstraint` on `(member, activity_application, skill_name)` enforces one result per skill per exam.
- Admin uses `get_readonly_fields` to allow `assessed_at` on create, then lock it after save.
- Generated and applied `apps/skills/migrations/0001_initial.py`.

**Prevention / Notes:**
Belt snapshot pattern is intentional — do not refactor to derive belt from member at query time.

---

### [2026-06-28] — activities App: ActivityTemplate, ActivityEvent & ActivityApplication Models

**Status:** Resolved **Severity:** N/A **App / Module:** activities **Environment:** Dev

**Symptom:** N/A — planned build step.

**Root Cause:** N/A

**Fix Applied:**
- `apps/activities/models.py`: Created `ActivityType` and `ApplicationStatus` TextChoices enums (module-level); `ActivityTemplate` (name, activity_type, form_schema JSONField, is_active, created_by FK→AUTH_USER_MODEL PROTECT, auto timestamps); `ActivityEvent` (template FK→ActivityTemplate PROTECT, event FK→events.Event PROTECT, dojo FK→dojos.DojoEntity PROTECT, scheduled_date, notes, created_at); `ActivityApplication` (activity_event FK PROTECT, member FK→members.MemberProfile CASCADE, form_data JSONField, state FSMField protected=True, coach_recommendation, gm_notes, submitted_at, completed_at, UniqueConstraint on activity_event+member)
- FSM transitions: `submit` (DRAFT→AWAITING_COACH_REC, sets submitted_at), `recommend` (AWAITING_COACH_REC→AWAITING_GM_APPROVAL), `approve` (AWAITING_GM_APPROVAL→PENDING_PAYMENT), `reject` (AWAITING_GM_APPROVAL→REJECTED), `confirm_payment` (PENDING_PAYMENT→PROCESSING_PDF), `complete` (PROCESSING_PDF→COMPLETED, sets completed_at)
- `apps/activities/admin.py`: `ActivityTemplateAdmin`, `ActivityEventAdmin`, `ActivityApplicationAdmin` with `action_submit` and `action_approve` admin actions; both actions filter queryset to the correct source state before calling the transition, silently skipping inapplicable rows
- `apps/activities/migrations/0001_initial.py`: Generated and applied cleanly

**Decisions:**
- `JSONField` used for both `form_schema` (template field definitions) and `form_data` (submitted answers) — SQLite-compatible since Django 3.1; no special backend handling required in dev; PostgreSQL (prod) stores as native JSONB
- `FSMField(protected=True)` — `state` can only change via defined transition methods; direct assignment raises `AttributeError`; enforces linear workflow at the model layer
- `form_data` is a snapshot captured at submission time and is **never re-validated** against `template.form_schema` after submission — the schema may change, but submitted data is immutable evidence
- No PDF generation logic added — deferred to fees/payments phase; `PROCESSING_PDF` state is a placeholder for that Celery task
- `UniqueConstraint(fields=['activity_event', 'member'])` — one application per member per exam event; duplicate attempts raise `IntegrityError`
- `submitted_at` / `completed_at` set inside transition bodies (not in `save()`) so timestamps are only written on the correct state change, not on any save
- Admin actions skip rows not in the correct source state rather than raising errors — safe for bulk selection

**Prevention / Notes:**
- `django-fsm 2.8.2` already present in `requirements/base.txt` — no install step needed
- When calling a transition in code, always call `obj.save()` immediately after to persist both the new state and any fields mutated inside the transition body (e.g., `submitted_at`)

---

### [2026-06-28] — events App: Event & AttendanceLog Models

**Status:** Resolved **Severity:** N/A **App / Module:** events **Environment:** Dev

**Symptom:** N/A — planned build step.

**Root Cause:** N/A

**Fix Applied:**
- Added `EventType`, `EventStatus`, `CheckInMethod` TextChoices enums and `Event`, `AttendanceLog` models to `apps/events/models.py`.
- `apps/events/admin.py`: `EventAdmin` with `AttendanceLogInline`; annotated queryset on `get_queryset` avoids N+1 on `attendance_count` list_display column (`Count('attendancelog')` — one SQL per page load). GPS fields shown as readonly in inline for debug visibility.
- Migration `apps/events/migrations/0001_initial.py` generated and applied cleanly.

**Prevention / Notes:**
- **AttendanceLog is the SSOT for all attendance data** — no counter fields anywhere; always query live.
- `UniqueConstraint(fields=['event', 'member'])` enforces one check-in per member per event at DB level.
- GPS fields (`gps_lat`, `gps_lng`) are nullable — QR geofence logic (100 m fence) deferred to a later phase; model stores coordinates only.
- `event_type=EXAM` reserved for future FK to activities app — do not add that FK prematurely.
- `choices=TextChoices` (bare class) fails Django system checks on this version — must pass `TextChoices.choices` explicitly.

---

### [2026-06-22] — members App: MemberProfile & MemberDojoEnrollment Models

**Status:** Resolved **Severity:** N/A **App / Module:** members **Environment:** Dev

**Symptom:** N/A — planned build step.

**Root Cause:** N/A

**Fix Applied:**

- `apps/members/models.py`: Created three top-level `TextChoices` enums — `BeltLevel` (11 levels WHITE→BLACK in ascending order), `MemberTier` (COLOUR_BELT/POOM/STUDENT_BLACK/ADULT_BLACK/OVERSEAS_BLACK mapped to annual fee amounts), `MemberStatus` (ACTIVE/INACTIVE/SUSPENDED/GRADUATED)
- `MemberProfile`: OneToOneField→accounts.User (PROTECT), `member_id` (unique CharField, club-assigned), `date_of_birth`, `gender` (inner TextChoices), `emergency_contact_name/phone`, `current_belt` (default WHITE), `tier` (default COLOUR_BELT), `status` (default ACTIVE), `primary_dojo` FK→dojos.DojoEntity (PROTECT), `joined_date`, `notes` (blank=True), `created_at`/`updated_at` (auto); properties: `full_name`, `age`, `is_active`
- `MemberDojoEnrollment`: FK→MemberProfile (CASCADE), FK→dojos.DojoEntity (PROTECT), `enrolled_date`, `is_active`; `UniqueConstraint(fields=['member','dojo'])` — raises IntegrityError on duplicate enrollment
- `apps/members/admin.py`: `MemberDojoEnrollmentInline` (TabularInline) inside `MemberProfileAdmin`; list_display: member_id/full_name/current_belt/tier/status/primary_dojo; list_filter: status/tier/current_belt/primary_dojo; search_fields: member_id/user__first_name/user__last_name/user__email; readonly_fields: created_at/updated_at
- `apps/members/migrations/0001_initial.py`: Generated and applied — `MemberProfile`, `MemberDojoEnrollment`, `unique_member_dojo_enrollment` constraint all green

**Decisions:**

- `BeltLevel` and `MemberTier` are intentionally separate — a poom-belt student and a colour-belt student may hold adjacent belts but pay different fees; tier drives billing, belt drives progression
- `current_belt` tracks present level only — historical belt progression will live in `SkillRecord` (skills app, Phase 6)
- `member_id` is `CharField`, not `AutoField` — club-assigned in the form "ADV-YYYY-NNN"; admin staff enter it manually
- `MemberProfile.is_active` is a `@property` shadowing the status check — not a separate DB column — to avoid sync bugs between `status` and a boolean field
- `on_delete=PROTECT` on `primary_dojo` — member record survives dojo closure; FK must be re-assigned before deleting a dojo
- `on_delete=CASCADE` on `MemberDojoEnrollment.member` — enrollment rows are owned by the profile and deleted with it
- No FK to events/skills/fees yet — members stays upstream in the dependency chain as per project constraint

**Prevention / Notes:**

- `UniqueConstraint` on `(member, dojo)` is DB-level; Django admin raises a friendly `ValidationError` before it hits the DB, but raw ORM inserts will raise `IntegrityError` — integration tests should test both paths
- `age` property has correct birthday-not-yet-reached logic: subtracts 1 if today's (month, day) is before the birthday tuple

---

### [2026-06-22] — dojos App: DojoEntity & DojoStaff Models

**Status:** Resolved **Severity:** N/A **App / Module:** dojos **Environment:** Dev

**Symptom:** N/A — planned build step.

**Root Cause:** N/A

**Fix Applied:**

- `apps/dojos/models.py`: Created `DojoEntity` (name, slug unique, address, district TextChoices, phone blank=True, is_active, created_at auto) and `DojoStaff` (FK→DojoEntity PROTECT, FK→accounts.User PROTECT, role TextChoices: HEAD_COACH/ASSISTANT_COACH/ADMIN_STAFF, joined_date DateField, is_active)
- `apps/dojos/admin.py`: Registered `DojoEntity` with `DojoStaffInline` (TabularInline); `list_display` for entity: name/district/is_active; registered `DojoStaff` directly with user/dojo/role/is_active; `prepopulated_fields` for slug
- `apps/dojos/migrations/0001_initial.py`: Generated and applied — `DojoEntity`, `DojoStaff`, `unique_head_coach_per_dojo` constraint all green

**Decisions:**

- `DojoStaff.role` is a per-dojo position entirely separate from `accounts.User.role` (system-level RBAC) — two different concepts intentionally modelled separately
- `UniqueConstraint` with `condition=Q(role='HEAD_COACH')` enforces exactly one HEAD_COACH per dojo at the DB level; a second assignment raises `IntegrityError`
- `on_delete=PROTECT` on both FKs — a dojo with staff records cannot be deleted; staff record must be cleared first
- No FK to `members` app — dojos stays upstream in the dependency chain

**Constraint Behaviour:**

- Partial unique index (`unique_head_coach_per_dojo`) is enforced at the database level via PostgreSQL partial index (or SQLite equivalent); attempting to insert a second HEAD_COACH for the same dojo raises `django.db.utils.IntegrityError`
- ASSISTANT_COACH and ADMIN_STAFF roles are unconstrained in count — multiple allowed per dojo

**Prevention / Notes:**

- Slug must be set at creation — `prepopulated_fields` handles this in admin; API serializers will need explicit slug handling when that layer is built
- District choices list derived from HK districts mentioned in Blueprint V0.7.1; can be extended as new branches open

---

### [2026-06-22] — accounts App: CustomUser Model & First Migration

**Status:** Resolved **Severity:** N/A **App / Module:** accounts **Environment:** Dev

**Symptom:** N/A — planned build step.

**Root Cause:** N/A

**Fix Applied:**

- `apps/accounts/models.py`: Created `User(AbstractUser)` with `role` (TextChoices: GRANDMASTER / DEPUTY_GRANDMASTER / ADMIN / EDITOR / COACH / MEMBER / PARENT, default MEMBER), `phone` (CharField, blank=True), `avatar` (ImageField, upload_to='avatars/', blank=True)
- `apps/accounts/admin.py`: Registered `CustomUser` with `UserAdmin`, extended fieldsets to expose `role`, `phone`, `avatar`; `list_display` includes `username`, `email`, `role`, `is_staff`, `is_active`
- `apps/accounts/migrations/0001_initial.py`: Generated and applied — all 19 migrations green
- `.env` created from `.env.example` with generated `DJANGO_SECRET_KEY` for dev (was missing — blocked `manage.py`)

**Decisions:**
- `Role` defined as inner `TextChoices` class on `User` — keeps choices co-located with the model, avoids a separate constants file at this stage
- No FK to other apps — accounts has zero cross-app dependencies as required
- No RBAC logic added — role field only; permission logic deferred to a later session

**Prevention / Notes:**
- `.env` must exist before any `manage.py` command; `python-decouple` raises `UndefinedValueError` otherwise
- Always run `makemigrations accounts` before `migrate` so custom user table is created before `django.contrib.admin` tables (which FK to `AUTH_USER_MODEL`)

---

### [2026-06-22] — Architecture Decision: PayMe / FPS Payment Flow

**Status:** Resolved **Severity:** N/A **App / Module:** payments **Environment:** Dev

**Symptom:** N/A — pre-build architectural decision recorded before `payments` app is written.

**Root Cause:** PayMe HK does not provide a reliable public REST SDK. Stripe handles international cards; local HK payments use FPS (Faster Payment System).

**Fix Applied:**

Confirmed implementation for `payments` app:

1. FPS QR code generation via `qrcode[pil]` with merchant details pre-filled
2. Member uploads payment screenshot via a Django form; file stored in `private_media/` (never publicly served)
3. Celery background task polls incoming IMAP email for FPS confirmation notices; matches subject / amount / date against pending `Payment` records; auto-advances status on match; flags unmatched records for manual staff review
4. `Payment` model status machine: `PENDING_QR → SCREENSHOT_UPLOADED → EMAIL_MATCHED → MANUALLY_CONFIRMED → FAILED`

No PayMe Business SDK integration.

**Prevention / Notes:**

- Screenshot files must be stored in `private_media/` and served only via Django `FileResponse` after RBAC check — same private storage rule as certificates.
- IMAP polling Celery task must use idempotent logic (track already-processed email UIDs) to avoid double-reconciliation on retry.
- All payment amount comparisons must use `Decimal`, never `float`.

---

### [2026-06-22] — Project Initialised

**Status:** Resolved **Severity:** N/A **App / Module:** Project setup **Environment:** Dev

**Symptom:** N/A — initial project creation.

**Root Cause:** N/A

**Fix Applied:**

- Django project scaffolded at `R:\My Drive\Work\Taekwondo\Coding\CRM DEV\ADV_Web_Project`  
- Settings split into `config/settings/base.py`, `dev.py`, `prod.py`  
- All 12 Django apps created as skeletons under `apps/` (accounts, members, dojos, events, activities, skills, fees, payments, communications, cms, matches, chatbot)  
- `config/celery.py` added for Celery + Redis async task queue  
- `README.md` and `DEBUGLOG.md` created  
- `.gitignore`, `.env.example`, `requirements/` created  
- `.github/workflows/ci.yml` placeholder created  
- Git repository initialised — commit hash: `998068678911bad01f4843f74573ed11cb5c96b0`

**Prevention / Notes:**

- Always use `--settings=config.settings.dev` flag for local management commands  
- Never commit `.env` — update `.env.example` whenever a new variable is added  
- Reference: System Spec Blueprint V0.7.1 (`docs/System_Spec_Blueprint_V0.7.1.pdf`)

---

### [2026-06-29] — fees App: AnnualFee, Invoice & WeasyPrint PDF Generation
**Status:** Resolved
**Severity:** Low
**App / Module:** fees
**Environment:** Dev

**Symptom:** fees app was an empty skeleton with no models, admin, or migration.

**Root Cause:** New milestone — implementing annual membership fee records and PDF invoice generation.

**Fix Applied:**
- Added `FeeStatus` TextChoices (`UNPAID / PARTIAL / PAID / WAIVED / OVERDUE`) and `AnnualFee` model with `UniqueConstraint(fields=['member','year'])` — one fee record per member per year
- `tier_at_billing` is a snapshot field (same pattern as `belt_level_at_assessment` in skills): captures the member's `MemberTier` at the time the fee is raised; never re-derived at query time because the member's tier may change later
- `amount_due` stored explicitly — not derived from tier at query time; billed amount is immutable after creation
- Added `balance_due` and `is_overdue` as `@property` methods on `AnnualFee`
- Added `Invoice` model with `OneToOneField → AnnualFee`; `invoice_number` uses a UUID-based default (`INV-{year}-{6-char hex}`) to avoid race conditions that `count()+1` would have under concurrent creation
- `generate_invoice_number` defined before `Invoice` class (no forward reference needed since it does not query `Invoice.objects`)
- `Invoice.generate_pdf()` uses WeasyPrint with `base_url=str(settings.BASE_DIR)` — `str()` cast required because `BASE_DIR` is a `pathlib.Path` and WeasyPrint expects a string
- PDF written to `MEDIA_ROOT/invoices/{invoice_number}.pdf`; `pdf_file` (FileField) updated via `save(update_fields=['pdf_file'])` to avoid overwriting other fields
- `templates/fees/invoice_pdf.html` is a standalone HTML file (no Django template inheritance) — WeasyPrint renders outside the request/response cycle so `{% extends %}` has no value here; Arial font-family set as fallback for Windows dev environments
- `AnnualFeeAdmin` uses a `get_balance_due` method decorated with `@admin.display(description='Balance Due (HK$)')` — Django admin cannot call model properties directly in `list_display` without this wrapper
- `InvoiceAdmin` exposes `action_generate_pdf` bulk action

**Prevention / Notes:**
- `pdf_file` currently stored in `MEDIA_ROOT/invoices/` (public media) — move to `PRIVATE_STORAGE_ROOT` during production hardening phase
- When testing `is_overdue`: set `due_date` to a past date and `status` to anything other than `PAID`; the property checks both conditions
- Migration: `apps/fees/migrations/0001_initial.py` applied cleanly

---

