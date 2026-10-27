"""Unit and integration tests for leave services."""
import datetime
import pytest

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.leave.domain import state_machine as sm
from modules.leave.models import LeaveBalance, LeaveRequest
from modules.leave.services import leaves as leave_service


@pytest.mark.django_db
def test_initialize_and_get_balance():
    user_id = 201
    bal = leave_service.get_or_create_balance(user_id, 2026, "CL")
    assert bal.allocated == 8.0
    assert bal.used == 0.0
    assert bal.pending == 0.0
    assert bal.available == 8.0


@pytest.mark.django_db
def test_submit_leave_success_and_pending_balance():
    user_id = 202
    req = leave_service.submit_leave(
        user_id=user_id,
        category="CL",
        start_date=datetime.date(2026, 11, 2),
        end_date=datetime.date(2026, 11, 3),
        purpose="Family function",
    )
    assert req.pk is not None
    assert req.status == sm.UNIT_HEAD
    assert req.days_count == 2.0

    # Balance pending must increase by 2.0
    bal = LeaveBalance.objects.get(user_id=user_id, year=2026, category="CL")
    assert bal.pending == 2.0
    assert bal.available == 6.0


@pytest.mark.django_db
def test_submit_insufficient_balance_raises():
    user_id = 203
    # Try to request 10 days of CL (only 8 available)
    with pytest.raises(ConflictError) as exc_info:
        leave_service.submit_leave(
            user_id=user_id,
            category="CL",
            start_date=datetime.date(2026, 11, 2),
            end_date=datetime.date(2026, 11, 13),  # 10 working days
        )
    assert "insufficient_balance" in str(exc_info.value.code)


@pytest.mark.django_db
def test_station_leave_mandatory_details():
    user_id = 204
    with pytest.raises(BadRequestError):
        leave_service.submit_leave(
            user_id=user_id,
            category="CL",
            start_date=datetime.date(2026, 11, 2),
            end_date=datetime.date(2026, 11, 2),
            station_leave=True,
            station_details="",  # Empty details violates BR-EL-013
        )


@pytest.mark.django_db
def test_substitute_consent_flow():
    user_id = 205
    sub_id = 206
    req = leave_service.submit_leave(
        user_id=user_id,
        category="CL",
        start_date=datetime.date(2026, 11, 2),
        end_date=datetime.date(2026, 11, 2),
        substitute_user_id=sub_id,
    )
    assert req.status == sm.AWAITING_SUB
    assert req.substitute_status == "pending"

    # Substitute accepts
    accepted_req = leave_service.respond_as_substitute(
        request_id=req.pk,
        substitute_user_id=sub_id,
        accept=True,
        remarks="Will take classes",
    )
    assert accepted_req.status == sm.UNIT_HEAD
    assert accepted_req.substitute_status == "accepted"


@pytest.mark.django_db
def test_rejection_reason_mandatory():
    user_id = 207
    req = leave_service.submit_leave(
        user_id=user_id,
        category="CL",
        start_date=datetime.date(2026, 11, 2),
        end_date=datetime.date(2026, 11, 2),
    )
    class HeadActor:
        def has_permission(self, p):
            return p == "elm.leave.recommend"

    # Rejecting with empty reason must fail
    with pytest.raises(BadRequestError):
        leave_service.transition(
            request_id=req.pk,
            to_status=sm.REJECTED,
            actor=HeadActor(),
            reason="",
        )


@pytest.mark.django_db
def test_approval_and_cancellation_balance_lifecycle():
    user_id = 208
    req = leave_service.submit_leave(
        user_id=user_id,
        category="CL",
        start_date=datetime.date(2026, 12, 1),
        end_date=datetime.date(2026, 12, 1),
    )
    class AuthorityActor:
        def has_permission(self, p):
            return p == "elm.leave.decide"

    # Approve
    approved_req = leave_service.transition(
        request_id=req.pk,
        to_status=sm.APPROVED,
        actor=AuthorityActor(),
        reason="Granted",
    )
    assert approved_req.status == sm.APPROVED
    bal = LeaveBalance.objects.get(user_id=user_id, year=2026, category="CL")
    assert bal.used == 1.0
    assert bal.pending == 0.0

    # Cancel approved leave before start date
    class EmpActor:
        user_id = 208
        def has_permission(self, p):
            return p == "elm.leave.cancel"

    cancelled_req = leave_service.transition(
        request_id=approved_req.pk,
        to_status=sm.CANCELLED,
        actor=EmpActor(),
        reason="Plans cancelled",
    )
    assert cancelled_req.status == sm.CANCELLED
    bal.refresh_from_db()
    assert bal.used == 0.0
    assert bal.available == 8.0
