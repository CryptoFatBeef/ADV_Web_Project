"""
verification/checks/test_public_forms.py

POST-based tests against enrollment:lead_create — the ONLY fully-public
CreateView in the entire codebase (no auth mixin at all, confirmed via
exhaustive exploration). Marked write_path (not rbac) since there's no
role gating involved — anyone, authenticated or not, can submit this form.
"""
import pytest
from django.urls import reverse

from apps.enrollment.models import EnrollmentLead


@pytest.mark.write_path
@pytest.mark.django_db
def test_enrollment_lead_valid_post_creates_row(client, seed_full_dataset_in_db):
    from apps.dojos.models import DojoEntity
    dojo = DojoEntity.objects.filter(slug="verification-full-dojo-a").first()
    assert dojo is not None, "Run seed_test_org_data --full first"

    count_before = EnrollmentLead.objects.count()
    response = client.post(reverse("enrollment:lead_create"), data={
        "full_name": "Public Form Test Applicant",
        "contact_phone": "+85299999999",
        "contact_email": "public-form-test@example.invalid",
        "interested_dojo": dojo.pk,
        "message": "Submitted by test_public_forms.py",
        "consent_pdpo": "on",
    })
    assert response.status_code == 302, (
        f"Valid POST to enrollment:lead_create should redirect (302), got {response.status_code}"
    )
    assert response.url == reverse("enrollment:lead_thanks")
    assert EnrollmentLead.objects.count() == count_before + 1, (
        "Valid POST should have created exactly one EnrollmentLead row"
    )
    lead = EnrollmentLead.objects.get(full_name="Public Form Test Applicant")
    assert lead.consent_pdpo is True


@pytest.mark.write_path
@pytest.mark.django_db
def test_enrollment_lead_missing_consent_rejected(client, seed_full_dataset_in_db):
    """
    EnrollmentLeadForm.clean_consent_pdpo() (apps/enrollment/forms.py) rejects
    a submission with consent_pdpo unchecked. No row should be created.
    """
    count_before = EnrollmentLead.objects.count()
    response = client.post(reverse("enrollment:lead_create"), data={
        "full_name": "Should Not Be Created",
        "contact_phone": "+85288888888",
        "contact_email": "should-not-be-created@example.invalid",
        "message": "Missing consent — should be rejected.",
        # consent_pdpo intentionally omitted
    })
    assert response.status_code == 200, (
        f"Invalid POST (missing consent) should re-render the form (200), got {response.status_code}"
    )
    assert not EnrollmentLead.objects.filter(full_name="Should Not Be Created").exists(), (
        "Missing consent_pdpo must not create an EnrollmentLead row"
    )
    assert EnrollmentLead.objects.count() == count_before


@pytest.mark.write_path
@pytest.mark.django_db
def test_enrollment_lead_with_child_age_creates_row_with_that_value(client, seed_full_dataset_in_db):
    """
    POST with child_age set (minor applicant) creates a row with that value.
    NOTE: this is a plain field-presence assertion — there is no special
    minor-applicant validation/branching logic in the form or model today
    (confirmed: EnrollmentLead has only a plain nullable child_age
    PositiveSmallIntegerField, no age-based conditional requirements).
    """
    response = client.post(reverse("enrollment:lead_create"), data={
        "full_name": "Public Form Test Minor Applicant",
        "contact_phone": "+85277777777",
        "contact_email": "public-form-minor@example.invalid",
        "child_age": 9,
        "message": "Minor applicant test.",
        "consent_pdpo": "on",
    })
    assert response.status_code == 302
    lead = EnrollmentLead.objects.get(full_name="Public Form Test Minor Applicant")
    assert lead.child_age == 9
