from datetime import date, datetime, timedelta
import pytest
from modules.elm.domain.counting import calculate_leave_days, is_weekend, is_holiday, HOLIDAYS
from modules.elm.domain.state_machine import (
    LeaveStatus,
    Transition,
    TRANSITIONS,
    get_valid_transitions,
    is_unit_head,
    is_substitute,
)


# ===========================================================================
# 1. CALENDAR & WEEKEND PREDICATE TESTS (BR-EL-011)
# ===========================================================================

@pytest.mark.parametrize("test_date,expected", [
    (date(2023, 10, 9), False),   # Monday
    (date(2023, 10, 10), False),  # Tuesday
    (date(2023, 10, 11), False),  # Wednesday
    (date(2023, 10, 12), False),  # Thursday
    (date(2023, 10, 13), False),  # Friday
    (date(2023, 10, 14), True),   # Saturday
    (date(2023, 10, 15), True),   # Sunday
    (date(2023, 1, 1), True),     # Sunday
    (date(2023, 12, 30), True),   # Saturday
    (date(2023, 12, 31), True),   # Sunday
])
def test_is_weekend_exhaustive(test_date, expected):
    """Verify weekend detection accurately classifies all days of week."""
    assert is_weekend(test_date) is expected


# ===========================================================================
# 2. CLOSED HOLIDAY RECOGNITION (BR-EL-031)
# ===========================================================================

@pytest.mark.parametrize("holiday_str", [
    "2023-01-01",  # New Year
    "2023-01-26",  # Republic Day
    "2023-03-17",  # Holi
    "2023-08-15",  # Independence Day
    "2023-10-02",  # Gandhi Jayanti
    "2023-10-16",  # Mid-semester break / Dussehra
    "2023-12-25",  # Christmas
])
def test_published_holidays_recognized(holiday_str):
    """Verify published calendar holidays are recognized by predicate."""
    dt = date.fromisoformat(holiday_str)
    assert is_holiday(dt) is True


@pytest.mark.parametrize("workday_str", [
    "2023-01-02",
    "2023-01-27",
    "2023-03-18",
    "2023-08-16",
    "2023-10-03",
    "2023-10-17",
    "2023-12-26",
])
def test_normal_workdays_not_flagged_as_holiday(workday_str):
    """Verify ordinary workdays are not falsely identified as holidays."""
    dt = date.fromisoformat(workday_str)
    assert is_holiday(dt) is False


# ===========================================================================
# 3. CASUAL LEAVE (CL) & HALF-DAY CALCULATION (BR-EL-002, BR-EL-010, BR-EL-011)
# ===========================================================================

def test_cl_single_workday():
    """1 ordinary working day of CL consumes 1.0 day."""
    assert calculate_leave_days("2023-10-10", "2023-10-10", "CL") == 1.0


def test_cl_single_day_holiday_yields_zero():
    """CL requested on an official closed holiday consumes 0 days."""
    assert calculate_leave_days("2023-08-15", "2023-08-15", "CL") == 0.0


def test_cl_single_day_saturday_yields_zero():
    """CL requested on a Saturday consumes 0 days."""
    assert calculate_leave_days("2023-10-14", "2023-10-14", "CL") == 0.0


def test_cl_single_day_sunday_yields_zero():
    """CL requested on a Sunday consumes 0 days."""
    assert calculate_leave_days("2023-10-15", "2023-10-15", "CL") == 0.0


def test_cl_full_working_week():
    """CL taken Monday to Friday without holidays consumes 5.0 days."""
    # 2023-10-09 (Mon) to 2023-10-13 (Fri)
    assert calculate_leave_days("2023-10-09", "2023-10-13", "CL") == 5.0


def test_cl_across_two_full_weeks():
    """CL across 14 calendar days (10 workdays) excludes both weekends."""
    # 2023-10-09 (Mon) to 2023-10-20 (Fri) -> 12 calendar days, 2 weekend days (14, 15) and 1 holiday (16)
    # Total = 10 workdays minus 1 holiday = 9 days
    assert calculate_leave_days("2023-10-09", "2023-10-20", "CL") == 9.0


def test_cl_half_day_flag_returns_half_day_constant():
    """BR-EL-010: Half day CL returns exactly 0.5."""
    assert calculate_leave_days("2023-10-11", "2023-10-11", "CL", is_half_day=True) == 0.5


def test_cl_half_day_flag_on_another_date():
    """BR-EL-010: Half day on any date returns 0.5."""
    assert calculate_leave_days("2023-04-18", "2023-04-18", "CL", is_half_day=True) == 0.5


# ===========================================================================
# 4. EARNED LEAVE (EL) CONTINUOUS COUNTING (BR-EL-005, BR-EL-011)
# ===========================================================================

def test_el_single_workday():
    """EL on 1 single day is 1.0 day."""
    assert calculate_leave_days("2023-10-11", "2023-10-11", "EL") == 1.0


def test_el_single_weekend_day():
    """Continuous counting: EL requested on Saturday is 1.0 day."""
    assert calculate_leave_days("2023-10-14", "2023-10-14", "EL") == 1.0


def test_el_single_holiday():
    """Continuous counting: EL requested on a holiday is 1.0 day."""
    assert calculate_leave_days("2023-08-15", "2023-08-15", "EL") == 1.0


def test_el_one_full_week_mon_to_sun():
    """EL Monday to Sunday is 7 full continuous days."""
    assert calculate_leave_days("2023-10-09", "2023-10-15", "EL") == 7.0


def test_el_ten_calendar_days():
    """EL spanning 10 calendar days gives 10.0 continuous days."""
    assert calculate_leave_days("2023-10-01", "2023-10-10", "EL") == 10.0


def test_el_thirty_calendar_days():
    """EL over a full 30-day month gives 30.0 days."""
    assert calculate_leave_days("2023-04-01", "2023-04-30", "EL") == 30.0


# ===========================================================================
# 5. COMMUTED LEAVE (COL) CONTINUOUS COUNTING (BR-EL-009, BR-EL-011)
# ===========================================================================

def test_col_single_day():
    """COL for 1 day returns 1.0 day."""
    assert calculate_leave_days("2023-05-10", "2023-05-10", "COL") == 1.0


def test_col_weekend_only_span():
    """COL spanning Saturday to Sunday is 2 continuous days."""
    assert calculate_leave_days("2023-10-14", "2023-10-15", "COL") == 2.0


def test_col_two_week_medical_recovery():
    """COL over 14 calendar days computes to 14.0 days."""
    assert calculate_leave_days("2023-10-02", "2023-10-15", "COL") == 14.0


def test_col_three_day_medical_over_weekend():
    """COL Friday to Sunday computes to 3.0 days."""
    assert calculate_leave_days("2023-10-13", "2023-10-15", "COL") == 3.0


# ===========================================================================
# 6. VACATION LEAVE (VL) CONTINUOUS COUNTING (BR-EL-006, BR-EL-011)
# ===========================================================================

def test_vl_single_day():
    """VL single day computes to 1.0 day."""
    assert calculate_leave_days("2023-06-15", "2023-06-15", "VL") == 1.0


def test_vl_entire_june_vacation_fortnight():
    """VL spanning 15 calendar days calculates as 15.0 continuous days."""
    assert calculate_leave_days("2023-06-01", "2023-06-15", "VL") == 15.0


def test_vl_weekend_inclusion():
    """VL across a weekend calculates all 3 days."""
    assert calculate_leave_days("2023-06-16", "2023-06-18", "VL") == 3.0


def test_vl_across_closed_holiday():
    """VL across 2023-06-19 holiday counts it continuously."""
    assert calculate_leave_days("2023-06-18", "2023-06-20", "VL") == 3.0


# ===========================================================================
# 7. SPECIAL CASUAL LEAVE (SCL) EXCLUSION RULES (BR-EL-004, BR-EL-011)
# ===========================================================================

def test_scl_single_workday():
    """SCL on a single working day is 1.0 day."""
    assert calculate_leave_days("2023-02-15", "2023-02-15", "SCL") == 1.0


def test_scl_on_weekend_gives_zero():
    """SCL on Sunday gives 0.0 days."""
    assert calculate_leave_days("2023-02-19", "2023-02-19", "SCL") == 0.0


def test_scl_on_holiday_gives_zero():
    """SCL on Republic Day holiday gives 0.0 days."""
    assert calculate_leave_days("2023-01-26", "2023-01-26", "SCL") == 0.0


def test_scl_four_day_midweek():
    """SCL Tuesday to Friday without holiday gives 4.0 days."""
    assert calculate_leave_days("2023-02-07", "2023-02-10", "SCL") == 4.0


def test_scl_week_with_intervening_holiday():
    """SCL over week with 1 holiday gives 4.0 working days."""
    # 2023-05-01 is a holiday (Labour Day). 2023-05-01 (Mon) to 2023-05-05 (Fri) = 4 days
    assert calculate_leave_days("2023-05-01", "2023-05-05", "SCL") == 4.0


# ===========================================================================
# 8. RESTRICTED HOLIDAY (RH) COUNTING (BR-EL-003, BR-EL-011)
# ===========================================================================

def test_rh_single_working_day():
    """RH requested on a working day consumes 1.0 day."""
    assert calculate_leave_days("2023-09-07", "2023-09-07", "RH") == 1.0


def test_rh_on_weekend_gives_zero():
    """RH on Saturday is 0 days."""
    assert calculate_leave_days("2023-09-09", "2023-09-09", "RH") == 0.0


def test_rh_on_closed_holiday_gives_zero():
    """RH on a closed holiday is 0 days."""
    assert calculate_leave_days("2023-10-02", "2023-10-02", "RH") == 0.0


# ===========================================================================
# 9. INPUT PARSING & RESILIENCE TESTS
# ===========================================================================

def test_calculate_leave_days_iso_strings():
    """calculate_leave_days parses ISO formatted date strings."""
    assert calculate_leave_days("2023-11-06", "2023-11-08", "CL") == 3.0


def test_calculate_leave_days_datetime_objects():
    """calculate_leave_days supports datetime.datetime instances."""
    d1 = datetime(2023, 11, 6, 9, 30)
    d2 = datetime(2023, 11, 8, 17, 30)
    assert calculate_leave_days(d1, d2, "CL") == 3.0


def test_calculate_leave_days_date_objects():
    """calculate_leave_days supports datetime.date instances."""
    d1 = date(2023, 11, 6)
    d2 = date(2023, 11, 8)
    assert calculate_leave_days(d1, d2, "CL") == 3.0


def test_calculate_leave_days_inverted_dates_gives_zero():
    """Inverted dates (start > end) returns 0 days."""
    assert calculate_leave_days("2023-11-10", "2023-11-08", "CL") == 0.0


# ===========================================================================
# 10. STATE MACHINE TRANSITION INTEGRITY (BW-EL-01..17, BR-EL-015..020)
# ===========================================================================

def test_state_machine_draft_transitions_with_create_perm():
    """Applicant with create permission can transition DRAFT to AWAITING_SUBSTITUTE."""
    perms = {"leave_management.request.create"}
    transitions = get_valid_transitions(LeaveStatus.DRAFT, perms)
    targets = {t.to_status for t in transitions}
    assert LeaveStatus.AWAITING_SUBSTITUTE in targets


def test_state_machine_draft_allows_rejection_with_create_perm():
    """DRAFT status includes REJECTED transition path."""
    perms = {"leave_management.request.create"}
    transitions = get_valid_transitions(LeaveStatus.DRAFT, perms)
    targets = {t.to_status for t in transitions}
    assert LeaveStatus.REJECTED in targets


def test_state_machine_draft_blocked_without_permission():
    """DRAFT status transitions require leave_management.request.create."""
    perms = {"leave_management.request.view_self"}
    transitions = get_valid_transitions(LeaveStatus.DRAFT, perms)
    assert len(transitions) == 0


def test_state_machine_substitute_consent_gate_valid():
    """AWAITING_SUBSTITUTE transitions to AWAITING_UNIT_HEAD with substitute role."""
    perms = {"leave_management.substitute.assign"}
    transitions = get_valid_transitions(LeaveStatus.AWAITING_SUBSTITUTE, perms)
    assert len(transitions) == 1
    assert transitions[0].to_status == LeaveStatus.AWAITING_UNIT_HEAD


def test_state_machine_substitute_gate_blocked_without_substitute_perm():
    """AWAITING_SUBSTITUTE cannot transition without substitute.assign."""
    perms = {"leave_management.request.create", "leave_management.unit_head.review"}
    transitions = get_valid_transitions(LeaveStatus.AWAITING_SUBSTITUTE, perms)
    assert len(transitions) == 0


def test_state_machine_unit_head_approval_available():
    """Unit Head review permission allows transition to APPROVED."""
    perms = {"leave_management.unit_head.review"}
    transitions = get_valid_transitions(LeaveStatus.AWAITING_UNIT_HEAD, perms)
    targets = {t.to_status for t in transitions}
    assert LeaveStatus.APPROVED in targets


def test_state_machine_unit_head_rejection_available():
    """Unit Head review permission allows transition to REJECTED."""
    perms = {"leave_management.unit_head.review"}
    transitions = get_valid_transitions(LeaveStatus.AWAITING_UNIT_HEAD, perms)
    targets = {t.to_status for t in transitions}
    assert LeaveStatus.REJECTED in targets


def test_state_machine_unit_head_blocked_without_perm():
    """AWAITING_UNIT_HEAD has no valid transitions without unit_head.review."""
    perms = {"leave_management.request.create", "leave_management.substitute.assign"}
    transitions = get_valid_transitions(LeaveStatus.AWAITING_UNIT_HEAD, perms)
    assert len(transitions) == 0


def test_state_machine_approved_is_terminal():
    """APPROVED state is terminal in the basic state machine."""
    all_perms = {
        "leave_management.request.create",
        "leave_management.substitute.assign",
        "leave_management.unit_head.review",
    }
    assert len(get_valid_transitions(LeaveStatus.APPROVED, all_perms)) == 0


def test_state_machine_rejected_is_terminal():
    """REJECTED state is terminal in the basic state machine."""
    all_perms = {
        "leave_management.request.create",
        "leave_management.substitute.assign",
        "leave_management.unit_head.review",
    }
    assert len(get_valid_transitions(LeaveStatus.REJECTED, all_perms)) == 0


# ===========================================================================
# 11. PREDICATES & GUARD HELPER TESTS
# ===========================================================================

def test_is_unit_head_predicate_positive():
    """is_unit_head returns True when unit_head.review permission is present."""
    assert is_unit_head({"leave_management.unit_head.review"}) is True
    assert is_unit_head(["leave_management.unit_head.review", "other.perm"]) is True


def test_is_unit_head_predicate_negative():
    """is_unit_head returns False when unit_head.review permission is absent."""
    assert is_unit_head(set()) is False
    assert is_unit_head({"leave_management.request.create"}) is False


def test_is_substitute_predicate_positive():
    """is_substitute returns True when substitute.assign permission is present."""
    assert is_substitute({"leave_management.substitute.assign"}) is True
    assert is_substitute(["leave_management.substitute.assign"]) is True


def test_is_substitute_predicate_negative():
    """is_substitute returns False when substitute.assign permission is absent."""
    assert is_substitute(set()) is False
    assert is_substitute({"leave_management.unit_head.review"}) is False


# ===========================================================================
# 12. TRANSITION OBJECT METHOD UNIT TESTS
# ===========================================================================

def test_transition_is_valid_wrong_from_status():
    """Transition.is_valid returns False if current status does not match from_status."""
    t = Transition(LeaveStatus.DRAFT, LeaveStatus.AWAITING_SUBSTITUTE)
    assert t.is_valid(LeaveStatus.AWAITING_UNIT_HEAD, set()) is False


def test_transition_is_valid_missing_permission():
    """Transition.is_valid returns False if required permission is missing."""
    t = Transition(LeaveStatus.DRAFT, LeaveStatus.AWAITING_SUBSTITUTE, permission="needed.perm")
    assert t.is_valid(LeaveStatus.DRAFT, {"wrong.perm"}) is False


def test_transition_is_valid_failing_guard():
    """Transition.is_valid returns False if a guard function evaluates to False."""
    failing_guard = lambda perms: False
    t = Transition(LeaveStatus.DRAFT, LeaveStatus.AWAITING_SUBSTITUTE, guards=[failing_guard])
    assert t.is_valid(LeaveStatus.DRAFT, set()) is False


def test_transition_is_valid_passing_all_checks():
    """Transition.is_valid returns True when status, permissions, and guards all match."""
    passing_guard = lambda perms: True
    t = Transition(LeaveStatus.DRAFT, LeaveStatus.AWAITING_SUBSTITUTE,
                   permission="needed.perm", guards=[passing_guard])
    assert t.is_valid(LeaveStatus.DRAFT, {"needed.perm"}) is True
