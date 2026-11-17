"""
verification/checks/test_legacy_fixture_consistency.py

Cross-check pre-supplied legacy CSVs against the new Django model data.
All district/venue mismatches are WARN-level (never fail) because the legacy
site's data model is coarser than the new DojoEntity model (9 codes vs 15).

Uses assert_or_warn() for advisory checks.
"""
import csv
from pathlib import Path

import pytest
from django.conf import settings

from apps.dojos.models import DojoEntity
from verification.docs_data.legacy_district_crosswalk import (
    ALL_MAPPINGS,
    APPROXIMATE_MATCHES,
    DIRECT_MATCHES,
    UNMAPPABLE_LEGACY_CODES,
)
from verification.reporting.models import assert_or_warn

# Local-only member roster, timetable, and photos. Absent on a fresh clone
# and gitignored so they are never committed. When the folder is present the
# checks below run unchanged.
LEGACY_DATA_DIR = Path(settings.BASE_DIR) / "verification" / "fixtures" / "legacy_data"
pytestmark = pytest.mark.skipif(
    not LEGACY_DATA_DIR.is_dir(),
    reason=(
        "verification/fixtures/legacy_data/ is absent "
        "(local-only member data; do not commit it)"
    ),
)


# ---------------------------------------------------------------------------
# District crosswalk checks
# ---------------------------------------------------------------------------

@pytest.mark.legacy_fixture
@pytest.mark.django_db
def test_legacy_district_codes_all_have_crosswalk_entry():
    """
    All 9 legacy district codes in dojo_location.csv have an entry in
    legacy_district_crosswalk.py (DIRECT, APPROXIMATE, or UNMAPPABLE).
    Fails hard if a new code appears that has no mapping at all.
    """
    with open(LEGACY_DATA_DIR / "dojo_location.csv", encoding="utf-8-sig") as f:
        locations = list(csv.DictReader(f))

    legacy_codes = {row["Location_Code"] for row in locations}
    mapped_codes = set(ALL_MAPPINGS.keys())
    unmapped = legacy_codes - mapped_codes
    assert not unmapped, (
        f"Legacy district code(s) {unmapped} have no crosswalk entry. "
        "Add them to verification/docs_data/legacy_district_crosswalk.py."
    )


@pytest.mark.legacy_fixture
@pytest.mark.django_db
def test_direct_match_districts_exist_in_model():
    """
    DIRECT_MATCHES codes map to DojoEntity.District values that must actually
    exist in the model. Fails hard if a model refactor removes a mapped district.
    """
    code_districts = set(DojoEntity.District.values)
    for legacy_code, district_value in DIRECT_MATCHES.items():
        assert district_value in code_districts, (
            f"DIRECT_MATCHES['{legacy_code}'] = '{district_value}' is not a valid "
            f"DojoEntity.District value. Update legacy_district_crosswalk.py or "
            f"apps/dojos/models.py."
        )


@pytest.mark.legacy_fixture
@pytest.mark.django_db
def test_approximate_match_districts_exist_in_model():
    """
    APPROXIMATE_MATCHES target districts must exist in DojoEntity.District.
    Warns (not fails) if a target district is missing — approximations may need
    re-evaluation when the district list changes.
    """
    code_districts = set(DojoEntity.District.values)
    for legacy_code, (district_value, reason) in APPROXIMATE_MATCHES.items():
        assert_or_warn(
            district_value in code_districts,
            message=(
                f"APPROXIMATE_MATCHES['{legacy_code}'] maps to '{district_value}' "
                f"which is no longer in DojoEntity.District. Re-evaluate the crosswalk."
            ),
            test_id=f"test_approximate_match_districts_exist_in_model[{legacy_code}]",
            category="legacy_fixture",
        )


@pytest.mark.legacy_fixture
@pytest.mark.django_db
def test_unmappable_legacy_codes_warn():
    """
    UNMAPPABLE_LEGACY_CODES (currently just 'ND' — 北區) have no equivalent
    in DojoEntity.District. This warns so the gap is visible in every report.
    """
    for legacy_code, note in UNMAPPABLE_LEGACY_CODES.items():
        assert_or_warn(
            False,
            message=(
                f"Legacy code '{legacy_code}' is UNMAPPABLE: {note}"
            ),
            test_id=f"test_unmappable_legacy_codes_warn[{legacy_code}]",
            category="legacy_fixture",
        )


# ---------------------------------------------------------------------------
# Fixture row-count sanity
# ---------------------------------------------------------------------------

@pytest.mark.legacy_fixture
def test_legacy_district_csv_has_9_rows():
    """dojo_location.csv must have exactly 9 district rows (the known legacy count)."""
    with open(LEGACY_DATA_DIR / "dojo_location.csv", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 9, (
        f"dojo_location.csv has {len(rows)} rows, expected 9. "
        "If the legacy district list changed, update legacy_district_crosswalk.py."
    )


@pytest.mark.legacy_fixture
def test_legacy_dojo_event_csv_non_empty():
    """dojo_event.csv must have at least 1 session row."""
    with open(LEGACY_DATA_DIR / "dojo_event.csv", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) > 0, "dojo_event.csv is empty — fixture may be corrupt"


@pytest.mark.legacy_fixture
def test_legacy_members_csv_non_empty():
    """memebers.csv must have at least 1 member row."""
    with open(LEGACY_DATA_DIR / "memebers.csv", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) > 0, "memebers.csv is empty — fixture may be corrupt"
    # All rows must have Level in 1-9
    invalid = [r["ID"] for r in rows if not r.get("Level", "").isdigit() or int(r["Level"]) not in range(1, 10)]
    assert not invalid, (
        f"memebers.csv rows with invalid Level (expected 1–9): {invalid[:10]}"
    )


@pytest.mark.legacy_fixture
def test_legacy_dojo_area_csv_has_2_areas():
    """dojo_area.csv must have exactly 2 area rows (KLN, NT)."""
    with open(LEGACY_DATA_DIR / "dojo_area.csv", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    area_codes = {r["Area_Code"] for r in rows}
    assert area_codes == {"KLN", "NT"}, (
        f"dojo_area.csv area codes: {area_codes}, expected {{'KLN', 'NT'}}"
    )
