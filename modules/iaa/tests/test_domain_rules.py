"""Domain rules tests: pure Python, no database."""

from decimal import Decimal

import pytest

from modules.iaa.domain.rules import (
    DomainValidationError,
    check_budget_sufficiency,
    is_high_value_ta,
    validate_decision_remarks,
    validate_record_not_locked,
    validate_request_completeness,
    validate_segregation_of_duties,
    validate_travel_completeness,
)


def test_segregation_of_duties_prevents_self_approval():
    with pytest.raises(DomainValidationError, match="Creator or claimant cannot approve"):
        validate_segregation_of_duties(1001, 1001)


def test_segregation_of_duties_allows_distinct_users():
    validate_segregation_of_duties(1001, 2002)


def test_decision_remarks_validation():
    validate_decision_remarks("Approved with satisfaction")
    with pytest.raises(DomainValidationError, match="remarks are mandatory"):
        validate_decision_remarks("")
    with pytest.raises(DomainValidationError, match="remarks are mandatory"):
        validate_decision_remarks("   ")
    with pytest.raises(DomainValidationError, match="remarks are mandatory"):
        validate_decision_remarks(None)


def test_request_completeness_validation():
    validate_request_completeness("Office Stationery", "Desc", "CSE", Decimal("500.00"), 2)
    with pytest.raises(DomainValidationError, match="Request title is mandatory"):
        validate_request_completeness("", "Desc", "CSE", Decimal("500.00"), 2)
    with pytest.raises(DomainValidationError, match="Department is mandatory"):
        validate_request_completeness("Office Stationery", "Desc", "", Decimal("500.00"), 2)
    with pytest.raises(DomainValidationError, match="Total amount must be greater than zero"):
        validate_request_completeness("Office Stationery", "Desc", "CSE", Decimal("0.00"), 2)
    with pytest.raises(DomainValidationError, match="At least one expense line item"):
        validate_request_completeness("Office Stationery", "Desc", "CSE", Decimal("500.00"), 0)


def test_travel_completeness_validation():
    validate_travel_completeness(
        "Conf", "2026-03-01", "2026-03-05", Decimal("100.00"), "DEL", "BOM"
    )
    with pytest.raises(DomainValidationError, match="Travel purpose is mandatory"):
        validate_travel_completeness(
            "", "2026-03-01", "2026-03-05", Decimal("100.00"), "DEL", "BOM"
        )
    with pytest.raises(DomainValidationError, match="Departure and arrival dates"):
        validate_travel_completeness("Conf", None, "2026-03-05", Decimal("100.00"), "DEL", "BOM")
    with pytest.raises(DomainValidationError, match="Source and destination locations"):
        validate_travel_completeness(
            "Conf", "2026-03-01", "2026-03-05", Decimal("100.00"), "", "BOM"
        )
    with pytest.raises(DomainValidationError, match="Claimed amount must be greater"):
        validate_travel_completeness(
            "Conf", "2026-03-01", "2026-03-05", Decimal("0.00"), "DEL", "BOM"
        )


def test_high_value_ta():
    assert is_high_value_ta(Decimal("50000.00"), Decimal("50000.00"))
    assert is_high_value_ta(Decimal("60000.00"), Decimal("50000.00"))
    assert not is_high_value_ta(Decimal("49999.00"), Decimal("50000.00"))


def test_budget_sufficiency():
    assert check_budget_sufficiency(Decimal("1000.00"), Decimal("500.00"))
    assert check_budget_sufficiency(Decimal("1000.00"), Decimal("1000.00"))
    assert not check_budget_sufficiency(Decimal("1000.00"), Decimal("1000.01"))


def test_record_locked_validation():
    validate_record_not_locked(False)
    with pytest.raises(DomainValidationError, match="locked against direct editing"):
        validate_record_not_locked(True)
