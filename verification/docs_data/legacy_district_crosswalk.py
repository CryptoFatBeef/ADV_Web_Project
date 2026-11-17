"""
verification/docs_data/legacy_district_crosswalk.py

Mapping from the legacy 9-code district system (dojo_location.csv) to
DojoEntity.District TextChoices (15 choices, source: apps/dojos/models.py).

Three tiers:
  DIRECT_MATCHES     — exact geographic match → test treats as PASS
  APPROXIMATE_MATCHES — adjacent/administrative match → test treats as WARN
  UNMAPPABLE_LEGACY_CODES — no DojoEntity.District equivalent → test treats as WARN

Tests that use this module never FAIL on mismatches; they warn only.
The legacy site's district grouping is coarser than the new model's 15 choices.
"""

# Legacy code → DojoEntity.District value (exact geographic match)
DIRECT_MATCHES: dict[str, str] = {
    "WTSD": "WongTaiSin",   # 黃大仙區
    "TPD":  "TaiPo",        # 大埔區
    "STD":  "ShaTin",       # 沙田區
    "YLD":  "YuenLong",     # 元朗區
    "TMD":  "TuenMun",      # 屯門區
}

# Legacy code → (DojoEntity.District value, reason for approximation)
APPROXIMATE_MATCHES: dict[str, tuple[str, str]] = {
    "KTD":  (
        "LamTin",
        "觀塘區(Kwun Tong) → LamTin; dojo_event.csv events are at Lam Tin South "
        "Sports Centre (within Kwun Tong district). Kwun Tong and Lam Tin are "
        "adjacent but distinct administrative districts.",
    ),
    "SKD":  (
        "TseungKwanO",
        "西貢區(Sai Kung) → TseungKwanO; Tseung Kwan O is administratively "
        "within Sai Kung district.",
    ),
    "KTSD": (
        "KwaiChung",
        "葵青區(Kwai Tsing) → KwaiChung; Kwai Tsing district contains Kwai Chung "
        "and Tsing Yi; KwaiChung is the closest single-name match available in "
        "DojoEntity.District.",
    ),
}

# Legacy codes with NO corresponding DojoEntity.District choice
UNMAPPABLE_LEGACY_CODES: dict[str, str] = {
    "ND": (
        "北區(North District) has no corresponding choice in DojoEntity.District. "
        "dojo_event.csv has sessions here: 保榮路體育館(少年/兒童班) and "
        "粉嶺綜合服務中心. "
        "ACTION REQUIRED if a North District dojo is added: add NorthDistrict or "
        "FanLing to DojoEntity.District and update this mapping."
    ),
}

# Convenience: all 9 legacy codes with their best mapping (None = unmappable)
ALL_MAPPINGS: dict[str, str | None] = {
    **{k: v for k, v in DIRECT_MATCHES.items()},
    **{k: v for k, v in APPROXIMATE_MATCHES.items()},
    **{k: None for k in UNMAPPABLE_LEGACY_CODES},
}
