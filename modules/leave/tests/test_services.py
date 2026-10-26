# Integration tests for ELM application services
from datetime import date, timedelta
from decimal import Decimal

import pytest

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.leave.domain.constants import (
    HALF_DAY_NONE,
    LEAVE_TYPE_CL,
    LEAVE_TYPE_EL,
    STATUS_APPROVED,
    STATUS_CANCELLED,
    STATUS_PENDING,
    STATUS_REJECTED,
    STATUS_WITHDRAWN,
)
from modules.leave.models import LeaveApplication, LeaveBalance
from modules.leave.services.applications import (
    cancel_application,
    initialize_user_balances,
    review_application,
    submit_application,
    withdraw_application,
)

pytestmark = pytest.mark.django_db


def test_submit_application_success():
    """Submit application computes days and creates PENDING record."""
    user_id = 501
    start = date(2026, 11, 2)   # Monday
    end = date(2026, 11, 4)     # Wednesday (3 working days)

    app = submit_application(
        user_id=user_id,
        leave_type=LEAVE_TYPE_CL,
        start_date=start,
        end_date=end,
        reason="Family event",
    )

    assert app.id is not None
    assert app.status == STATUS_PENDING
    assert app.days == Decimal("3.00")
    # Verify balance was initialized
    bal = LeaveBalance.objects.get(user_id=user_id, leave_type=LEAVE_TYPE_CL, year=2026)
    assert bal.allocated == Decimal("8.00")
    assert bal.used == Decimal("0.00")


def test_submit_insufficient_balance():
    """Submitting leave exceeding available balance raises BadRequestError."""
    user_id = 502
    initialize_user_balances(user_id, 2026)
    # Drain balance
    LeaveBalance.objects.filter(user_id=user_id, leave_type=LEAVE_TYPE_CL, year=2026).update(
        used=Decimal("7.00")
    )

    start = date(2026, 11, 2)
    end = date(2026, 11, 4)  # 3 days requested, only 1 available
    with pytest.raises(BadRequestError, match="Insufficient balance"):
        submit_application(
            user_id=user_id,
            leave_type=LEAVE_TYPE_CL,
            start_date=start,
            end_date=end,
            reason="Vacation",
        )


def test_review_approval_deducts_balance():
    """Approving pending application deducts balance and sets APPROVED."""
    applicant_id = 503
    reviewer_id = 999
    start = date(2026, 11, 2)
    end = date(2026, 11, 3)

    app = submit_application(
        user_id=applicant_id,
        leave_type=LEAVE_TYPE_CL,
        start_date=start,
        end_date=end,
        reason="Medical checkup",
    )

    reviewed = review_application(
        application_id=app.id,
        reviewer_user_id=reviewer_id,
        action="APPROVE",
        remarks="Approved as requested",
    )

    assert reviewed.status == STATUS_APPROVED
    assert reviewed.reviewed_by == reviewer_id
    bal = LeaveBalance.objects.get(user_id=applicant_id, leave_type=LEAVE_TYPE_CL, year=2026)
    assert bal.used == Decimal("2.00")


def test_review_rejection_preserves_balance():
    """Rejecting pending application does NOT deduct balance."""
    applicant_id = 504
    reviewer_id = 999
    start = date(2026, 11, 2)
    end = date(2026, 11, 3)

    app = submit_application(
        user_id=applicant_id,
        leave_type=LEAVE_TYPE_CL,
        start_date=start,
        end_date=end,
        reason="Short trip",
    )

    reviewed = review_application(
        application_id=app.id,
        reviewer_user_id=reviewer_id,
        action="REJECT",
        remarks="Academic duty pending",
    )

    assert reviewed.status == STATUS_REJECTED
    bal = LeaveBalance.objects.get(user_id=applicant_id, leave_type=LEAVE_TYPE_CL, year=2026)
    assert bal.used == Decimal("0.00")


def test_self_approval_blocked():
    """BR-EL-036: Approver cannot approve their own application."""
    user_id = 505
    start = date(2026, 11, 2)
    end = date(2026, 11, 3)

    app = submit_application(
        user_id=user_id,
        leave_type=LEAVE_TYPE_CL,
        start_date=start,
        end_date=end,
        reason="Personal work",
    )

    with pytest.raises(PermissionDeniedError, match="strictly prohibited"):
        review_application(
            application_id=app.id,
            reviewer_user_id=user_id,
            action="APPROVE",
        )


def test_withdraw_application_success():
    """BR-EL-022: Applicant can immediately withdraw pending request."""
    user_id = 506
    start = date(2026, 11, 2)
    end = date(2026, 11, 3)

    app = submit_application(
        user_id=user_id,
        leave_type=LEAVE_TYPE_CL,
        start_date=start,
        end_date=end,
        reason="Personal",
    )

    withdrawn = withdraw_application(application_id=app.id, user_id=user_id)
    assert withdrawn.status == STATUS_WITHDRAWN

    # Non-applicant cannot withdraw
    with pytest.raises(PermissionDeniedError, match="Only the applicant"):
        withdraw_application(application_id=app.id, user_id=999)


def test_cancel_application_restores_balance():
    """BR-EL-023: Cancelling approved application before start date refunds balance."""
    applicant_id = 507
    reviewer_id = 999
    # Start date in future
    future_start = date.today() + timedelta(days=10)
    future_end = future_start + timedelta(days=2)

    app = submit_application(
        user_id=applicant_id,
        leave_type=LEAVE_TYPE_EL,
        start_date=future_start,
        end_date=future_end,
        reason="Conference travel",
    )
    review_application(app.id, reviewer_id, "APPROVE")

    bal_before = LeaveBalance.objects.get(user_id=applicant_id, leave_type=LEAVE_TYPE_EL, year=future_start.year)
    assert bal_before.used == Decimal("3.00")

    cancelled = cancel_application(application_id=app.id, user_id=applicant_id)
    assert cancelled.status == STATUS_CANCELLED

    bal_after = LeaveBalance.objects.get(user_id=applicant_id, leave_type=LEAVE_TYPE_EL, year=future_start.year)
    assert bal_after.used == Decimal("0.00")


def test_cancel_application_fails_after_start_date():
    """BR-EL-023: Cannot cancel approved leave on or after start date."""
    applicant_id = 508
    past_start = date.today() - timedelta(days=2)
    past_end = date.today() + timedelta(days=1)

    app = LeaveApplication.objects.create(
        user_id=applicant_id,
        leave_type=LEAVE_TYPE_CL,
        start_date=past_start,
        end_date=past_end,
        half_day=HALF_DAY_NONE,
        days=Decimal("2.00"),
        reason="Emergency",
        status=STATUS_APPROVED,
    )
    LeaveBalance.objects.create(
        user_id=applicant_id,
        leave_type=LEAVE_TYPE_CL,
        year=past_start.year,
        allocated=Decimal("8.00"),
        used=Decimal("2.00"),
    )

    with pytest.raises(ConflictError, match="cannot be cancelled once start date arrived"):
        cancel_application(application_id=app.id, user_id=applicant_id)
