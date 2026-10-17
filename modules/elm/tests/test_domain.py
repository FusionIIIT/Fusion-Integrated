"""Leave rules in isolation: no database, no Django."""
from datetime import date
from decimal import Decimal

import pytest

from modules.elm.domain import policy
from modules.elm.domain import state_machine as sm
from modules.elm.domain.entities import (
    Balance,
    HalfDay,
    LeaveCategory,
    LeaveSpan,
    LeaveStatus,
)
from modules.elm.domain.errors import (
    IneligibleCategory,
    InsufficientBalance,
    InvalidDateRange,
    InvalidTransition,
    MissingStationDetails,
    OverlappingLeave,
)

C = LeaveCategory
MON, FRI, SUN = date(2026, 10, 12), date(2026, 10, 16), date(2026, 10, 18)
NEXT_MON = date(2026, 10, 19)
ALL = frozenset({sm.P_REVIEW, sm.P_APPROVE, sm.P_WITHDRAW})


def full(category, days=30):
    return Balance(category, Decimal(days), Decimal(0))


# -- BR-EL-002..006, 009: entitlements ----------------------------------------
@pytest.mark.parametrize(("category", "kind", "expected"), [
    (C.CL, "staff", 8), (C.RH, "faculty", 2), (C.SCL, "staff", 15),
    (C.EL, "staff", 30), (C.EL, "faculty", 0), (C.COL, "faculty", 20),
    (C.VL, "faculty", 60), (C.VL, "staff", 0), (C.CL, "student", 0),
])
def test_annual_entitlement(category, kind, expected):
    assert policy.entitlement_for(category, kind) == Decimal(expected)


# -- BR-EL-001: eligibility ---------------------------------------------------
def test_students_cannot_apply():
    with pytest.raises(IneligibleCategory):
        policy.check_eligibility(C.CL, "student")


def test_vacation_leave_is_faculty_only():
    policy.check_eligibility(C.VL, "faculty")
    with pytest.raises(IneligibleCategory):
        policy.check_eligibility(C.VL, "staff")


# -- BR-EL-010/011: counting --------------------------------------------------
def test_casual_leave_skips_the_weekend():
    assert policy.count_days(C.CL, LeaveSpan(FRI, NEXT_MON)) == 2


def test_casual_leave_skips_supplied_holidays():
    assert policy.count_days(C.CL, LeaveSpan(MON, FRI), holidays=[date(2026, 10, 14)]) == 4


@pytest.mark.parametrize("category", [C.EL, C.COL, C.VL])
def test_continuous_categories_count_the_weekend(category):
    assert policy.count_days(category, LeaveSpan(FRI, NEXT_MON)) == 4


def test_half_day_casual_leave_is_half_a_day():
    assert policy.count_days(C.CL, LeaveSpan(MON, MON, HalfDay.FIRST)) == Decimal("0.5")


def test_half_day_must_be_casual_leave_on_one_date():
    with pytest.raises(InvalidDateRange):
        policy.count_days(C.EL, LeaveSpan(MON, MON, HalfDay.FIRST))
    with pytest.raises(InvalidDateRange):
        policy.count_days(C.CL, LeaveSpan(MON, FRI, HalfDay.FIRST))


def test_end_before_start_is_rejected():
    with pytest.raises(InvalidDateRange):
        policy.count_days(C.CL, LeaveSpan(FRI, MON))


def test_weekend_only_casual_leave_is_rejected():
    with pytest.raises(InvalidDateRange):
        policy.count_days(C.CL, LeaveSpan(date(2026, 10, 17), SUN))


# -- BR-EL-012: overlap -------------------------------------------------------
def test_overlapping_leave_is_blocked():
    with pytest.raises(OverlappingLeave):
        policy.check_no_overlap(LeaveSpan(MON, FRI), [LeaveSpan(FRI, NEXT_MON)])


def test_adjacent_leave_does_not_overlap():
    policy.check_no_overlap(LeaveSpan(MON, FRI), [LeaveSpan(NEXT_MON, NEXT_MON)])


def test_two_halves_of_one_day_do_not_overlap():
    policy.check_no_overlap(LeaveSpan(MON, MON, HalfDay.FIRST),
                            [LeaveSpan(MON, MON, HalfDay.SECOND)])


def test_the_same_half_twice_overlaps():
    with pytest.raises(OverlappingLeave):
        policy.check_no_overlap(LeaveSpan(MON, MON, HalfDay.FIRST),
                                [LeaveSpan(MON, MON, HalfDay.FIRST)])


def test_a_half_day_overlaps_a_full_day():
    with pytest.raises(OverlappingLeave):
        policy.check_no_overlap(LeaveSpan(MON, MON, HalfDay.FIRST), [LeaveSpan(MON, MON)])


# -- balance and Station Leave ------------------------------------------------
def test_pending_requests_reserve_balance():
    b = Balance(C.CL, Decimal(8), Decimal(3), reserved=Decimal(4))
    assert b.available == 1
    with pytest.raises(InsufficientBalance):
        policy.check_balance(b, Decimal(2))


def test_station_leave_needs_address_and_contact():
    policy.check_station_details(False, "", "")
    policy.check_station_details(True, "Home, Bhopal", "9876543210")
    with pytest.raises(MissingStationDetails):
        policy.check_station_details(True, "Home, Bhopal", "  ")


def test_validate_new_request_returns_days():
    days = policy.validate_new_request(category=C.EL, kind="staff",
                                       span=LeaveSpan(FRI, NEXT_MON),
                                       balance=full(C.EL), existing=[])
    assert days == 4


def test_request_cannot_cross_a_year():
    with pytest.raises(InvalidDateRange):
        policy.validate_new_request(category=C.EL, kind="staff",
                                    span=LeaveSpan(date(2026, 12, 30), date(2027, 1, 2)),
                                    balance=full(C.EL), existing=[])


# -- BR-EL-016/017/022: lifecycle ---------------------------------------------
def test_unit_head_approves_casual_leave_outright():
    sm.resolve(LeaveStatus.PENDING, LeaveStatus.APPROVED, C.CL,
               permissions=frozenset({sm.P_REVIEW}), is_applicant=False)


def test_unit_head_cannot_finally_approve_earned_leave():
    with pytest.raises(InvalidTransition):
        sm.resolve(LeaveStatus.PENDING, LeaveStatus.APPROVED, C.EL,
                   permissions=ALL, is_applicant=False)


def test_not_recommended_still_reaches_the_sanctioning_authority():
    sm.resolve(LeaveStatus.NOT_RECOMMENDED, LeaveStatus.APPROVED, C.EL,
               permissions=frozenset({sm.P_APPROVE}), is_applicant=False)


def test_sanctioning_needs_the_approve_permission():
    with pytest.raises(InvalidTransition) as exc:
        sm.resolve(LeaveStatus.RECOMMENDED, LeaveStatus.APPROVED, C.EL,
                   permissions=frozenset({sm.P_REVIEW}), is_applicant=False)
    assert exc.value.denied


def test_nobody_decides_their_own_leave():
    with pytest.raises(InvalidTransition) as exc:
        sm.resolve(LeaveStatus.PENDING, LeaveStatus.APPROVED, C.CL,
                   permissions=ALL, is_applicant=True)
    assert exc.value.denied


def test_only_the_applicant_withdraws():
    sm.resolve(LeaveStatus.RECOMMENDED, LeaveStatus.WITHDRAWN, C.EL,
               permissions=ALL, is_applicant=True)
    with pytest.raises(InvalidTransition):
        sm.resolve(LeaveStatus.PENDING, LeaveStatus.WITHDRAWN, C.CL,
                   permissions=ALL, is_applicant=False)


@pytest.mark.parametrize("final", [LeaveStatus.APPROVED, LeaveStatus.REJECTED,
                                   LeaveStatus.WITHDRAWN])
def test_final_states_have_no_way_out(final):
    assert not [t for t in sm.TRANSITIONS if t.frm == final]


def test_allowed_targets_match_the_actor():
    assert sorted(sm.allowed_targets(LeaveStatus.PENDING, C.EL,
                                     permissions=frozenset({sm.P_REVIEW}),
                                     is_applicant=False)) == ["not_recommended", "recommended"]
    assert sm.allowed_targets(LeaveStatus.PENDING, C.EL, permissions=ALL,
                              is_applicant=True) == ["withdrawn"]
