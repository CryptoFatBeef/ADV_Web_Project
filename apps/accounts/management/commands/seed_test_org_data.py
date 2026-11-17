"""
apps/accounts/management/commands/seed_test_org_data.py

Seed organisational data for the verification suite. Three modes:

  --minimal  (default)
      Creates one placeholder DojoEntity + minimal FK rows so RBAC tests
      don't fail on missing relations instead of missing permissions.
      Fast; no file I/O; uses test_credentials.csv usernames.

  --real-data
      Reads fixtures/legacy_data/memebers.csv + goals.csv + members_images/.
      Seeds 161 real black-belt members as User + MemberProfile + DojoStaff,
      with synthesised HKTKD Dan certifications prepended before goals.csv entries.

  --full
      State-coverage dataset across all 14 apps — every enum value, every
      FSM state, every role-visible branch gets at least one row. Uses the
      12-persona test_credentials.csv (t0.2.0) at 2 real dojos (WongTaiSin,
      TaiPo). Requires seed_test_users to have been run first. Writes
      verification/fixtures/full_dataset_manifest.json.

Hard-guarded against prod: raises CommandError if DEBUG is False.

Usage:
    python manage.py seed_test_org_data --settings=config.settings.dev
    python manage.py seed_test_org_data --real-data --settings=config.settings.dev
    python manage.py seed_test_org_data --full --settings=config.settings.dev
"""
import csv
import hashlib
import json
from datetime import date, datetime
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import User
from apps.activities.models import ActivityApplication, ActivityEvent, ActivityTemplate, ActivityType
from apps.chatbot.models import ChatMessage, ChatSession, FAQCategory, FAQEntry
from apps.cms.models import Announcement, ContentBlock, ContentStatus, NewsPost, PageSection
from apps.communications.models import Notification, NotificationChannel, NotificationStatus
from apps.dojos.models import DojoEntity, DojoStaff
from apps.enrollment.models import EnrollmentLead
from apps.events.models import AttendanceLog, CheckInMethod, Event, EventStatus, EventType
from apps.fees.models import AnnualFee, FeeStatus, Invoice
from apps.matches.models import MatchEntry, MatchResult, MatchType, Medal, Tournament
from apps.members.models import (
    BeltLevel, MemberDojoEnrollment, MemberProfile, MemberStatus, MemberTier,
)
from apps.payments.models import PaymentMethod, PaymentRecord, PaymentStatus
from apps.skills.models import SkillCategory, SkillRecord, SkillResult

# ---------------------------------------------------------------------------
# --full: anchored date constants (never date.today() in seeded data values,
# so re-runs produce byte-identical output).
# ---------------------------------------------------------------------------
SEED_JOIN_DATE = date(2024, 1, 1)
SEED_EVENT_PAST_1 = timezone.make_aware(datetime(2025, 3, 1, 10, 0))
SEED_EVENT_PAST_2 = timezone.make_aware(datetime(2025, 6, 1, 14, 0))
SEED_EVENT_PAST_3 = timezone.make_aware(datetime(2025, 9, 1, 9, 0))
SEED_EVENT_PAST_4 = timezone.make_aware(datetime(2025, 11, 1, 9, 0))
SEED_EVENT_FUTURE_1 = timezone.make_aware(datetime(2026, 6, 1, 10, 0))
SEED_EVENT_FUTURE_2 = timezone.make_aware(datetime(2026, 7, 1, 14, 0))
SEED_EVENT_FUTURE_3 = timezone.make_aware(datetime(2026, 8, 1, 9, 0))
SEED_EVENT_FUTURE_4 = timezone.make_aware(datetime(2026, 9, 1, 9, 0))
SEED_DOB = date(1995, 1, 1)
SEED_ANNOUNCEMENT_PUBLISHED_AT = timezone.make_aware(datetime(2026, 1, 1, 9, 0))
SEED_ANNOUNCEMENT_EXPIRES_AT = timezone.make_aware(datetime(2026, 12, 31, 23, 59))
SEED_NEWS_PUBLISHED_AT = timezone.make_aware(datetime(2026, 1, 15, 9, 0))

FIXTURES_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "verification" / "fixtures"
)
LEGACY_DATA_DIR = FIXTURES_DIR / "legacy_data"
MEMBERS_CSV = LEGACY_DATA_DIR / "memebers.csv"
GOALS_CSV = LEGACY_DATA_DIR / "goals.csv"
MEMBERS_IMAGES_DIR = LEGACY_DATA_DIR / "members_images"

# System role from HKTKD Dan grade
LEVEL_TO_ROLE = {
    9: "GRANDMASTER",
    8: "DEPUTY_GRANDMASTER",
    7: "DEPUTY_GRANDMASTER",
    6: "COACH",
    5: "COACH",
    4: "COACH",
    3: "MEMBER",
    2: "MEMBER",
    1: "MEMBER",
}

# Tier heuristic: Dan grade 1-3 = junior black belt = STUDENT_BLACK
LEVEL_TO_TIER = {
    9: MemberTier.ADULT_BLACK,
    8: MemberTier.ADULT_BLACK,
    7: MemberTier.ADULT_BLACK,
    6: MemberTier.ADULT_BLACK,
    5: MemberTier.ADULT_BLACK,
    4: MemberTier.ADULT_BLACK,
    3: MemberTier.STUDENT_BLACK,
    2: MemberTier.STUDENT_BLACK,
    1: MemberTier.STUDENT_BLACK,
}

DAN_ORDINAL = {
    1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th",
    6: "6th", 7: "7th", 8: "8th", 9: "9th",
}

PLACEHOLDER_DOJO_SLUG = "verification-placeholder-dojo"

# Roles that need a DojoStaff FK row for --minimal seeding
COACH_ROLES = {"GRANDMASTER", "DEPUTY_GRANDMASTER", "ADMIN", "EDITOR", "COACH"}
# Roles that need a MemberProfile FK row
MEMBER_ROLES = {"MEMBER", "PARENT"}


def _make_dan_certification(level: int) -> dict:
    """Synthesise a HKTKD Dan grade certification entry from memebers.csv Level field."""
    return {
        "org_en":   "Hong Kong, China Taekwondo Association",
        "org_zh":   "中國香港跆拳道協會",
        "level_en": f"{DAN_ORDINAL[level]} Dan Black Belt",
        "level_zh": f"黑帶{level}段",
        "year":     "N/G",
        "source":   "memebers_csv_level_field",
    }


def _parse_name(name_en: str) -> tuple[str, str]:
    """Split 'Lai Yiu Kam Andy (Chairman / Technical Adviser)' → (first, last)."""
    # Strip parenthetical title
    name = name_en.split("(")[0].strip()
    parts = name.split()
    if len(parts) >= 2:
        return parts[0], " ".join(parts[1:])
    return name, ""


def _get_or_create_placeholder_dojo() -> DojoEntity:
    dojo, created = DojoEntity.objects.get_or_create(
        slug=PLACEHOLDER_DOJO_SLUG,
        defaults={
            "name":     "Verification Placeholder Dojo",
            "address":  "N/A — seeded for verification suite only",
            "district": DojoEntity.District.TAI_PO,
            "is_active": True,
        },
    )
    return dojo


class Command(BaseCommand):
    help = "Seed organisational data (dojos, members, staff) for the verification suite"

    def add_arguments(self, parser):
        parser.add_argument(
            "--real-data",
            action="store_true",
            help="Seed from fixtures/legacy_data/memebers.csv + goals.csv (161 members)",
        )
        parser.add_argument(
            "--full",
            action="store_true",
            help="Seed the full state-coverage dataset across all 14 apps (t0.2.0)",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "seed_test_org_data must only run in DEBUG mode. "
                "Never seed test data into a production database."
            )

        if options["full"]:
            self._seed_full()
        elif options["real_data"]:
            self._seed_real_data()
        else:
            self._seed_minimal()

    # ------------------------------------------------------------------
    # --minimal (default)
    # ------------------------------------------------------------------
    def _seed_minimal(self):
        self.stdout.write("Mode: --minimal")
        dojo = _get_or_create_placeholder_dojo()
        self.stdout.write(f"  Placeholder dojo: {dojo.name}")

        # Ensure test users exist (seed_test_users should have been run first)
        test_users = User.objects.filter(username__startswith="test_")
        if not test_users.exists():
            self.stdout.write(
                self.style.WARNING(
                    "  No test_* users found. Run seed_test_users first."
                )
            )
            return

        for user in test_users:
            if user.role in COACH_ROLES:
                DojoStaff.objects.get_or_create(
                    user=user,
                    dojo=dojo,
                    defaults={
                        "role": "HEAD_COACH" if user.role == "GRANDMASTER" else "ASSISTANT_COACH",
                        "joined_date": date(2024, 1, 1),
                        "is_active": True,
                        "is_public": False,
                    },
                )
                self.stdout.write(f"  DojoStaff ← {user.username} ({user.role})")

            if user.role in MEMBER_ROLES:
                if not MemberProfile.objects.filter(user=user).exists():
                    MemberProfile.objects.create(
                        user=user,
                        member_id=f"VERIFY-{user.username.upper()}",
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
                    self.stdout.write(f"  MemberProfile ← {user.username} ({user.role})")

        self.stdout.write(self.style.SUCCESS("\nMinimal seed complete."))

    # ------------------------------------------------------------------
    # --real-data
    # ------------------------------------------------------------------
    def _seed_real_data(self):
        self.stdout.write("Mode: --real-data")

        if not MEMBERS_CSV.exists():
            raise CommandError(f"memebers.csv not found: {MEMBERS_CSV}")
        if not GOALS_CSV.exists():
            raise CommandError(f"goals.csv not found: {GOALS_CSV}")

        dojo = _get_or_create_placeholder_dojo()
        self.stdout.write(f"  Placeholder dojo: {dojo.name}")

        # Load goals indexed by PersonIndex (int)
        goals_by_person: dict[int, list[dict]] = {}
        with open(GOALS_CSV, encoding="utf-8-sig") as f:
            for goal in csv.DictReader(f):
                if goal.get("Allow_EN", "").strip().upper() == "T":
                    idx = int(goal["PersonIndex"])
                    goals_by_person.setdefault(idx, []).append(goal)

        # Load members and seed
        with open(MEMBERS_CSV, encoding="utf-8-sig") as f:
            members = list(csv.DictReader(f))

        created_count = updated_count = 0
        for row in members:
            level = int(row["Level"])
            person_index = int(row["PersonIndex"])
            first_name, last_name = _parse_name(row["Name_EN"])

            # 1. Build certifications list
            certifications = [_make_dan_certification(level)]
            for goal in goals_by_person.get(person_index, []):
                certifications.append({
                    "org_en":   goal["Name_EN"],
                    "org_zh":   goal["Name_zh_HK"],
                    "level_en": goal["Level_EN"],
                    "level_zh": goal["Level_zh_HK"],
                    "year":     goal["Year_EN"],
                    "source":   "goals_csv",
                })

            # 2. User
            user, created = User.objects.update_or_create(
                username=row["ID"],
                defaults={
                    "first_name": first_name,
                    "last_name":  last_name,
                    "role":       LEVEL_TO_ROLE[level],
                    "is_active":  True,
                },
            )
            if created:
                user.set_password(
                    hashlib.sha256(f"legacy-seed:{row['ID']}".encode()).hexdigest()[:16]
                )
                user.save(update_fields=["password"])
                created_count += 1
            else:
                updated_count += 1

            # 3. MemberProfile
            tier = LEVEL_TO_TIER[level]
            MemberProfile.objects.update_or_create(
                user=user,
                defaults={
                    "current_belt":           BeltLevel.BLACK,
                    "tier":                   tier,
                    "status":                 MemberStatus.ACTIVE,
                    "member_id":              f"ADV-LEGACY-{person_index:03d}",
                    "joined_date":            date.today(),
                    "primary_dojo":           dojo,
                    "date_of_birth":          date(1990, 1, 1),
                    "gender":                 "OTHER",
                    "emergency_contact_name": "N/G",
                    "emergency_contact_phone": "N/G",
                },
            )
            self.stdout.write(
                f"  [{row['PersonIndex']:>3}] {row['ID']:20s} "
                f"Level={level} role={LEVEL_TO_ROLE[level]:20s} tier={tier}"
            )
            self.stdout.write(
                f"       INFO: tier={tier} assigned by Dan-grade heuristic; review individually"
            )

            # 4. DojoStaff
            # CRITICAL: unique_head_coach_per_dojo constraint — only Level 9 (Chairman) = HEAD_COACH.
            # Assigning HEAD_COACH to Level >= 7 would IntegrityError on the second insert
            # since all members share the same default_dojo placeholder.
            dojo_role = "HEAD_COACH" if level == 9 else "ASSISTANT_COACH"
            photo_path = MEMBERS_IMAGES_DIR / row["Image"]
            staff_defaults = {
                "role":         dojo_role,
                "joined_date":  date.today(),
                "is_active":    True,
                "is_public":    True,
                "bio_zh":       row["Name_zh_HK"],
                "bio_en":       row["Name_EN"],
                "certifications": certifications,
            }
            if photo_path.exists():
                with open(photo_path, "rb") as photo_f:
                    staff, _ = DojoStaff.objects.update_or_create(
                        user=user, dojo=dojo, defaults=staff_defaults
                    )
                    staff.photo.save(photo_path.name, File(photo_f), save=True)
            else:
                DojoStaff.objects.update_or_create(
                    user=user, dojo=dojo, defaults=staff_defaults
                )
                self.stdout.write(
                    f"       WARN: Photo not found: {photo_path} — skipping for {row['ID']}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nReal-data seed complete: {created_count} created, {updated_count} updated."
            )
        )

    # ------------------------------------------------------------------
    # --full: state-coverage dataset across all 14 apps (t0.2.0)
    # ------------------------------------------------------------------
    def _seed_full(self):
        self.stdout.write("Mode: --full")

        users = self._full_get_test_users()
        dojo_a, dojo_b = self._full_seed_dojos()
        self._full_seed_dojo_staff(users, dojo_a, dojo_b)
        members = self._full_seed_members(users, dojo_a, dojo_b)
        events = self._full_seed_events(dojo_a, dojo_b)
        self._full_seed_attendance(events, members)
        activity_apps, activity_events = self._full_seed_activities(
            users, dojo_a, dojo_b, events, members
        )
        skills = self._full_seed_skills(users, members, activity_apps)
        fees = self._full_seed_fees(members)
        payments = self._full_seed_payments(users, fees)
        notifications = self._full_seed_communications(members)
        cms = self._full_seed_cms(users)
        tournaments, entries = self._full_seed_matches(events, members)
        chatbot = self._full_seed_chatbot(users, members)
        leads = self._full_seed_enrollment(dojo_a, dojo_b)

        manifest = {
            "note": (
                "Generated by seed_test_org_data --full. All dates are anchored "
                "constants (never date.today()) so re-runs produce identical output."
            ),
            "dojos": {
                "a": {"pk": dojo_a.pk, "slug": dojo_a.slug, "district": dojo_a.district},
                "b": {"pk": dojo_b.pk, "slug": dojo_b.slug, "district": dojo_b.district},
            },
            "members": {
                username: {
                    "pk": m.pk, "member_id": m.member_id, "status": m.status,
                    "tier": m.tier, "primary_dojo_pk": m.primary_dojo_id,
                }
                for username, m in members.items()
            },
            "events": [
                {"pk": e.pk, "title": e.title, "event_type": e.event_type, "status": e.status}
                for e in events
            ],
            "activity_applications": [
                {"pk": a.pk, "state": a.state, "member_pk": a.member_id}
                for a in activity_apps
            ],
            "skills": [
                {"pk": s.pk, "category": s.category, "result": s.result, "skill_name": s.skill_name}
                for s in skills
            ],
            "fees": [
                {"pk": f.pk, "year": f.year, "status": f.status}
                for f in fees
            ],
            "payments": [
                {"pk": p.pk, "method": p.method, "status": p.status}
                for p in payments
            ],
            "communications": [
                {"pk": n.pk, "channel": n.channel, "status": n.status}
                for n in notifications
            ],
            "cms": cms,
            "matches": {
                "tournaments": [{"pk": t.pk, "name": t.name} for t in tournaments],
                "entries": [
                    {"pk": e.pk, "tournament_pk": e.tournament_id, "result": e.result, "medal": e.medal}
                    for e in entries
                ],
            },
            "chatbot": chatbot,
            "enrollment": [
                {"pk": lead.pk, "full_name": lead.full_name, "child_age": lead.child_age}
                for lead in leads
            ],
        }

        manifest_path = FIXTURES_DIR / "full_dataset_manifest.json"
        FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        self.stdout.write(f"  Written manifest → {manifest_path}")

        self.stdout.write(self.style.SUCCESS("\nFull-coverage seed complete."))

    def _full_get_test_users(self) -> dict:
        usernames = [
            "test_grandmaster", "test_deputy_grandmaster", "test_admin", "test_editor",
            "test_coach_a", "test_coach_b",
            "test_member_a1", "test_member_a2", "test_member_b1",
            "test_member_suspended", "test_member_inactive",
            "test_parent_a",
        ]
        users = {}
        missing = []
        for username in usernames:
            try:
                users[username] = User.objects.get(username=username)
            except User.DoesNotExist:
                missing.append(username)
        if missing:
            raise CommandError(
                f"Missing test users: {missing}. Run seed_test_users first: "
                "python manage.py seed_test_users --settings=config.settings.dev"
            )
        return users

    def _full_seed_dojos(self) -> tuple:
        dojo_a, _ = DojoEntity.objects.get_or_create(
            slug="verification-full-dojo-a",
            defaults={
                "name": "Verification Full Dojo A (Wong Tai Sin)",
                "address": "N/A — seeded for verification suite only",
                "district": DojoEntity.District.WONG_TAI_SIN,
                "is_active": True,
            },
        )
        dojo_b, _ = DojoEntity.objects.get_or_create(
            slug="verification-full-dojo-b",
            defaults={
                "name": "Verification Full Dojo B (Tai Po)",
                "address": "N/A — seeded for verification suite only",
                "district": DojoEntity.District.TAI_PO,
                "is_active": True,
            },
        )
        self.stdout.write(f"  Dojos: {dojo_a.name}, {dojo_b.name}")
        return dojo_a, dojo_b

    def _full_seed_dojo_staff(self, users: dict, dojo_a: DojoEntity, dojo_b: DojoEntity) -> None:
        # Two different dojos — unique_head_coach_per_dojo is scoped per-dojo,
        # so both coaches can legally be HEAD_COACH of their own dojo.
        DojoStaff.objects.update_or_create(
            user=users["test_coach_a"], dojo=dojo_a,
            defaults={
                "role": "HEAD_COACH", "joined_date": SEED_JOIN_DATE,
                "is_active": True, "is_public": False,
            },
        )
        DojoStaff.objects.update_or_create(
            user=users["test_coach_b"], dojo=dojo_b,
            defaults={
                "role": "HEAD_COACH", "joined_date": SEED_JOIN_DATE,
                "is_active": True, "is_public": False,
            },
        )
        self.stdout.write("  DojoStaff: test_coach_a → HEAD_COACH @ A, test_coach_b → HEAD_COACH @ B")

    def _full_seed_members(self, users: dict, dojo_a: DojoEntity, dojo_b: DojoEntity) -> dict:
        # (username, dojo, status)
        specs = [
            ("test_member_a1", dojo_a, MemberStatus.ACTIVE),
            ("test_member_a2", dojo_a, MemberStatus.ACTIVE),
            ("test_member_b1", dojo_b, MemberStatus.ACTIVE),
            ("test_member_suspended", dojo_a, MemberStatus.SUSPENDED),
            ("test_member_inactive", dojo_a, MemberStatus.INACTIVE),
        ]
        members = {}
        for username, dojo, status in specs:
            user = users[username]
            member, _ = MemberProfile.objects.update_or_create(
                user=user,
                defaults={
                    "member_id": f"FULL-{username.removeprefix('test_').upper()}"[:30],
                    "date_of_birth": SEED_DOB,
                    "gender": "OTHER",
                    "emergency_contact_name": "N/G",
                    "emergency_contact_phone": "N/G",
                    "current_belt": BeltLevel.BLACK,
                    "tier": MemberTier.ADULT_BLACK,
                    "status": status,
                    "primary_dojo": dojo,
                    "joined_date": SEED_JOIN_DATE,
                },
            )
            MemberDojoEnrollment.objects.get_or_create(
                member=member, dojo=dojo,
                defaults={"enrolled_date": SEED_JOIN_DATE, "is_active": True},
            )
            members[username] = member
        # test_parent_a deliberately gets NO MemberProfile — MemberGuardian
        # doesn't exist yet; a PARENT test persona shouldn't fake being a
        # member themselves (see Phase 3 correction vs t0.1.0's --minimal).
        self.stdout.write(
            f"  MemberProfile + enrollment seeded for {len(members)} members "
            "(test_parent_a: none, by design)"
        )
        return members

    def _full_seed_events(self, dojo_a: DojoEntity, dojo_b: DojoEntity) -> list:
        # 4 EventType × (past/upcoming) = 8, spread across all 4 EventStatus values.
        specs = [
            (
                "Full Coverage Training (past, A)",
                EventType.TRAINING, EventStatus.PUBLISHED, dojo_a, SEED_EVENT_PAST_1,
            ),
            (
                "Full Coverage Training (upcoming, B, draft)",
                EventType.TRAINING, EventStatus.DRAFT, dojo_b, SEED_EVENT_FUTURE_1,
            ),
            (
                "Full Coverage Exam (past, A)",
                EventType.EXAM, EventStatus.PUBLISHED, dojo_a, SEED_EVENT_PAST_2,
            ),
            (
                "Full Coverage Exam (upcoming, B)",
                EventType.EXAM, EventStatus.PUBLISHED, dojo_b, SEED_EVENT_FUTURE_2,
            ),
            (
                "Full Coverage Tournament (past, A, completed)",
                EventType.TOURNAMENT, EventStatus.COMPLETED, dojo_a, SEED_EVENT_PAST_3,
            ),
            (
                "Full Coverage Tournament (upcoming, B)",
                EventType.TOURNAMENT, EventStatus.PUBLISHED, dojo_b, SEED_EVENT_FUTURE_3,
            ),
            (
                "Full Coverage Other (past, A)",
                EventType.OTHER, EventStatus.PUBLISHED, dojo_a, SEED_EVENT_PAST_4,
            ),
            (
                "Full Coverage Other (upcoming, B, cancelled)",
                EventType.OTHER, EventStatus.CANCELLED, dojo_b, SEED_EVENT_FUTURE_4,
            ),
        ]
        admin_user = User.objects.get(username="test_admin")
        events = []
        for title, event_type, status, dojo, start in specs:
            end = start + timezone.timedelta(hours=2)
            event, _ = Event.objects.update_or_create(
                title=title,
                defaults={
                    "event_type": event_type, "status": status, "dojo": dojo,
                    "start_datetime": start, "end_datetime": end,
                    "created_by": admin_user,
                },
            )
            events.append(event)
        self.stdout.write(f"  Events: {len(events)} rows, all 4 EventType × all 4 EventStatus covered")
        return events

    def _full_seed_attendance(self, events: list, members: dict) -> None:
        # First event ("Full Coverage Training (past, A)") gets 3 attendance
        # rows covering all 3 CheckInMethod values — not "both", there are 3.
        training_event = events[0]
        specs = [
            ("test_member_a1", CheckInMethod.QR_SCAN),
            ("test_member_a2", CheckInMethod.MANUAL),
            ("test_member_suspended", CheckInMethod.COACH_MARKED),
        ]
        for username, method in specs:
            AttendanceLog.objects.update_or_create(
                event=training_event, member=members[username],
                defaults={"check_in_method": method},
            )
        self.stdout.write("  AttendanceLog: 3 rows, all 3 CheckInMethod values covered")

    def _full_seed_activities(
        self, users: dict, dojo_a: DojoEntity, dojo_b: DojoEntity,
        events: list, members: dict,
    ) -> tuple:
        admin_user = users["test_admin"]
        template, _ = ActivityTemplate.objects.update_or_create(
            name="Full Coverage Grading Template",
            defaults={
                "activity_type": ActivityType.BELT_GRADING,
                "form_schema": {},
                "is_active": True,
                "created_by": admin_user,
            },
        )
        # events[2] = "Full Coverage Exam (past, A)", events[3] = "...(upcoming, B)"
        activity_event_a, _ = ActivityEvent.objects.update_or_create(
            template=template, event=events[2], dojo=dojo_a,
            defaults={"scheduled_date": events[2].start_datetime.date()},
        )
        activity_event_b, _ = ActivityEvent.objects.update_or_create(
            template=template, event=events[3], dojo=dojo_b,
            defaults={"scheduled_date": events[3].start_datetime.date()},
        )

        # (activity_event, member_username, target_state) — every (activity_event,
        # member) pair is unique so unique_member_activity_event is respected.
        specs = [
            (activity_event_a, "test_member_a1", "DRAFT"),
            (activity_event_a, "test_member_a2", "AWAITING_COACH_REC"),
            (activity_event_b, "test_member_b1", "AWAITING_GM_APPROVAL"),
            (activity_event_b, "test_member_a1", "PENDING_PAYMENT"),
            (activity_event_b, "test_member_a2", "REJECTED"),
            (activity_event_a, "test_member_suspended", "PROCESSING_PDF"),
            (activity_event_a, "test_member_inactive", "COMPLETED"),
        ]
        applications = []
        for activity_event, username, target_state in specs:
            app, _ = ActivityApplication.objects.get_or_create(
                activity_event=activity_event, member=members[username],
                defaults={"form_data": {}},
            )
            app = _advance_activity_application(app, target_state)
            applications.append(app)

        self.stdout.write(
            f"  Activities: 1 template, 2 ActivityEvents, {len(applications)} "
            "ActivityApplications (one per FSM state, via real transitions)"
        )
        return applications, (activity_event_a, activity_event_b)

    def _full_seed_skills(self, users: dict, members: dict, activity_apps: list) -> list:
        # FK'd to the COMPLETED application (activity_application is PROTECT).
        completed_app = next(a for a in activity_apps if a.state == "COMPLETED")
        coach = users["test_coach_a"]
        categories = list(SkillCategory.values)  # 7 values
        results_cycle = [SkillResult.PASS, SkillResult.FAIL, SkillResult.EXEMPTED]
        skills = []
        for i, category in enumerate(categories):
            record, _ = SkillRecord.objects.update_or_create(
                member=completed_app.member, activity_application=completed_app,
                skill_name=f"{category} Assessment",
                defaults={
                    "category": category,
                    "result": results_cycle[i % len(results_cycle)],
                    "assessed_by": coach,
                    "assessed_at": SEED_JOIN_DATE,
                    "belt_level_at_assessment": BeltLevel.BLACK,
                },
            )
            skills.append(record)
        self.stdout.write(f"  Skills: {len(skills)} rows, all 7 SkillCategory values covered")
        return skills

    def _full_seed_fees(self, members: dict) -> list:
        member = members["test_member_a1"]
        statuses = list(FeeStatus.values)  # 5 values
        fees = []
        for i, status in enumerate(statuses):
            year = 2022 + i
            amount_paid = {
                FeeStatus.UNPAID: 0, FeeStatus.PARTIAL: 400,
                FeeStatus.PAID: 1200, FeeStatus.WAIVED: 0, FeeStatus.OVERDUE: 0,
            }[status]
            fee, _ = AnnualFee.objects.update_or_create(
                member=member, year=year,
                defaults={
                    "tier_at_billing": MemberTier.ADULT_BLACK,
                    "amount_due": 1200,
                    "amount_paid": amount_paid,
                    "status": status,
                    "due_date": date(year, 3, 1),
                },
            )
            fees.append(fee)
            if status == FeeStatus.PAID:
                Invoice.objects.get_or_create(annual_fee=fee)
        self.stdout.write(f"  Fees: {len(fees)} AnnualFee rows, all 5 FeeStatus values covered, 1 Invoice")
        return fees

    def _full_seed_payments(self, users: dict, fees: list) -> list:
        admin_user = users["test_admin"]
        statuses = list(PaymentStatus.values)  # 6 values
        payments = []
        for i, status in enumerate(statuses):
            fee = fees[i % len(fees)]
            method = PaymentMethod.STRIPE if i == 0 else PaymentMethod.FPS_PAYME
            confirmed_by = admin_user if status == PaymentStatus.MANUALLY_CONFIRMED else None
            payment, _ = PaymentRecord.objects.update_or_create(
                annual_fee=fee, method=method, status=status,
                defaults={
                    "amount": 1200, "currency": "HKD",
                    "reference_id": f"FULL-SEED-{i}",
                    "confirmed_by": confirmed_by,
                },
            )
            payments.append(payment)
        self.stdout.write(
            f"  Payments: {len(payments)} rows, all 6 PaymentStatus values covered "
            "(1 STRIPE, rest FPS_PAYME)"
        )
        return payments

    def _full_seed_communications(self, members: dict) -> list:
        member = members["test_member_a1"]
        specs = [
            (NotificationChannel.EMAIL, NotificationStatus.PENDING),
            (NotificationChannel.EMAIL, NotificationStatus.SENT),
            (NotificationChannel.IN_APP, NotificationStatus.DELIVERED),
            (NotificationChannel.WHATSAPP, NotificationStatus.FAILED),
            (NotificationChannel.IN_APP, NotificationStatus.READ),
        ]
        notifications = []
        for i, (channel, status) in enumerate(specs):
            failure_reason = "WhatsApp Phase 1 stub — no provider SDK integrated" \
                if channel == NotificationChannel.WHATSAPP else ""
            notif, _ = Notification.objects.update_or_create(
                recipient=member, channel=channel, subject=f"Full coverage notification {i}",
                defaults={
                    "body": "Seeded for verification suite state coverage.",
                    "status": status,
                    "failure_reason": failure_reason,
                },
            )
            notifications.append(notif)
        self.stdout.write(
            "  Communications: 5 Notification rows, all 5 NotificationStatus values covered; "
            "one channel=WHATSAPP+status=FAILED cross-references test_whatsapp_stub_still_failed"
        )
        return notifications

    def _full_seed_cms(self, users: dict) -> dict:
        editor = users["test_editor"]
        sections = list(PageSection.values)  # 7 values
        status_cycle = [ContentStatus.DRAFT, ContentStatus.PUBLISHED, ContentStatus.ARCHIVED]
        blocks = []
        for i, section in enumerate(sections):
            block, _ = ContentBlock.objects.update_or_create(
                section=section, title=f"Full Coverage {section} Block",
                defaults={
                    "status": status_cycle[i % len(status_cycle)],
                    "order": i,
                    "body": "Seeded for verification suite state coverage.",
                    "created_by": editor,
                },
            )
            blocks.append(block)

        announcement, _ = Announcement.objects.update_or_create(
            title="Full Coverage Announcement",
            defaults={
                "body": "Seeded for verification suite state coverage.",
                "status": ContentStatus.PUBLISHED,
                "is_pinned": True,
                "published_at": SEED_ANNOUNCEMENT_PUBLISHED_AT,
                "expires_at": SEED_ANNOUNCEMENT_EXPIRES_AT,
                "created_by": editor,
            },
        )
        news_post, _ = NewsPost.objects.update_or_create(
            slug="full-coverage-news-post",
            defaults={
                "title": "Full Coverage News Post",
                "status": ContentStatus.PUBLISHED,
                "excerpt": "Seeded for verification suite state coverage.",
                "body": "Seeded for verification suite state coverage.",
                "published_at": SEED_NEWS_PUBLISHED_AT,
                "created_by": editor,
            },
        )
        self.stdout.write(
            f"  CMS: {len(blocks)} ContentBlock rows (all 7 PageSection values), "
            "1 Announcement (with expires_at), 1 NewsPost"
        )
        return {
            "content_blocks": [{"pk": b.pk, "section": b.section, "status": b.status} for b in blocks],
            "announcement": {"pk": announcement.pk, "expires_at": announcement.expires_at.isoformat()},
            "news_post": {"pk": news_post.pk, "slug": news_post.slug},
        }

    def _full_seed_matches(self, events: list, members: dict) -> tuple:
        # events[4] = "Full Coverage Tournament (past, A, completed)"
        # events[5] = "Full Coverage Tournament (upcoming, B)"
        tournament_1, _ = Tournament.objects.update_or_create(
            name="Full Coverage Open 2026 A",
            defaults={"event": events[4], "match_type": MatchType.SPARRING},
        )
        tournament_2, _ = Tournament.objects.update_or_create(
            name="Full Coverage Open 2026 B",
            defaults={"event": events[5], "match_type": MatchType.POOMSAE},
        )

        # unique_member_per_tournament — members may repeat ACROSS tournaments,
        # never within the same one. Split 4+3 (see plan amendment): only 5
        # MemberProfiles exist, so 7 entries covering 6 MatchResult values + 1
        # blank/pending state cannot fit in a single tournament.
        t1_specs = [
            ("test_member_a1", MatchResult.WIN, Medal.GOLD),
            ("test_member_a2", MatchResult.LOSS, Medal.NONE),
            ("test_member_b1", MatchResult.DRAW, Medal.NONE),
            ("test_member_suspended", "", Medal.NONE),  # blank/pending — 7th state, not one of the 6
        ]
        t2_specs = [
            ("test_member_a1", MatchResult.DISQUALIFIED, Medal.NONE),
            ("test_member_a2", MatchResult.WITHDREW, Medal.NONE),
            ("test_member_inactive", MatchResult.BYE, Medal.NONE),
        ]
        entries = []
        for tournament, specs in ((tournament_1, t1_specs), (tournament_2, t2_specs)):
            for username, result, medal in specs:
                entry, _ = MatchEntry.objects.update_or_create(
                    tournament=tournament, member=members[username],
                    defaults={
                        "belt_at_match": BeltLevel.BLACK,
                        "result": result,
                        "medal": medal,
                    },
                )
                entries.append(entry)

        self.stdout.write(
            f"  Matches: 2 Tournaments, {len(entries)} MatchEntry rows split 4+3 — "
            "all 6 MatchResult values + 1 blank/pending state covered"
        )
        return [tournament_1, tournament_2], entries

    def _full_seed_chatbot(self, users: dict, members: dict) -> dict:
        admin_user = users["test_admin"]
        categories = list(FAQCategory.values)  # 6 values
        faqs = []
        for i, category in enumerate(categories):
            faq, _ = FAQEntry.objects.update_or_create(
                category=category, question=f"Full coverage FAQ question {i}",
                defaults={
                    "answer": "Seeded for verification suite state coverage.",
                    "is_active": True, "order": i, "created_by": admin_user,
                },
            )
            faqs.append(faq)

        anon_session, _ = ChatSession.objects.update_or_create(
            session_key="verify-full-anon-session",
            defaults={"member": None},
        )
        member_session, _ = ChatSession.objects.update_or_create(
            session_key="verify-full-member-session",
            defaults={"member": members["test_member_a1"]},
        )
        # ChatMessage.Role uses lowercase values ('user'/'assistant') —
        # inconsistent with every other enum in this app; documented here,
        # not "fixed" (see t0.1.0 exploration notes).
        for session in (anon_session, member_session):
            ChatMessage.objects.get_or_create(
                session=session, role="user",
                defaults={"content": "Full coverage seed question."},
            )
            ChatMessage.objects.get_or_create(
                session=session, role="assistant",
                defaults={"content": "Full coverage seed answer."},
            )

        self.stdout.write(
            f"  Chatbot: {len(faqs)} FAQEntry rows (all 6 FAQCategory values), "
            "2 ChatSession (1 anonymous, 1 linked), 4 ChatMessage rows"
        )
        return {
            "faq_count": len(faqs),
            "sessions": [
                {"pk": anon_session.pk, "member": None},
                {"pk": member_session.pk, "member": "test_member_a1"},
            ],
        }

    def _full_seed_enrollment(self, dojo_a: DojoEntity, dojo_b: DojoEntity) -> list:
        lead_minor, _ = EnrollmentLead.objects.update_or_create(
            full_name="Full Coverage Applicant (Minor)",
            defaults={
                "contact_phone": "+85261234567",
                "contact_email": "full-coverage-minor@example.invalid",
                "interested_dojo": dojo_a,
                "child_age": 10,
                "consent_pdpo": True,
            },
        )
        lead_adult, _ = EnrollmentLead.objects.update_or_create(
            full_name="Full Coverage Applicant (Adult)",
            defaults={
                "contact_phone": "+85267654321",
                "contact_email": "full-coverage-adult@example.invalid",
                "interested_dojo": dojo_b,
                "child_age": None,
                "consent_pdpo": True,
            },
        )
        self.stdout.write("  Enrollment: 2 EnrollmentLead rows (1 minor via child_age, 1 adult)")
        return [lead_minor, lead_adult]


# ---------------------------------------------------------------------------
# FSM transition-chain helper (module-level — no `self` needed)
# ---------------------------------------------------------------------------
def _advance_activity_application(app: ActivityApplication, target_state: str) -> ActivityApplication:
    """
    Idempotently drive an ActivityApplication to target_state via the real
    @transition-decorated methods. state is FSMField(protected=True), which
    blocks direct assignment — every non-DRAFT row must be built by calling
    submit()/recommend()/approve()/reject()/confirm_payment()/complete() in
    sequence.

    Idempotent: if the row is already at target_state (e.g. a previous run
    already seeded it), this is a no-op. A freshly get_or_create'd row is
    always at the model's default state (DRAFT), so re-runs never encounter
    a row stuck mid-chain.
    """
    if app.state == target_state:
        return app

    if target_state == "AWAITING_COACH_REC":
        app.submit()
    elif target_state == "AWAITING_GM_APPROVAL":
        app.submit()
        app.recommend()
    elif target_state == "PENDING_PAYMENT":
        app.submit()
        app.recommend()
        app.approve()
    elif target_state == "REJECTED":
        app.submit()
        app.recommend()
        app.reject()
    elif target_state == "PROCESSING_PDF":
        app.submit()
        app.recommend()
        app.approve()
        app.confirm_payment()
    elif target_state == "COMPLETED":
        app.submit()
        app.recommend()
        app.approve()
        app.confirm_payment()
        app.complete()
    # else target_state == "DRAFT": nothing to do, already default.

    app.save()
    return app
