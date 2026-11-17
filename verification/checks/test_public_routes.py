"""
verification/checks/test_public_routes.py

Verify that public routes (no auth required) return 200 and that basic
content expectations hold — founding year present on about page, etc.

Requires seed_test_org_data --minimal to have been run (provides slug-based
detail view rows for our-dojos/<slug>/ and news/<slug>/).

Advisory checks (org intro text, founding year) use assert_or_warn() — they
are warn-level because About page copy is editorial and may phrase things
differently without being wrong.
"""
import pytest
from django.urls import reverse

from verification.reporting.models import assert_or_warn

from apps.accounts.models import User
from apps.dojos.models import DojoEntity, DojoStaff


@pytest.mark.legacy_fixture
@pytest.mark.django_db
def test_public_homepage_returns_200(client):
    response = client.get(reverse("public:home"))
    assert response.status_code == 200


@pytest.mark.legacy_fixture
@pytest.mark.django_db
def test_public_about_returns_200(client):
    response = client.get(reverse("public:about"))
    assert response.status_code == 200


@pytest.mark.legacy_fixture
@pytest.mark.django_db
def test_public_about_contains_founding_year(client):
    """
    WARN-LEVEL: The About page should mention the founding year 1991
    (sourced from legacy_org_intro.csv field 'founding_year').
    Advisory only — copy is editorial.
    """
    response = client.get(reverse("public:about"))
    assert_or_warn(
        b"1991" in response.content,
        message=(
            "About page (/about/) does not contain '1991'. "
            "The org was founded in 1991 (per legacy_org_intro.csv). "
            "Consider adding the founding year to templates/public/about.html."
        ),
        test_id="test_public_about_contains_founding_year",
        category="legacy_fixture",
    )


@pytest.mark.legacy_fixture
@pytest.mark.django_db
def test_public_instructors_returns_200(client):
    response = client.get(reverse("public:instructors"))
    assert response.status_code == 200


@pytest.mark.legacy_fixture
@pytest.mark.django_db
def test_public_instructors_shows_public_coach(client):
    """
    Content-level check (not just 200): a DojoStaff row marked
    is_public=True/is_active=True/coach_level=<set> must actually render on
    /instructors/, grouped under its HKTKDA tier heading.

    Independent of seed_test_org_data — creates its own fixture data — because
    seed_test_org_data --minimal/--full intentionally set is_public=False for
    synthetic test personas (see DEBUGLOG and test_known_issues_regression.py).
    This is the check that would have caught the page rendering empty in
    production even though the route itself returned 200.
    """
    dojo = DojoEntity.objects.create(
        name="Verification Test Dojo",
        slug="verification-test-dojo",
        address="1 Test Street",
        district=DojoEntity.District.CENTRAL,
    )
    user = User.objects.create_user(
        username="verify_public_coach",
        first_name="Verify",
        last_name="Coach",
        role=User.Role.COACH,
    )
    DojoStaff.objects.create(
        dojo=dojo,
        user=user,
        role=DojoStaff.Role.HEAD_COACH,
        coach_level=DojoStaff.CoachLevel.ELEMENTARY,
        joined_date="2024-01-01",
        is_active=True,
        is_public=True,
    )
    response = client.get(reverse("public:instructors"))
    assert response.status_code == 200
    assert b"Verify Coach" in response.content
    assert "初級教練".encode() in response.content


@pytest.mark.legacy_fixture
@pytest.mark.django_db
def test_public_instructor_detail_returns_200(client):
    """
    Content-level check for the per-coach detail page linked from
    /instructors/ — must render the coach's name and HKTKDA tier.
    """
    dojo = DojoEntity.objects.create(
        name="Verification Test Dojo 2",
        slug="verification-test-dojo-2",
        address="1 Test Street",
        district=DojoEntity.District.CENTRAL,
    )
    user = User.objects.create_user(
        username="verify_public_coach_2",
        first_name="Verify",
        last_name="CoachTwo",
        role=User.Role.COACH,
    )
    staff = DojoStaff.objects.create(
        dojo=dojo,
        user=user,
        role=DojoStaff.Role.HEAD_COACH,
        coach_level=DojoStaff.CoachLevel.SENIOR,
        joined_date="2024-01-01",
        is_active=True,
        is_public=True,
    )
    response = client.get(reverse("public:instructor_detail", args=[staff.slug]))
    assert response.status_code == 200
    assert b"Verify CoachTwo" in response.content
    assert "高級教練".encode() in response.content


@pytest.mark.legacy_fixture
@pytest.mark.django_db
def test_public_dojo_list_returns_200(client):
    response = client.get(reverse("public:dojo_list"))
    assert response.status_code == 200


@pytest.mark.legacy_fixture
@pytest.mark.django_db
def test_public_news_list_returns_200(client):
    response = client.get(reverse("public:news_list"))
    assert response.status_code == 200


@pytest.mark.legacy_fixture
@pytest.mark.django_db
def test_public_showcase_returns_200(client):
    response = client.get(reverse("public:showcase_list"))
    assert response.status_code == 200


@pytest.mark.legacy_fixture
@pytest.mark.django_db
def test_public_enrollment_returns_200(client):
    response = client.get(reverse("enrollment:lead_create"))
    assert response.status_code == 200


@pytest.mark.legacy_fixture
@pytest.mark.django_db
def test_public_robots_txt_returns_200_plain(client):
    response = client.get(reverse("public:robots_txt"))
    assert response.status_code == 200
    assert "text/plain" in response.get("Content-Type", "")


@pytest.mark.legacy_fixture
@pytest.mark.django_db
def test_login_page_returns_200(client):
    response = client.get(reverse("accounts:login"))
    assert response.status_code == 200


@pytest.mark.legacy_fixture
@pytest.mark.django_db
def test_public_dojo_detail_returns_404_without_seed(client):
    """
    /our-dojos/<nonexistent-slug>/ must return 404, not 500.
    The real slug-based test requires seed_test_org_data --minimal.
    """
    response = client.get("/our-dojos/nonexistent-dojo/")
    assert response.status_code == 404
