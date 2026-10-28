"""ELM leave categories and their baseline v1.4 rules (ELM Problem Statement §2-4).

Pure Python: no Django import, so the rule table tests in milliseconds and can
be read by a human without a database in front of them.
"""
from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

TWOPLACES = Decimal("0.01")


class LeaveCategory(StrEnum):
    CL = "CL"     # Casual Leave
    RH = "RH"     # Restricted Holiday
    SCL = "SCL"   # Special Casual Leave
    EL = "EL"     # Earned Leave
    COL = "COL"   # Commuted / balance-controlled leave
    VL = "VL"     # Vacation Leave (faculty)


class FinalAuthority(StrEnum):
    """Who ends the request. CL/RH: the applicant's Unit Head. The rest only get
    Recommended / Not Recommended and then travel up the configured hierarchy
    to a Sanctioning Authority (ELM Problem Statement §7)."""

    UNIT_HEAD = "unit_head"
    SANCTIONING_AUTHORITY = "sanctioning_authority"


class YearEndOutcome(StrEnum):
    LAPSE = "lapse"
    CARRY_FORWARD = "carry_forward"
    CONVERT_TO_EL = "convert_to_el"


#: One row per category. This table is the single source of the category rules;
#: the policy rows seeded from it are editable, but these are the baseline.
CATEGORY_RULES: dict[LeaveCategory, dict] = {
    LeaveCategory.CL: {
        "label": "Casual Leave", "annual_entitlement": Decimal("8"),
        "carries_forward": False, "continuous_counting": False,
        "half_day_allowed": True, "final_authority": FinalAuthority.UNIT_HEAD,
        "year_end": YearEndOutcome.LAPSE, "max_per_year": Decimal("8"),
    },
    LeaveCategory.RH: {
        "label": "Restricted Holiday", "annual_entitlement": Decimal("2"),
        "carries_forward": False, "continuous_counting": False,
        "half_day_allowed": False, "final_authority": FinalAuthority.UNIT_HEAD,
        "year_end": YearEndOutcome.LAPSE, "max_per_year": Decimal("2"),
    },
    LeaveCategory.SCL: {
        "label": "Special Casual Leave", "annual_entitlement": Decimal("15"),
        "carries_forward": False, "continuous_counting": False,
        "half_day_allowed": False,
        "final_authority": FinalAuthority.SANCTIONING_AUTHORITY,
        "year_end": YearEndOutcome.LAPSE, "max_per_year": Decimal("15"),
    },
    LeaveCategory.EL: {
        "label": "Earned Leave", "annual_entitlement": Decimal("30"),
        "carries_forward": True, "continuous_counting": True,
        "half_day_allowed": False,
        "final_authority": FinalAuthority.SANCTIONING_AUTHORITY,
        "year_end": YearEndOutcome.CARRY_FORWARD, "max_per_year": None,
    },
    LeaveCategory.COL: {
        "label": "Commuted Leave", "annual_entitlement": Decimal("20"),
        "carries_forward": True, "continuous_counting": True,
        "half_day_allowed": False,
        "final_authority": FinalAuthority.SANCTIONING_AUTHORITY,
        "year_end": YearEndOutcome.CARRY_FORWARD, "max_per_year": None,
    },
    LeaveCategory.VL: {
        "label": "Vacation Leave", "annual_entitlement": Decimal("60"),
        "carries_forward": False, "continuous_counting": True,
        "half_day_allowed": False,
        "final_authority": FinalAuthority.SANCTIONING_AUTHORITY,
        "year_end": YearEndOutcome.CONVERT_TO_EL, "max_per_year": Decimal("60"),
    },
}

#: Continuous counting applies to EL, COL and VL — intervening weekends and
#: closed holidays inside the interval count as leave days. It does NOT apply
#: to CL, SCL or RH (ELM Problem Statement §4).
CONTINUOUS_CATEGORIES = frozenset(
    c for c, r in CATEGORY_RULES.items() if r["continuous_counting"])

#: Only CL supports first-half / second-half (Problem Statement §3).
HALF_DAY_CATEGORIES = frozenset(
    c for c, r in CATEGORY_RULES.items() if r["half_day_allowed"])

#: Faculty hold VL; non-faculty hold EL. Used only for the default account seed.
VL_TO_EL_RATIO = Decimal("2")   # unused VL converts to EL at 2 VL : 1 EL


def entitlement(category: LeaveCategory) -> Decimal:
    return Decimal(CATEGORY_RULES[category]["annual_entitlement"])


def carries_forward(category: LeaveCategory) -> bool:
    return bool(CATEGORY_RULES[category]["carries_forward"])


def final_authority(category: LeaveCategory) -> FinalAuthority:
    return CATEGORY_RULES[category]["final_authority"]


def year_end_outcome(category: LeaveCategory) -> YearEndOutcome:
    return CATEGORY_RULES[category]["year_end"]


def convert_vl_to_el(vl_days: Decimal) -> Decimal:
    """Unused faculty VL converts to EL at 2 VL : 1 EL, fractions included."""
    if vl_days <= 0:
        return Decimal("0")
    return (Decimal(vl_days) / VL_TO_EL_RATIO).quantize(TWOPLACES)


def is_half_day_category(category: LeaveCategory) -> bool:
    return category in HALF_DAY_CATEGORIES
