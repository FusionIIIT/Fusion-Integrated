"""Pure Python domain tests for year-end processing (BR-EL-007, BR-EL-008, EL-UC-020)."""
from decimal import Decimal

from modules.elm.domain.constants import LeaveCategory
from modules.elm.domain.year_end import (
    YearEndAccountInput,
    calculate_year_end_outcome,
)


def test_year_end_cl_rh_scl_lapse():
    """BR-EL-007: CL, RH, and SCL lapse at the end of the year."""
    cl_input = YearEndAccountInput(
        user_id=1,
        user_kind="staff",
        category=LeaveCategory.CL.value,
        balance=Decimal("3.50"),
    )
    outcome_cl = calculate_year_end_outcome(cl_input)
    assert outcome_cl.lapsed_amount == Decimal("3.50")
    assert outcome_cl.carry_forward_amount == Decimal("0.00")
    assert outcome_cl.converted_to_el == Decimal("0.00")

    rh_input = YearEndAccountInput(
        user_id=1,
        user_kind="staff",
        category=LeaveCategory.RH.value,
        balance=Decimal("1.00"),
    )
    outcome_rh = calculate_year_end_outcome(rh_input)
    assert outcome_rh.lapsed_amount == Decimal("1.00")
    assert outcome_rh.carry_forward_amount == Decimal("0.00")


def test_year_end_faculty_vl_conversion_to_el():
    """BR-EL-008: Faculty VL lapses and converts to EL at 2 VL : 1 EL (ratio 0.50)."""
    # 30 days of unavailed VL -> 15.0 days of EL
    vl_input = YearEndAccountInput(
        user_id=10,
        user_kind="faculty",
        category=LeaveCategory.VL.value,
        balance=Decimal("30.00"),
    )
    outcome = calculate_year_end_outcome(vl_input)
    assert outcome.lapsed_amount == Decimal("30.00")
    assert outcome.converted_to_el == Decimal("15.00")
    assert outcome.carry_forward_amount == Decimal("0.00")

    # Odd VL days: e.g. 15 days -> 7.5 days EL
    vl_odd = YearEndAccountInput(
        user_id=10,
        user_kind="faculty",
        category=LeaveCategory.VL.value,
        balance=Decimal("15.00"),
    )
    outcome_odd = calculate_year_end_outcome(vl_odd)
    assert outcome_odd.converted_to_el == Decimal("7.50")


def test_year_end_el_and_col_carry_forward():
    """EL and COL carry forward to subsequent year."""
    el_input = YearEndAccountInput(
        user_id=2,
        user_kind="staff",
        category=LeaveCategory.EL.value,
        balance=Decimal("24.00"),
    )
    outcome_el = calculate_year_end_outcome(el_input)
    assert outcome_el.lapsed_amount == Decimal("0.00")
    assert outcome_el.carry_forward_amount == Decimal("24.00")

    col_input = YearEndAccountInput(
        user_id=2,
        user_kind="staff",
        category=LeaveCategory.COL.value,
        balance=Decimal("12.00"),
    )
    outcome_col = calculate_year_end_outcome(col_input)
    assert outcome_col.lapsed_amount == Decimal("0.00")
    assert outcome_col.carry_forward_amount == Decimal("12.00")
