"""Leave categories in the study baseline (SRS-EL-002)."""
from __future__ import annotations

CL = "CL"
RH = "RH"
SCL = "SCL"
EL = "EL"
COL = "COL"
VL = "VL"

ALL = (CL, RH, SCL, EL, COL, VL)

LABELS = {
    CL: "Casual Leave", RH: "Restricted Holiday", SCL: "Special Casual Leave",
    EL: "Earned Leave", COL: "Commuted Leave", VL: "Vacation Leave",
}

#: BR-EL-016: the Unit Head is final for these.
UNIT_HEAD_FINAL = frozenset({CL, RH})
#: BR-EL-017/018: Unit Head recommends, the configured hierarchy decides.
HIGHER_SANCTION = frozenset({SCL, EL, COL, VL})
#: BR-EL-011: intervening weekends and closed holidays count.
CONTINUOUS = frozenset({EL, COL, VL})
#: BR-EL-025, BR-EL-027: extension and resumption apply only to these.
EXTENDABLE = frozenset({EL, COL, VL})
RESUMABLE = frozenset({EL, COL, VL})
#: BR-EL-002..004: lapse at year end.
LAPSING = frozenset({CL, RH, SCL})
#: BR-EL-005, BR-EL-008, BR-EL-009: carry forward.
CARRY_FORWARD = frozenset({EL, COL})

FIRST_HALF = "first"
SECOND_HALF = "second"
HALVES = (FIRST_HALF, SECOND_HALF)

FACULTY = "faculty"
STAFF = "staff"
EMPLOYEE_KINDS = (FACULTY, STAFF)
