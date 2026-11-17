"""
verification/checks/test_activity_fsm_transitions.py

Bonus: reuses the FSM transition-chain logic that seed_test_org_data --full
already needs (verification/apps/accounts/management/commands/seed_test_org_data.py
_advance_activity_application()). Verifies:
  - A full valid chain DRAFT→...→COMPLETED succeeds and sets completed_at.
  - DRAFT→...→REJECTED succeeds and is terminal (further transitions raise).
  - Skipping steps (calling .approve() directly on a fresh DRAFT row) raises.
  - Direct attribute assignment to `state` is blocked (FSMField(protected=True)).

Marked fsm rather than rbac — this is business-logic correctness, not
permission checking.
"""
import pytest
from django_fsm import TransitionNotAllowed

from apps.activities.models import ActivityApplication, ActivityEvent, ActivityTemplate, ActivityType
from apps.dojos.models import DojoEntity
from apps.events.models import Event, EventStatus, EventType
from apps.members.models import MemberProfile


@pytest.fixture
def fresh_application(db):
    """A brand-new ActivityApplication at the default DRAFT state, isolated
    from the shared seed_full_dataset_in_db fixture so transition tests don't
    interfere with the seeded state-coverage rows."""
    from apps.accounts.models import User

    admin_user, _ = User.objects.get_or_create(
        username="test_fsm_admin",
        defaults={"role": "ADMIN", "is_active": True},
    )
    dojo, _ = DojoEntity.objects.get_or_create(
        slug="fsm-test-dojo",
        defaults={
            "name": "FSM Test Dojo", "address": "N/A",
            "district": DojoEntity.District.TAI_PO, "is_active": True,
        },
    )
    member_user, _ = User.objects.get_or_create(
        username="test_fsm_member",
        defaults={"role": "MEMBER", "is_active": True},
    )
    member, _ = MemberProfile.objects.get_or_create(
        user=member_user,
        defaults={
            "member_id": "FSM-TEST-MEMBER",
            "date_of_birth": "1995-01-01",
            "gender": "OTHER",
            "emergency_contact_name": "N/G",
            "emergency_contact_phone": "N/G",
            "primary_dojo": dojo,
            "joined_date": "2024-01-01",
        },
    )
    event, _ = Event.objects.get_or_create(
        title="FSM Test Underlying Event",
        defaults={
            "event_type": EventType.EXAM, "status": EventStatus.PUBLISHED,
            "dojo": dojo, "start_datetime": "2026-01-01T10:00:00Z",
            "end_datetime": "2026-01-01T12:00:00Z", "created_by": admin_user,
        },
    )
    template, _ = ActivityTemplate.objects.get_or_create(
        name="FSM Test Template",
        defaults={"activity_type": ActivityType.BELT_GRADING, "form_schema": {}, "created_by": admin_user},
    )
    activity_event, _ = ActivityEvent.objects.get_or_create(
        template=template, event=event, dojo=dojo,
        defaults={"scheduled_date": "2026-01-01"},
    )
    app = ActivityApplication.objects.create(
        activity_event=activity_event, member=member, form_data={},
    )
    assert app.state == "DRAFT"
    return app


@pytest.mark.fsm
def test_full_valid_chain_reaches_completed(fresh_application):
    app = fresh_application
    app.submit()
    app.recommend()
    app.approve()
    app.confirm_payment()
    app.complete()
    app.save()

    assert app.state == "COMPLETED"
    assert app.completed_at is not None
    assert app.submitted_at is not None


@pytest.mark.fsm
def test_reject_branch_is_terminal(fresh_application):
    app = fresh_application
    app.submit()
    app.recommend()
    app.reject()
    app.save()

    assert app.state == "REJECTED"
    with pytest.raises(TransitionNotAllowed):
        app.approve()
    with pytest.raises(TransitionNotAllowed):
        app.confirm_payment()


@pytest.mark.fsm
def test_completed_is_terminal(fresh_application):
    app = fresh_application
    app.submit()
    app.recommend()
    app.approve()
    app.confirm_payment()
    app.complete()
    app.save()

    assert app.state == "COMPLETED"
    with pytest.raises(TransitionNotAllowed):
        app.submit()


@pytest.mark.fsm
def test_skipping_steps_raises_transition_not_allowed(fresh_application):
    """Calling .approve() directly on a fresh DRAFT row (skipping submit()/
    recommend()) must raise — the transition's source doesn't match DRAFT."""
    app = fresh_application
    assert app.state == "DRAFT"
    with pytest.raises(TransitionNotAllowed):
        app.approve()
    with pytest.raises(TransitionNotAllowed):
        app.confirm_payment()
    with pytest.raises(TransitionNotAllowed):
        app.complete()


@pytest.mark.fsm
def test_direct_state_assignment_is_blocked(fresh_application):
    """
    state = FSMField(default='DRAFT', protected=True) blocks direct attribute
    assignment outside of @transition-decorated methods. Confirm the exact
    exception empirically rather than assuming AttributeError.
    """
    app = fresh_application
    with pytest.raises(AttributeError):
        app.state = "COMPLETED"
