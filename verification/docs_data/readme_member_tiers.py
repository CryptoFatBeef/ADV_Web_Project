"""
verification/docs_data/readme_member_tiers.py

Ground truth: member tier prices documented in README.md.

NOTE: These prices exist only as Python comments in apps/members/models.py
(e.g. # HK$100), not as queryable model data. There is no FeeSchedule table.
The test that uses this module is WARN-level only (not fail) because we can
only compare comment text, not real data.

apps/fees/models.py has AnnualFee with tier_at_billing (snapshot field, v0.2.0).
To promote the check to fail-level, add a tier→amount mapping constant to
apps/fees/models.py (or a FeeSchedule model) — no separate table needed.
"""

# {tier_code: annual_fee_hkd} as documented in README.md
PRICES: dict[str, int] = {
    "COLOUR_BELT":    100,
    "POOM":           800,
    "STUDENT_BLACK":  800,
    "ADULT_BLACK":   1200,
    "OVERSEAS_BLACK": 1200,
}

# Comment patterns to search for in apps/members/models.py source
# Maps tier code → expected comment substring
COMMENT_PATTERNS: dict[str, str] = {
    "COLOUR_BELT":    "HK$100",
    "POOM":           "HK$800",
    "STUDENT_BLACK":  "HK$800",
    "ADULT_BLACK":    "HK$1,200",
    "OVERSEAS_BLACK": "HK$1,200",
}
