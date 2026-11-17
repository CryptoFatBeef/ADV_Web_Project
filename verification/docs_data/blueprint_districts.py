"""
verification/docs_data/blueprint_districts.py

District values for DojoEntity.District (apps/dojos/models.py).

SOURCE: apps/dojos/models.py — DojoEntity.District TextChoices.
This is NOT derived from README.md, DEBUGLOG.md, or the Blueprint PDF,
because none of those documents enumerate the individual district values.

When districts are added/removed in models.py:
  1. Update this list.
  2. Update README.md to document the new district.
The test that reads this file catches the code side; the README update is manual.
"""

DISTRICTS = [
    "KwaiChung",
    "TuenMun",
    "TaiPo",
    "MaOnShan",
    "LamTin",
    "KowloonTong",
    "ShamShuiPo",
    "WongTaiSin",
    "TsuenWan",
    "YuenLong",
    "ShaTin",
    "TseungKwanO",
    "Central",
    "WanChai",
    "CausewayBay",
]
