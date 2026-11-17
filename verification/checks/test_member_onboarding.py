"""
verification/checks/test_member_onboarding.py

Covers the Member CRM module overhaul:
  - Payments tab visibility (ADMIN_ROLES only, hidden from COACH).
  - The two-form (User + MemberProfile) member edit view persists both.
  - The coach-initiated invitation -> parent self-service onboarding flow:
    dojo-scoping, happy path (creates User x2 + MemberProfile + MemberGuardian),
    and rejection of expired/already-completed invitations.
"""
import csv
from datetime import timedelta
from pathlib import Path

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.dojos.models import DojoEntity
from apps.members.models import InvitationStatus, MemberGuardian, MemberProfile, RegistrationInvitation

CREDENTIALS_CSV = Path(__file__).resolve().parent.parent / "fixtures" / "test_credentials.csv"


def _login_as(client, username):
    with open(CREDENTIALS_CSV, encoding="utf-8") as f:
        creds = {row["username"]: row["password"] for row in csv.DictReader(f)}
    logged_in = client.login(username=username, password=creds[username])
    if not logged_in:
        pytest.skip(f"Login failed for {username}")


# ---------------------------------------------------------------------------
# Payments tab visibility
# ---------------------------------------------------------------------------

@pytest.mark.rbac
@pytest.mark.django_db
def test_payments_tab_visible_for_admin(client, seed_full_dataset_in_db):
    _login_as(client, "test_grandmaster")
    member = MemberProfile.objects.get(member_id="FULL-MEMBER_A1")
    response = client.get(reverse("members:member_detail", kwargs={"pk": member.pk}))
    assert response.status_code == 200
    assert response.context["can_view_payments"] is True
    assert b"payments-pane" in response.content


@pytest.mark.rbac
@pytest.mark.django_db
def test_payments_tab_hidden_for_coach(client, seed_full_dataset_in_db):
    _login_as(client, "test_coach_a")
    member = MemberProfile.objects.get(member_id="FULL-MEMBER_A1")
    response = client.get(reverse("members:member_detail", kwargs={"pk": member.pk}))
    assert response.status_code == 200
    assert "can_view_payments" not in response.context
    assert b"payments-pane" not in response.content


# ---------------------------------------------------------------------------
# Two-form member edit
# ---------------------------------------------------------------------------

@pytest.mark.rbac
@pytest.mark.django_db
def test_member_edit_saves_new_profile_and_contact_fields(client, seed_full_dataset_in_db):
    _login_as(client, "test_grandmaster")
    member = MemberProfile.objects.get(member_id="FULL-MEMBER_A1")
    url = reverse("members:member_edit", kwargs={"pk": member.pk})
    response = client.post(url, data={
        "first_name": "Edited", "last_name": "Name", "phone": "98765432", "email": "edited@example.com",
        "chinese_name": "編輯測試", "date_of_birth": member.date_of_birth, "gender": member.gender,
        "height_cm": "150.5", "weight_kg": "45.0",
        "emergency_contact_name": member.emergency_contact_name,
        "emergency_contact_phone": member.emergency_contact_phone,
        "status": member.status, "current_belt": member.current_belt, "tier": member.tier,
        "primary_dojo": member.primary_dojo_id, "public_showcase_consent": False, "notes": "",
    })
    assert response.status_code == 302
    member.refresh_from_db()
    member.user.refresh_from_db()
    assert member.chinese_name == "編輯測試"
    assert str(member.height_cm) == "150.5"
    assert member.user.first_name == "Edited"
    assert member.user.email == "edited@example.com"


# ---------------------------------------------------------------------------
# Invitation creation: dojo-scoping
# ---------------------------------------------------------------------------

@pytest.mark.rbac
@pytest.mark.django_db
def test_coach_can_invite_for_own_dojo(client, seed_full_dataset_in_db):
    _login_as(client, "test_coach_a")
    dojo_a = DojoEntity.objects.filter(name__icontains="Dojo A").first()
    response = client.post(reverse("members:invitation_create"), data={
        "contact_email": "own_dojo_parent@example.com", "target_dojo": dojo_a.pk,
    })
    assert response.status_code == 200
    assert RegistrationInvitation.objects.filter(contact_email="own_dojo_parent@example.com").exists()


@pytest.mark.rbac
@pytest.mark.django_db
def test_coach_cannot_invite_for_other_dojo(client, seed_full_dataset_in_db):
    _login_as(client, "test_coach_a")
    dojo_b = DojoEntity.objects.filter(name__icontains="Dojo B").first()
    response = client.post(reverse("members:invitation_create"), data={
        "contact_email": "other_dojo_parent@example.com", "target_dojo": dojo_b.pk,
    })
    assert response.status_code == 200
    assert not RegistrationInvitation.objects.filter(contact_email="other_dojo_parent@example.com").exists()


# ---------------------------------------------------------------------------
# Onboarding happy path + rejection cases
# ---------------------------------------------------------------------------

def _make_invitation(status=InvitationStatus.PENDING, expires_delta=timedelta(days=7)):
    dojo = DojoEntity.objects.filter(name__icontains="Dojo A").first()
    creator = User.objects.get(username="test_grandmaster")
    invitation = RegistrationInvitation.objects.create(
        contact_email="onboarding_test_parent@example.com",
        target_dojo=dojo,
        created_by=creator,
        expires_at=timezone.now() + expires_delta,
        status=status,
    )
    return invitation


@pytest.mark.legacy_fixture
@pytest.mark.django_db
def test_onboarding_happy_path_creates_member_and_guardian(client, seed_full_dataset_in_db):
    invitation = _make_invitation()
    url = reverse("members:onboarding", kwargs={"token": invitation.token})

    response = client.get(url)
    assert response.status_code == 200
    assert b'class="sidebar' not in response.content

    response = client.post(url, data={
        "guardian_first_name": "Test", "guardian_last_name": "Guardian",
        "guardian_phone": "91234567", "relationship": "MOTHER",
        "password": "OnboardTest123!", "password_confirm": "OnboardTest123!",
        "member_first_name": "Test", "member_last_name": "Child",
        "member_chinese_name": "測試學員", "date_of_birth": "2015-06-01", "gender": "MALE",
        "height_cm": "140", "weight_kg": "35",
        "emergency_contact_name": "Test Guardian", "emergency_contact_phone": "91234567",
    })
    assert response.status_code == 302

    invitation.refresh_from_db()
    assert invitation.status == InvitationStatus.COMPLETED

    guardian = User.objects.get(email="onboarding_test_parent@example.com")
    assert guardian.role == "PARENT"
    assert client.login(username=guardian.username, password="OnboardTest123!")

    member = MemberProfile.objects.get(chinese_name="測試學員")
    assert member.primary_dojo == invitation.target_dojo
    assert MemberGuardian.objects.filter(member=member, guardian=guardian, relationship="MOTHER").exists()


@pytest.mark.legacy_fixture
@pytest.mark.django_db
def test_onboarding_rejects_expired_invitation(client, seed_full_dataset_in_db):
    invitation = _make_invitation(expires_delta=timedelta(days=-1))
    url = reverse("members:onboarding", kwargs={"token": invitation.token})
    response = client.get(url)
    assert response.status_code == 410
    assert b'class="sidebar' not in response.content


@pytest.mark.legacy_fixture
@pytest.mark.django_db
def test_onboarding_rejects_already_completed_invitation(client, seed_full_dataset_in_db):
    invitation = _make_invitation(status=InvitationStatus.COMPLETED)
    url = reverse("members:onboarding", kwargs={"token": invitation.token})
    response = client.get(url)
    assert response.status_code == 410
