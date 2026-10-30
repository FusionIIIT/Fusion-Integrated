from datetime import date
from decimal import Decimal
import pytest

from modules.elm.domain.constants import CL, EL, RH, SCL, VL
from modules.elm.domain.counting import calculate_leave_days
from modules.elm.domain.eligibility import check_overlap, validate_eligibility_and_balance
from modules.elm.domain.state_machine import (
    initial_status,
    transition_substitute_response,
    transition_unit_head_decision,
    transition_withdraw,
)
from modules.elm.domain.year_end import compute_year_end_outcomes


def test_leave_day_counting_continuous():
    # EL counts weekends continuously
    # Mon 2026-10-05 to Sun 2026-10-11 = 7 days
    start = date(2026, 10, 5)
    end = date(2026, 10, 11)
    days = calculate_leave_days(EL, start, end)
    assert days == Decimal("7.0")


def test_leave_day_counting_discrete():
    # CL excludes weekends (Sat, Sun)
    # Mon 2026-10-05 to Sun 2026-10-11 = 5 working days
    start = date(2026, 10, 5)
    end = date(2026, 10, 11)
    days = calculate_leave_days(CL, start, end)
    assert days == Decimal("5.0")


def test_half_day_cl():
    d = date(2026, 10, 6)
    days = calculate_leave_days(CL, d, d, half_day_type="first_half")
    assert days == Decimal("0.5")


def test_overlap_allowed_different_half_day():
    d = date(2026, 10, 6)
    existing = [{"start_date": d, "end_date": d, "leave_category": CL, "half_day_type": "first_half"}]
    # Second half on same day should not overlap
    is_overlapping = check_overlap(d, d, CL, "second_half", existing)
    assert not is_overlapping


def test_state_machine_flow():
    assert initial_status(has_substitute=True) == "pending_substitute"
    assert transition_substitute_response("pending_substitute", "accepted") == "pending_unit_head"
    # CL Unit Head is final
    assert transition_unit_head_decision("pending_unit_head", CL, "approved") == "approved"
    # EL Unit Head recommended moves to higher sanction
    assert transition_unit_head_decision("pending_unit_head", EL, "recommended") == "pending_higher_sanction"


def test_year_end_processing_faculty():
    balances = {
        CL: Decimal("3.0"),
        RH: Decimal("1.0"),
        SCL: Decimal("5.0"),
        VL: Decimal("20.0"),
        EL: Decimal("10.0"),
        "COL": Decimal("15.0"),
    }
    outcomes = {o.category: o for o in compute_year_end_outcomes(balances, is_faculty=True)}

    # CL lapses
    assert outcomes[CL].lapsed == Decimal("3.0")
    # VL converts 20 -> 10 EL
    assert outcomes[VL].converted_to_el == Decimal("10.0")
    # EL gets carried forward 10 + 10 = 20
    assert outcomes[EL].carried_forward == Decimal("20.0")
