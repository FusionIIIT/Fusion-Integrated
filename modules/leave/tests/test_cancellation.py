"""Tests for cancellation of approved leave (BR-EL-023, BR-EL-024, EL-UC-008, WF-EL-03)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from core.api.exceptions import ConflictError
from modules.leave.models import LeaveBalance, LeaveLedgerEntry
from modules.leave.services import (
    apply_for_leave,
    process_cancellation_decision,
    request_cancellation,
    review_by_unit_head,
    sanction_application,
)


@pytest.mark.django_db
def test_cancellation_before_start_restores_balance_cl():
    user_id = 401
    unit_head_id = 402
    today = date.today()
    start = today + timedelta(days=7)
    end = today + timedelta(days=8)

    bal = LeaveBalance.objects.create(user_id=user_id, year=start.year, cl_balance=Decimal("8.0"))
    app = apply_for_leave(
        user_id=user_id,
        category="CL",
        start_date=start,
        end_date=end,
        purpose="Personal errand",
    )
    review_by_unit_head(
        reviewer_user_id=unit_head_id,
        application_id=app.pk,
        recommended=True,
    )
    app.refresh_from_db()
    assert app.status == "approved"
    bal.refresh_from_db()
    assert bal.cl_balance == Decimal("6.0")

    cancel_req = request_cancellation(
        user_id=user_id,
        application_id=app.pk,
        reason="Errand postponed",
    )
    assert cancel_req.status == "cancel_requested"
    assert cancel_req.parent_leave_id == app.pk

    review_by_unit_head(
        reviewer_user_id=unit_head_id,
        application_id=cancel_req.pk,
        recommended=True,
        remarks="Cancellation accepted",
    )

    app.refresh_from_db()
    cancel_req.refresh_from_db()
    assert app.status == "cancelled"
    assert cancel_req.status == "cancelled"

    bal.refresh_from_db()
    assert bal.cl_balance == Decimal("8.0")

    reversal = LeaveLedgerEntry.objects.filter(
        balance=bal, category="CL", entry_type="reversal"
    ).first()
    assert reversal is not None
    assert reversal.change_amount == Decimal("2.0")


@pytest.mark.django_db
def test_cancellation_rejection_leaves_original_approved():
    user_id = 403
    unit_head_id = 404
    today = date.today()
    start = today + timedelta(days=7)
    end = today + timedelta(days=8)

    bal = LeaveBalance.objects.create(user_id=user_id, year=start.year, cl_balance=Decimal("8.0"))
    app = apply_for_leave(
        user_id=user_id,
        category="CL",
        start_date=start,
        end_date=end,
        purpose="Personal errand",
    )
    review_by_unit_head(
        reviewer_user_id=unit_head_id,
        application_id=app.pk,
        recommended=True,
    )
    app.refresh_from_db()
    assert app.status == "approved"

    cancel_req = request_cancellation(
        user_id=user_id,
        application_id=app.pk,
        reason="Errand postponed",
    )

    review_by_unit_head(
        reviewer_user_id=unit_head_id,
        application_id=cancel_req.pk,
        recommended=False,
        remarks="Cannot cancel at short notice",
    )

    app.refresh_from_db()
    cancel_req.refresh_from_db()
    assert app.status == "approved"
    assert cancel_req.status == "rejected"
    bal.refresh_from_db()
    assert bal.cl_balance == Decimal("6.0")


@pytest.mark.django_db
def test_cancellation_blocked_after_start_date():
    user_id = 405
    today = date.today()
    start = today - timedelta(days=1)
    end = today + timedelta(days=3)

    LeaveBalance.objects.create(user_id=user_id, year=start.year, el_balance=Decimal("30.0"))
    app = apply_for_leave(
        user_id=user_id,
        category="EL",
        start_date=start,
        end_date=end,
        purpose="Family visit",
    )
    sanction_application(
        sanctioner_user_id=501,
        application_id=app.pk,
        decision="approved",
    )
    app.refresh_from_db()
    assert app.status == "approved"

    with pytest.raises(ConflictError) as exc_info:
        request_cancellation(
            user_id=user_id,
            application_id=app.pk,
            reason="Want to cancel ongoing leave",
        )
    assert exc_info.value.code == "leave_already_started"


@pytest.mark.django_db
def test_higher_sanction_cancellation_workflow():
    user_id = 406
    sanctioner_id = 502
    today = date.today()
    start = today + timedelta(days=10)
    end = today + timedelta(days=14)

    bal = LeaveBalance.objects.create(user_id=user_id, year=start.year, el_balance=Decimal("30.0"))
    app = apply_for_leave(
        user_id=user_id,
        category="EL",
        start_date=start,
        end_date=end,
        purpose="Conference",
    )
    sanction_application(
        sanctioner_user_id=sanctioner_id,
        application_id=app.pk,
        decision="approved",
    )
    app.refresh_from_db()
    assert app.status == "approved"
    bal.refresh_from_db()
    assert bal.el_balance == Decimal("25.0")

    cancel_req = request_cancellation(
        user_id=user_id,
        application_id=app.pk,
        reason="Conference cancelled",
    )
    assert cancel_req.status == "cancel_requested"

    process_cancellation_decision(
        reviewer_user_id=sanctioner_id,
        application_id=cancel_req.pk,
        decision="approved",
        remarks="Refund approved",
    )

    app.refresh_from_db()
    cancel_req.refresh_from_db()
    assert app.status == "cancelled"
    assert cancel_req.status == "cancelled"
    bal.refresh_from_db()
    assert bal.el_balance == Decimal("30.0")
