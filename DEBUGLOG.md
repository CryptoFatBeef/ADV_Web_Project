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

