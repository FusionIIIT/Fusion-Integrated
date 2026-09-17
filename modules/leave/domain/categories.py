"""The leave categories and the properties that distinguish them."""
from __future__ import annotations

from enum import StrEnum


class Category(StrEnum):
    CL = "CL"
    RH = "RH"
    SCL = "SCL"
    EL = "EL"
    COL = "COL"
    VL = "VL"


#: BR-EL-011. Weekends and closed holidays inside the interval are chargeable.
CONTINUOUS_COUNTING = frozenset({Category.EL, Category.COL, Category.VL})

#: BR-EL-010. Only CL may be taken as a half day.
HALF_DAY_ALLOWED = frozenset({Category.CL})

#: BR-EL-025, BR-EL-027, BR-EL-028. Extension and resumption apply to these.
RESUMABLE = frozenset({Category.EL, Category.COL, Category.VL})

#: BR-EL-016. Unit Head is the final authority; no higher sanction is sought.
UNIT_HEAD_FINAL = frozenset({Category.CL, Category.RH})

#: BR-EL-003. The date must match a published restricted holiday.
CALENDAR_BOUND = frozenset({Category.RH})

#: BR-EL-006, BR-EL-022. Availing is confined to a published vacation period.
VACATION_BOUND = frozenset({Category.VL})


def counts_intervening_days(category: Category) -> bool:
    return category in CONTINUOUS_COUNTING


def allows_half_day(category: Category) -> bool:
    return category in HALF_DAY_ALLOWED


def needs_higher_sanction(category: Category) -> bool:
    return category not in UNIT_HEAD_FINAL
