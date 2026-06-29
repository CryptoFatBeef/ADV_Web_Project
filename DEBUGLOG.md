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

