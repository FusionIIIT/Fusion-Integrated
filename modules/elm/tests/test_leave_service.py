from datetime import date
from decimal import Decimal

import pytest

from core.api.exceptions import ConflictError, PermissionDeniedError
from modules.elm.models import LeaveBalance, LeaveRequest, LeaveStatus, LeaveType
from modules.elm.services.leave_service import LeaveService


class Actor:
    def __init__(self, user_id, active_role, *permissions):
        self.user_id = user_id
        self.active_role = active_role
        self.permissions = set(permissions)

    def has_permission(self, code):
        return code in self.permissions


def _balance(user_id="1001", credited="4.0"):
    return LeaveBalance.objects.create(
        user_id=user_id,
        leave_type=LeaveType.CASUAL,
        year=2026,
        credited=Decimal(credited),
    )


def _apply(actor, **overrides):
    values = {
        "actor": actor,
        "leave_type": LeaveType.CASUAL,
        "start_date": date(2026, 10, 27),
        "end_date": date(2026, 10, 27),
        "duration_days": Decimal("1.0"),
        "reason": "Personal work",
    }
    values.update(overrides)
    return LeaveService.apply_leave(**values)


@pytest.mark.django_db
def test_apply_uses_identity_and_reserves_a_configured_balance():
    _balance()
    actor = Actor(1001, "faculty", "elm.leave.apply")

    request = _apply(actor)

    balance = LeaveBalance.objects.get(user_id="1001", leave_type=LeaveType.CASUAL, year=2026)
    assert request.applicant_user_id == "1001"
    assert request.status == LeaveStatus.PENDING_UNIT_HEAD
    assert balance.pending == Decimal("1.0")
    assert balance.balance == Decimal("3.0")
    assert request.action_logs.get().actor_user_id == "1001"


@pytest.mark.django_db
def test_apply_does_not_create_or_guess_a_leave_entitlement():
    actor = Actor(1001, "faculty", "elm.leave.apply")

    with pytest.raises(ConflictError, match="No leave balance is configured"):
        _apply(actor)

    assert not LeaveBalance.objects.exists()
    assert not LeaveRequest.objects.exists()


@pytest.mark.django_db
def test_apply_rejects_an_actor_without_the_module_permission():
    _balance()
    actor = Actor(1001, "faculty")

    with pytest.raises(PermissionDeniedError):
        _apply(actor)

    assert not LeaveRequest.objects.exists()


@pytest.mark.django_db
def test_forwarded_request_can_be_decided_by_the_authority_and_settles_once():
    balance = _balance()
    employee = Actor(1001, "faculty", "elm.leave.apply")
    unit_head = Actor(2002, "unit_head", "elm.leave.approve")
    director = Actor(3003, "director", "elm.leave.approve")
    request = _apply(employee)

    forwarded = LeaveService.review_unit_head(
        str(request.id), unit_head, approve=True, forward_higher=True
    )
    assert forwarded.status == LeaveStatus.PENDING_AUTHORITY
    balance.refresh_from_db()
    assert balance.pending == Decimal("1.0")
    assert balance.availed == Decimal("0.0")

    approved = LeaveService.review_authority(str(request.id), director, approve=True)
    balance.refresh_from_db()
    assert approved.status == LeaveStatus.APPROVED
    assert approved.current_approver_role == ""
    assert balance.pending == Decimal("0.0")
    assert balance.availed == Decimal("1.0")


@pytest.mark.django_db
def test_approver_cannot_approve_their_own_request():
    _balance()
    employee_approver = Actor(1001, "unit_head", "elm.leave.apply", "elm.leave.approve")
    request = _apply(employee_approver)

    with pytest.raises(PermissionDeniedError, match="own leave request"):
        LeaveService.review_unit_head(str(request.id), employee_approver, approve=True)

    balance = LeaveBalance.objects.get(user_id="1001", leave_type=LeaveType.CASUAL, year=2026)
    assert balance.pending == Decimal("1.0")
    assert request.status == LeaveStatus.PENDING_UNIT_HEAD


@pytest.mark.django_db
def test_substitute_decline_returns_request_for_replacement_without_releasing_balance():
    balance = _balance()
    employee = Actor(1001, "faculty", "elm.leave.apply")
    substitute = Actor(2002, "faculty", "elm.leave.substitute")
    request = _apply(employee, substitute_id="2002")

    declined = LeaveService.respond_substitute(str(request.id), substitute, accept=False)
    balance.refresh_from_db()
    assert declined.status == LeaveStatus.APPLICANT_ACTION_REQUIRED
    assert balance.pending == Decimal("1.0")

    replacement = LeaveService.replace_substitute(str(request.id), employee, "2003")
    balance.refresh_from_db()
    assert replacement.status == LeaveStatus.PENDING_SUBSTITUTE
    assert replacement.substitute_user_id == "2003"
    assert balance.pending == Decimal("1.0")


@pytest.mark.django_db
def test_higher_sanction_leave_routes_on_both_unit_head_recommendations():
    balance = LeaveBalance.objects.create(
        user_id="1001", leave_type=LeaveType.EARNED, year=2026, credited=Decimal("10.0")
    )
    employee = Actor(1001, "faculty", "elm.leave.apply")
    unit_head = Actor(2002, "unit_head", "elm.leave.approve")
    for recommend in (True, False):
        request = _apply(
            employee,
            leave_type=LeaveType.EARNED,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 1),
        )
        routed = LeaveService.review_unit_head(str(request.id), unit_head, approve=recommend)
        assert routed.status == LeaveStatus.PENDING_AUTHORITY
        assert routed.unit_head_recommendation == (
            "RECOMMENDED" if recommend else "NOT_RECOMMENDED"
        )
    balance.refresh_from_db()
    assert balance.pending == Decimal("2.0")


@pytest.mark.django_db
def test_director_applicant_uses_director_self_sanction_route():
    balance = _balance(user_id="3003")
    director = Actor(3003, "director", "elm.leave.apply", "elm.leave.approve")
    request = _apply(director)

    assert request.status == LeaveStatus.PENDING_AUTHORITY
    assert request.current_approver_role == "director"
    approved = LeaveService.review_authority(str(request.id), director, approve=True)
    balance.refresh_from_db()
    assert approved.status == LeaveStatus.APPROVED
    assert balance.pending == Decimal("0.0")
    assert balance.availed == Decimal("1.0")
