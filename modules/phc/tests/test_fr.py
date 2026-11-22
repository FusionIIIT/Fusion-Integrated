"""FR strategy: verify observable functional requirements and service outputs."""

from decimal import Decimal

import pytest

from modules.phc.domain.reimbursement import (
    ReimbursementValidationError,
    check_employee_eligibility,
    check_submission_window,
)
from modules.phc.domain.state_machine import (
    InvalidClaimTransition,
    advance_claim,
)
from modules.phc.domain.state_machine import (
    ReimbursementState as RS,
)
from modules.phc.models import InventoryItem


def test_employee_and_staff_are_eligible_but_student_is_not():
    check_employee_eligibility("faculty")
    check_employee_eligibility("staff")
    with pytest.raises(ReimbursementValidationError):
        check_employee_eligibility("student")


def test_claim_window_accepts_boundary_and_rejects_expired_or_future_date():
    import datetime as dt

    expense = dt.date(2026, 1, 1)
    check_submission_window(expense, dt.date(2026, 3, 2), 60)
    with pytest.raises(ReimbursementValidationError):
        check_submission_window(expense, dt.date(2026, 3, 3), 60)
    with pytest.raises(ReimbursementValidationError):
        check_submission_window(dt.date(2026, 1, 2), expense, 60)


def test_claim_transitions_require_forward_order_and_correct_actor():
    advance_claim(RS.PENDING_PHC_REVIEW, RS.PENDING_ACCOUNTS, "phc_staff")
    with pytest.raises(InvalidClaimTransition):
        advance_claim(RS.PENDING_PHC_REVIEW, RS.REJECTED, "phc_staff")
    with pytest.raises(InvalidClaimTransition):
        advance_claim(RS.PENDING_ACCOUNTS, RS.PENDING_SANCTION, "phc_staff")


@pytest.mark.django_db
def test_inventory_low_stock_is_strictly_below_threshold():
    item = InventoryItem.objects.create(
        name="Gauze", stock_quantity=Decimal("4"), reorder_threshold=Decimal("5")
    )
    assert item.is_low_stock
    item.stock_quantity = Decimal("5")
    assert not item.is_low_stock
