from datetime import date, datetime
from decimal import Decimal

import pytest

from modules.elm.domain.leave_days import UnsupportedLeaveCountingRule
from modules.elm.domain.leave_requests import (
    ExistingLeaveRequest,
    LeaveRequestState,
    LeaveRequestValidationError,
    ensure_no_overlap,
    validate_available_balance,
    validate_leave_request,
)


def test_valid_continuous_request_returns_decimal_quantity():
    result = validate_leave_request(
        leave_type="EL",
        start_date=date(2025, 10, 3),
        end_date=date(2025, 10, 6),
        purpose="Personal leave",
    )

    assert result == Decimal("4")
    assert isinstance(result, Decimal)


@pytest.mark.parametrize("purpose", ("", "  ", None))
def test_purpose_is_required(purpose):
    with pytest.raises(LeaveRequestValidationError) as error:
        validate_leave_request(
            leave_type="EL",
            start_date=date(2025, 10, 1),
            end_date=date(2025, 10, 1),
            purpose=purpose,
        )

    assert error.value.field == "purpose"
    assert error.value.code == "required"


@pytest.mark.parametrize(
    ("leave_type", "start_date", "end_date", "half_day"),
    (
        ("UNKNOWN", date(2025, 10, 1), date(2025, 10, 1), None),
        ("EL", "2025-10-01", date(2025, 10, 1), None),
        ("EL", datetime(2025, 10, 1), date(2025, 10, 1), None),
        ("EL", date(2025, 10, 2), date(2025, 10, 1), None),
        ("EL", date(2025, 10, 1), date(2025, 10, 1), "FIRST"),
        ("CL", date(2025, 10, 1), date(2025, 10, 1), "THIRD"),
    ),
)
def test_invalid_request_shape_is_rejected(leave_type, start_date, end_date, half_day):
    with pytest.raises(LeaveRequestValidationError):
        validate_leave_request(
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            purpose="Personal leave",
            half_day=half_day,
        )


@pytest.mark.parametrize("half_day", ("FIRST", "SECOND"))
def test_single_day_cl_half_day_returns_exact_half_day(half_day):
    assert validate_leave_request(
        leave_type="CL",
        start_date=date(2025, 10, 1),
        end_date=date(2025, 10, 1),
        purpose="Personal leave",
        half_day=half_day,
    ) == Decimal("0.5")


@pytest.mark.parametrize(
    ("leave_type", "half_day"),
    (("CL", None), ("RH", None), ("SCL", None)),
)
def test_unsupported_counting_rules_propagate(leave_type, half_day):
    with pytest.raises(UnsupportedLeaveCountingRule):
        validate_leave_request(
            leave_type=leave_type,
            start_date=date(2025, 10, 1),
            end_date=date(2025, 10, 1),
            purpose="Required purpose",
            half_day=half_day,
        )


def test_multi_day_cl_counting_rule_is_explicitly_unsupported():
    with pytest.raises(UnsupportedLeaveCountingRule):
        validate_leave_request(
            leave_type="CL",
            start_date=date(2025, 10, 1),
            end_date=date(2025, 10, 2),
            purpose="Required purpose",
        )


def _existing(
    *,
    start=date(2025, 10, 1),
    end=date(2025, 10, 1),
    half="FIRST",
    status=LeaveRequestState.PENDING_UNIT_HEAD,
    leave_type="CL",
):
    return ExistingLeaveRequest(start, end, leave_type, status, half)


def _check_overlap(candidate_half, existing):
    return ensure_no_overlap(
        leave_type="CL",
        start_date=date(2025, 10, 1),
        end_date=date(2025, 10, 1),
        half_day=candidate_half,
        existing_requests=(existing,),
    )


def test_same_cl_half_overlaps():
    with pytest.raises(LeaveRequestValidationError) as error:
        _check_overlap("FIRST", _existing(half="FIRST"))
    assert error.value.code == "overlap"


def test_different_cl_halves_on_same_day_do_not_overlap():
    assert _check_overlap("FIRST", _existing(half="SECOND")) is None


@pytest.mark.parametrize("existing_half", ("FIRST", "SECOND"))
def test_full_day_cl_conflicts_with_half_day_cl(existing_half):
    with pytest.raises(LeaveRequestValidationError):
        _check_overlap(None, _existing(half=existing_half))


@pytest.mark.parametrize(
    "status",
    (
        LeaveRequestState.PENDING_SUBSTITUTE,
        LeaveRequestState.APPLICANT_ACTION_REQUIRED,
        LeaveRequestState.PENDING_UNIT_HEAD,
        LeaveRequestState.PENDING_ESTABLISHMENT,
        LeaveRequestState.PENDING_FINAL_DECISION,
        LeaveRequestState.PENDING_DIRECTOR_SANCTION,
        LeaveRequestState.APPROVED,
    ),
)
def test_pending_and_approved_overlaps_block(status):
    with pytest.raises(LeaveRequestValidationError):
        _check_overlap("FIRST", _existing(half="FIRST", status=status))


@pytest.mark.parametrize(
    "status",
    (
        LeaveRequestState.DRAFT,
        LeaveRequestState.REJECTED,
        LeaveRequestState.CANCELLED,
        LeaveRequestState.WITHDRAWN,
    ),
)
def test_nonblocking_states_do_not_block(status):
    assert _check_overlap("FIRST", _existing(half="FIRST", status=status)) is None


def test_unknown_state_fails_even_when_interval_does_not_overlap():
    request = _existing(start=date(2025, 11, 1), end=date(2025, 11, 1), status="MYSTERY")
    with pytest.raises(LeaveRequestValidationError) as error:
        _check_overlap("FIRST", request)
    assert error.value.code == "unknown_state"


def test_overlapping_non_cl_intervals_are_rejected():
    request = _existing(start=date(2025, 9, 30), end=date(2025, 10, 2), half=None, leave_type="EL")
    with pytest.raises(LeaveRequestValidationError):
        _check_overlap("FIRST", request)


def test_sufficient_exact_decimal_balance_is_accepted():
    assert validate_available_balance(Decimal("0.5"), Decimal("0.5")) is None


@pytest.mark.parametrize(
    ("available", "chargeable", "code"),
    (
        (Decimal("0.49"), Decimal("0.5"), "insufficient_balance"),
        (Decimal("-0.1"), Decimal("0.5"), "negative_balance"),
        (Decimal("1"), Decimal("-0.5"), "negative_quantity"),
    ),
)
def test_invalid_or_insufficient_balance_is_rejected(available, chargeable, code):
    with pytest.raises(LeaveRequestValidationError) as error:
        validate_available_balance(available, chargeable)
    assert error.value.code == code


def test_balance_rejects_non_decimal_and_nonfinite_values():
    for available, chargeable in ((0.5, Decimal("0.5")), (Decimal("NaN"), Decimal("1"))):
        with pytest.raises(LeaveRequestValidationError):
            validate_available_balance(available, chargeable)
