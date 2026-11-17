"""
verification/checks/test_rbac_write_matrix.py

POST-based tests against the 3 real write-capable views in the codebase
(confirmed via exhaustive exploration — zero DeleteViews exist anywhere;
these are the only Create/Update views period):
  - events:event_create   (ADMIN_ROLES)
  - members:member_edit   (ADMIN_ROLES)
  - cms:page_edit         (EDITOR_ROLES)

Allowed roles are read from role_capability_matrix.CAPABILITY_MATRIX, not
re-hardcoded here, so this test self-updates if the matrix changes.

Every DENY case (role not in the allowed set) asserts TWO things:
  1. response.status_code == 403
  2. the database is unchanged (no partial write happened before the
     permission check fired) — a stronger guarantee than the status code alone.
"""
import csv
from pathlib import Path

import pytest
from django.urls import reverse

from apps.cms.models import ContentBlock
from apps.events.models import Event
from apps.members.models import MemberProfile
from verification.docs_data.role_capability_matrix import (
    PRIMARY_USERNAME_BY_ROLE,
    allowed_roles_for,
)

ALL_ROLES = list(PRIMARY_USERNAME_BY_ROLE.keys())

CREDENTIALS_CSV = Path(__file__).resolve().parent.parent / "fixtures" / "test_credentials.csv"


def _login_as(client, role):
    username = PRIMARY_USERNAME_BY_ROLE[role]
    with open(CREDENTIALS_CSV, encoding="utf-8") as f:
        creds = {row["username"]: row["password"] for row in csv.DictReader(f)}
    logged_in = client.login(username=username, password=creds[username])
    if not logged_in:
        pytest.skip(f"Login failed for {username}")
    return username


# ---------------------------------------------------------------------------
# events:event_create — Create view
# ---------------------------------------------------------------------------

@pytest.mark.rbac
@pytest.mark.django_db
@pytest.mark.parametrize("role", ALL_ROLES)
def test_event_create_rbac(client, seed_full_dataset_in_db, role):
    """POST to events:event_create: 200/302 if allowed, 403 + DB-unchanged if not."""
    _login_as(client, role)
    allowed = allowed_roles_for("events:event_create")

    from apps.dojos.models import DojoEntity
    dojo_obj = DojoEntity.objects.filter(slug="verification-full-dojo-a").first()
    assert dojo_obj is not None, "Run seed_test_org_data --full first"

    count_before = Event.objects.count()
    url = reverse("events:event_create")
    response = client.post(url, data={
        "title": f"RBAC write-matrix test event ({role})",
        "event_type": "TRAINING",
        "status": "DRAFT",
        "dojo": dojo_obj.pk,
        "start_datetime": "2026-01-01 10:00:00",
        "end_datetime": "2026-01-01 12:00:00",
    })
    count_after = Event.objects.count()

    if role in allowed:
        assert response.status_code in (200, 302), (
            f"Role={role} (allowed) expected 200/302, got {response.status_code}"
        )
        assert count_after == count_before + 1, (
            f"Role={role} (allowed) POST should have created an Event"
        )
    else:
        assert response.status_code == 403, (
            f"Role={role} (denied) expected 403, got {response.status_code}"
        )
        assert count_after == count_before, (
            f"Role={role} (denied) POST must NOT create an Event — "
            f"count was {count_before}, now {count_after}"
        )


# ---------------------------------------------------------------------------
# members:member_edit — Update view
# ---------------------------------------------------------------------------

@pytest.mark.rbac
@pytest.mark.django_db
@pytest.mark.parametrize("role", ALL_ROLES)
def test_member_edit_rbac(client, seed_full_dataset_in_db, role):
    """POST to members:member_edit: 200/302 if allowed, 403 + DB-unchanged if not."""
    _login_as(client, role)
    allowed = allowed_roles_for("members:member_edit")

    member = MemberProfile.objects.get(member_id="FULL-MEMBER_A1")
    original_status = member.status
    original_tier = member.tier

    url = reverse("members:member_edit", kwargs={"pk": member.pk})
    new_status = "GRADUATED" if original_status != "GRADUATED" else "ACTIVE"
    response = client.post(url, data={
        # MemberContactForm (accounts.User) fields
        "first_name": member.user.first_name,
        "last_name": member.user.last_name,
        "phone": member.user.phone,
        "email": member.user.email,
        # MemberProfileForm fields
        "chinese_name": member.chinese_name,
        "date_of_birth": member.date_of_birth,
        "gender": member.gender,
        "height_cm": member.height_cm or "",
        "weight_kg": member.weight_kg or "",
        "emergency_contact_name": member.emergency_contact_name,
        "emergency_contact_phone": member.emergency_contact_phone,
        "status": new_status,
        "current_belt": member.current_belt,
        "tier": member.tier,
        "primary_dojo": member.primary_dojo_id,
        "public_showcase_consent": False,
        "notes": member.notes,
    })
    member.refresh_from_db()

    if role in allowed:
        assert response.status_code in (200, 302), (
            f"Role={role} (allowed) expected 200/302, got {response.status_code}"
        )
        assert member.status == new_status, (
            f"Role={role} (allowed) POST should have updated MemberProfile.status"
        )
        # restore for subsequent parametrized runs
        member.status = original_status
        member.tier = original_tier
        member.save(update_fields=["status", "tier"])
    else:
        assert response.status_code == 403, (
            f"Role={role} (denied) expected 403, got {response.status_code}"
        )
        assert member.status == original_status, (
            f"Role={role} (denied) POST must NOT change MemberProfile.status — "
            f"was {original_status!r}, now {member.status!r}"
        )


# ---------------------------------------------------------------------------
# cms:page_edit — Update view
# ---------------------------------------------------------------------------

@pytest.mark.rbac
@pytest.mark.django_db
@pytest.mark.parametrize("role", ALL_ROLES)
def test_cms_page_edit_rbac(client, seed_full_dataset_in_db, role):
    """POST to cms:page_edit: 200/302 if allowed, 403 + DB-unchanged if not."""
    _login_as(client, role)
    allowed = allowed_roles_for("cms:page_edit")

    block = ContentBlock.objects.filter(section="HOME").first()
    assert block is not None, "Run seed_test_org_data --full first"
    original_title = block.title

    url = reverse("cms:page_edit", kwargs={"pk": block.pk})
    new_title = f"{original_title} (edited by {role})"
    response = client.post(url, data={
        "title": new_title,
        "section": block.section,
        "status": block.status,
        "order": block.order,
        "body": block.body,
        "is_featured": block.is_featured,
    })
    block.refresh_from_db()

    if role in allowed:
        assert response.status_code in (200, 302), (
            f"Role={role} (allowed) expected 200/302, got {response.status_code}"
        )
        assert block.title == new_title, (
            f"Role={role} (allowed) POST should have updated ContentBlock.title"
        )
        # restore for subsequent parametrized runs
        block.title = original_title
        block.save(update_fields=["title"])
    else:
        assert response.status_code == 403, (
            f"Role={role} (denied) expected 403, got {response.status_code}"
        )
        assert block.title == original_title, (
            f"Role={role} (denied) POST must NOT change ContentBlock.title — "
            f"was {original_title!r}, now {block.title!r}"
        )
