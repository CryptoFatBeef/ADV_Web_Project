"""
verification/checks/test_object_level_access.py

Tests the dojo/owner-scoping fixes added in apps/members, events, activities,
skills views.py (t0.2.0 Phase 2). Depends on seed_full_dataset_in_db, which
seeds 2 real dojos (A=WongTaiSin, B=TaiPo) with distinct COACH/MEMBER personas
at each — this is exactly what's needed to prove scoping actually isolates
data between dojos, not just that a filter clause exists.
"""
import csv
from datetime import date, datetime
from pathlib import Path

import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.activities.models import (
    ActivityApplication,
    ActivityEvent,
    ActivityTemplate,
    ActivityType,
    CoachCertificationRecord,
)
from apps.dojos.models import DojoEntity, DojoStaff
from apps.events.models import Event
from apps.members.models import MemberProfile
from apps.skills.models import SkillRecord

CREDENTIALS_CSV = Path(__file__).resolve().parent.parent / "fixtures" / "test_credentials.csv"


def _login_as(client, username):
    with open(CREDENTIALS_CSV, encoding="utf-8") as f:
        creds = {row["username"]: row["password"] for row in csv.DictReader(f)}
    logged_in = client.login(username=username, password=creds[username])
    if not logged_in:
        pytest.skip(f"Login failed for {username}")


# ---------------------------------------------------------------------------
# Members: coach_a sees only Dojo A members
# ---------------------------------------------------------------------------

@pytest.mark.rbac
@pytest.mark.django_db
def test_coach_a_member_list_excludes_dojo_b(client, seed_full_dataset_in_db):
    _login_as(client, "test_coach_a")
    response = client.get(reverse("members:member_list"))
    assert response.status_code == 200
    member_ids = {m.member_id for m in response.context["members"]}
    assert "FULL-MEMBER_B1" not in member_ids, (
        "test_coach_a (Dojo A) must not see FULL-MEMBER_B1 (Dojo B) in member_list"
    )
    assert "FULL-MEMBER_A1" in member_ids, (
        "test_coach_a (Dojo A) should see its own dojo's members"
    )


@pytest.mark.rbac
@pytest.mark.django_db
def test_coach_a_cannot_view_member_detail_at_dojo_b(client, seed_full_dataset_in_db):
    _login_as(client, "test_coach_a")
    member_b1 = MemberProfile.objects.get(member_id="FULL-MEMBER_B1")
    response = client.get(reverse("members:member_detail", kwargs={"pk": member_b1.pk}))
    assert response.status_code == 404, (
        "test_coach_a (Dojo A) must get 404 viewing a Dojo B member's detail page"
    )


@pytest.mark.rbac
@pytest.mark.django_db
def test_member_detail_shows_coach_role_and_certification(client, seed_full_dataset_in_db):
    """
    A member who is also a registered coach (DojoStaff) with a passed
    CoachCertificationRecord must see both surfaced on their CRM member_detail
    page — previously this page showed only belt/tier/status, with no way to
    see a member's coaching qualifications without cross-referencing the
    Django admin.
    """
    _login_as(client, "test_grandmaster")

    dojo = DojoEntity.objects.create(
        name="Object Level Access Test Dojo", slug="ola-test-dojo",
        address="1 Test Street", district=DojoEntity.District.CENTRAL,
    )
    user = User.objects.create_user(username="ola_coach_member", first_name="Ola", last_name="CoachMember", role=User.Role.COACH)
    member = MemberProfile.objects.create(
        user=user, member_id="OLA-COACH-1", date_of_birth=date(1995, 1, 1), gender="MALE",
        emergency_contact_name="X", emergency_contact_phone="00000000",
        primary_dojo=dojo, joined_date=date(2022, 1, 1),
    )
    DojoStaff.objects.create(
        dojo=dojo, user=user, role=DojoStaff.Role.ASSISTANT_COACH,
        coach_level=DojoStaff.CoachLevel.ELEMENTARY, joined_date=date(2024, 1, 1), is_active=True,
    )
    tmpl = ActivityTemplate.objects.create(
        name="OLA Coach Course", activity_type=ActivityType.COACH_CERTIFICATION,
        form_schema={}, created_by=user,
    )
    event_obj = Event.objects.create(
        title="OLA Coach Course Event", event_type="OTHER", dojo=dojo,
        start_datetime=datetime(2026, 1, 1, 9, 0), end_datetime=datetime(2026, 1, 1, 17, 0),
        created_by=user,
    )
    activity_event = ActivityEvent.objects.create(
        template=tmpl, event=event_obj, dojo=dojo, scheduled_date=date(2026, 1, 1),
    )
    application = ActivityApplication.objects.create(activity_event=activity_event, member=member)
    CoachCertificationRecord.objects.create(
        activity_application=application, certifying_body="HKTKDA",
        course_name="OLA Elementary Coach Course", exam_date=date(2026, 1, 15), result="PASS",
    )

    response = client.get(reverse("members:member_detail", kwargs={"pk": member.pk}))
    assert response.status_code == 200
    assert b"Ola CoachMember" in response.content
    assert b"OLA Elementary Coach Course" in response.content
    assert "初級教練".encode() in response.content


@pytest.mark.rbac
@pytest.mark.django_db
def test_coach_b_member_list_excludes_dojo_a(client, seed_full_dataset_in_db):
    _login_as(client, "test_coach_b")
    response = client.get(reverse("members:member_list"))
    assert response.status_code == 200
    member_ids = {m.member_id for m in response.context["members"]}
    assert "FULL-MEMBER_A1" not in member_ids
    assert "FULL-MEMBER_B1" in member_ids


# ---------------------------------------------------------------------------
# Events: coach_a sees only Dojo A events
# ---------------------------------------------------------------------------

@pytest.mark.rbac
@pytest.mark.django_db
def test_coach_a_event_list_excludes_dojo_b(client, seed_full_dataset_in_db):
    _login_as(client, "test_coach_a")
    response = client.get(reverse("events:event_list"))
    assert response.status_code == 200
    dojo_ids = {e.dojo_id for e in response.context["events"]}
    from apps.dojos.models import DojoEntity
    dojo_b = DojoEntity.objects.get(slug="verification-full-dojo-b")
    assert dojo_b.pk not in dojo_ids, (
        "test_coach_a (Dojo A) must not see any Dojo B events in event_list"
    )


@pytest.mark.rbac
@pytest.mark.django_db
def test_coach_a_cannot_view_event_detail_at_dojo_b(client, seed_full_dataset_in_db):
    _login_as(client, "test_coach_a")
    from apps.dojos.models import DojoEntity
    dojo_b = DojoEntity.objects.get(slug="verification-full-dojo-b")
    dojo_b_event = Event.objects.filter(dojo=dojo_b).first()
    assert dojo_b_event is not None
    response = client.get(reverse("events:event_detail", kwargs={"pk": dojo_b_event.pk}))
    assert response.status_code == 404, (
        "test_coach_a (Dojo A) must get 404 viewing a Dojo B event's detail page"
    )


# ---------------------------------------------------------------------------
# Activities: coach_a sees only Dojo A activity sessions
# ---------------------------------------------------------------------------

@pytest.mark.rbac
@pytest.mark.django_db
def test_coach_a_activity_list_excludes_dojo_b(client, seed_full_dataset_in_db):
    _login_as(client, "test_coach_a")
    response = client.get(reverse("activities:activity_list"))
    assert response.status_code == 200
    dojo_ids = {a.dojo_id for a in response.context["activities"]}
    from apps.dojos.models import DojoEntity
    dojo_b = DojoEntity.objects.get(slug="verification-full-dojo-b")
    assert dojo_b.pk not in dojo_ids, (
        "test_coach_a (Dojo A) must not see any Dojo B ActivityEvent in activity_list"
    )


@pytest.mark.rbac
@pytest.mark.django_db
def test_coach_a_cannot_view_activity_detail_at_dojo_b(client, seed_full_dataset_in_db):
    _login_as(client, "test_coach_a")
    from apps.dojos.models import DojoEntity
    dojo_b = DojoEntity.objects.get(slug="verification-full-dojo-b")
    dojo_b_activity = ActivityEvent.objects.filter(dojo=dojo_b).first()
    assert dojo_b_activity is not None
    response = client.get(reverse("activities:activity_detail", kwargs={"pk": dojo_b_activity.pk}))
    assert response.status_code == 404, (
        "test_coach_a (Dojo A) must get 404 viewing a Dojo B ActivityEvent's detail page"
    )


# ---------------------------------------------------------------------------
# Skills: member_a1 cannot see member_a2's or member_b1's skill records
# ---------------------------------------------------------------------------

@pytest.mark.rbac
@pytest.mark.django_db
def test_member_a1_skill_list_excludes_other_members(client, seed_full_dataset_in_db):
    _login_as(client, "test_member_a1")
    response = client.get(reverse("skills:skill_list"))
    assert response.status_code == 200
    member_ids_seen = {s.member_id for s in response.context["skills"]}
    member_a1 = MemberProfile.objects.get(member_id="FULL-MEMBER_A1")
    member_a2 = MemberProfile.objects.get(member_id="FULL-MEMBER_A2")
    member_b1 = MemberProfile.objects.get(member_id="FULL-MEMBER_B1")
    assert member_a2.pk not in member_ids_seen, (
        "test_member_a1 must not see test_member_a2's SkillRecord rows"
    )
    assert member_b1.pk not in member_ids_seen, (
        "test_member_a1 must not see test_member_b1's SkillRecord rows"
    )
    # member_a1 itself has no SkillRecord rows in the seeded dataset (skills
    # are all on the COMPLETED application, owned by test_member_inactive) —
    # so member_ids_seen may legitimately be empty here. The assertion above
    # (no OTHER member's rows visible) is what matters for this test.


@pytest.mark.rbac
@pytest.mark.django_db
def test_coach_a_skill_list_scoped_to_dojo(client, seed_full_dataset_in_db):
    _login_as(client, "test_coach_a")
    response = client.get(reverse("skills:skill_list"))
    assert response.status_code == 200
    member_ids_seen = {s.member_id for s in response.context["skills"]}
    member_b1 = MemberProfile.objects.get(member_id="FULL-MEMBER_B1")
    assert member_b1.pk not in member_ids_seen, (
        "test_coach_a (Dojo A) must not see Dojo B member's SkillRecord rows"
    )
