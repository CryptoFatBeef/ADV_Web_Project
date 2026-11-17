"""
verification/reporting/models.py

CheckResult dataclass and assert_or_warn() helper.

warn is not a native pytest outcome. We implement it by recording a warn-level
CheckResult without raising AssertionError, so the pytest test still passes but
the warning is captured in the JSON/CSV report.
"""
from dataclasses import dataclass, field
from typing import Literal

# Session-level registry populated by assert_or_warn()
_warnings: list["CheckResult"] = []


@dataclass
class CheckResult:
    test_id: str
    category: str
    status: Literal["pass", "fail", "warn"]
    message: str


def assert_or_warn(condition: bool, message: str, test_id: str = "", category: str = "") -> None:
    """
    Record a warn-level CheckResult if condition is False, without failing the test.
    Use this for advisory checks where legacy data is known to be coarser than the
    new model (e.g. district crosswalk mismatches, fuzzy venue name matching).
    """
    if not condition:
        _warnings.append(CheckResult(
            test_id=test_id,
            category=category,
            status="warn",
            message=message,
        ))


def get_warnings() -> list[CheckResult]:
    return list(_warnings)


def clear_warnings() -> None:
    _warnings.clear()
