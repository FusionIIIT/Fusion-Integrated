"""Leave categories in the study baseline (SRS-EL-002, BR-EL-001)."""

CL = "CL"
RH = "RH"
SCL = "SCL"
EL = "EL"
COL = "COL"
VL = "VL"

CATEGORIES = (CL, RH, SCL, EL, COL, VL)
HIGHER_SANCTION = frozenset({SCL, EL, COL, VL})  # BR-EL-017, BR-EL-018
UNIT_HEAD_FINAL = frozenset({CL, RH})            # BR-EL-016
CONTINUOUS_COUNT = frozenset({EL, COL, VL})      # BR-EL-011
HALVES = ("first", "second")
EXTENDABLE = frozenset({EL, COL, VL})            # BR-EL-025
RESUMABLE = frozenset({EL, COL, VL})             # BR-EL-027
LAPSE_AT_YEAR_END = frozenset({CL, RH, SCL})     # BR-EL-002..004
CARRY_FORWARD = frozenset({EL, COL})             # BR-EL-005, BR-EL-009
