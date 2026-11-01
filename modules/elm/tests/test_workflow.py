from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.elm.domain.leave import Category, Stage
from modules.elm.models import (
    HolidayCalendar, HolidayDate, LeaveApplication, LeaveApplicationTransition,
    LeaveApprovalRoute, LeaveBalance,
)
from modules.elm.services import leave

pytestmark = pytest.mark.django_db


def actor(user_id, *permissions, kind="staff", roles=()):
    return SimpleNamespace(user_id=user_id, kind=kind, roles=roles,
                           has_permission=lambda code: code in permissions)


def test_submit_assigned_review_approve_and_withdraw_reservations(monkeypatch):
    from modules.directory.contracts import UserDTO
    monkeypatch.setattr("modules.directory.contracts.get_users", lambda ids: {
        uid: UserDTO(uid, "u", "User", "staff") for uid in ids
    })
    employee = actor(7, leave.P_APPLY, kind="staff")
    reviewer = actor(9, leave.P_REVIEW)
    LeaveApprovalRoute.objects.create(employee_id=7, category="CL", step_order=1,
                                      stage=Stage.UNIT_HEAD, approver_user_id=9)
    balance = LeaveBalance.objects.create(employee_id=7, category="CL", year=2026,
                                          allotted=Decimal(8))
    app = leave.apply_for_leave(actor=employee, category="CL", start_date=date(2026, 6, 1),
                                end_date=date(2026, 6, 1), reason="Appointment")
    balance.refresh_from_db()
    assert balance.reserved == Decimal(1)
    with pytest.raises(ConflictError):
        leave.apply_for_leave(actor=employee, category="CL", start_date=date(2026, 6, 1),
                              end_date=date(2026, 6, 1), reason="Duplicate")
    with pytest.raises(NotFoundError):
        leave.decide(actor=actor(10, leave.P_REVIEW), application_id=app.id, approve=True)
    approved = leave.decide(actor=reviewer, application_id=app.id, approve=True)
    balance.refresh_from_db()
    assert approved.status == LeaveApplication.Status.APPROVED
    assert (balance.reserved, balance.used) == (Decimal(0), Decimal(1))
    assert LeaveApplicationTransition.objects.filter(application=app).count() == 2

    second = leave.apply_for_leave(actor=employee, category="CL", start_date=date(2026, 6, 2),
                                   end_date=date(2026, 6, 2), reason="Appointment")
    leave.withdraw(actor=employee, application_id=second.id)
    balance.refresh_from_db()
    assert balance.reserved == Decimal(0)
    with pytest.raises(NotFoundError):
        leave.withdraw(actor=actor(8, leave.P_APPLY), application_id=second.id)
    third = leave.apply_for_leave(actor=employee, category="CL", start_date=date(2026, 6, 3),
                                  end_date=date(2026, 6, 3), reason="Appointment")
    rejected = leave.decide(actor=reviewer, application_id=third.id, approve=False)
    balance.refresh_from_db()
    assert rejected.status == LeaveApplication.Status.REJECTED
    assert (balance.reserved, balance.used) == (Decimal(0), Decimal(1))


def test_wrong_kind_entitlement_and_director_self_routing(monkeypatch):
    from modules.directory.contracts import UserDTO
    monkeypatch.setattr("modules.directory.contracts.get_users", lambda ids: {
        uid: UserDTO(uid, "u", "User", "faculty") for uid in ids
    })
    admin = actor(1, leave.P_MANAGE)
    with pytest.raises(ValueError):
        leave.set_balance(actor=admin, employee_id=2, category="EL", year=2026,
                          allotted=Decimal(30))
    monkeypatch.setattr("modules.directory.contracts.get_users", lambda ids: {
        uid: UserDTO(uid, "u", "User", "staff") for uid in ids
    })
    with pytest.raises(ValueError, match="annual limit"):
        leave.set_balance(actor=admin, employee_id=2, category="CL", year=2026,
                          allotted=Decimal("8.5"))
    monkeypatch.setattr("modules.directory.contracts.get_users", lambda ids: {
        uid: UserDTO(uid, "u", "User", "staff", is_active=False) for uid in ids
    })
    with pytest.raises(ValueError, match="active Faculty or Staff"):
        leave.set_balance(actor=admin, employee_id=2, category="CL", year=2026,
                          allotted=Decimal(8))
    monkeypatch.setattr("modules.directory.contracts.get_users", lambda ids: {
        uid: UserDTO(uid, "u", "User", "staff") for uid in ids
    })
    with pytest.raises(ValueError, match="applicant"):
        leave.set_route(actor=admin, employee_id=2, category="CL", steps=[
            {"approver_user_id": 3, "stage": Stage.DIRECTOR_SELF},
        ])
    with pytest.raises(ValueError, match="own reviewer"):
        leave.set_route(actor=admin, employee_id=2, category="EL", steps=[
            {"approver_user_id": 2, "stage": Stage.UNIT_HEAD},
            {"approver_user_id": 4, "stage": Stage.FINAL},
        ])


def test_self_review_denied_without_director_role():
    LeaveApprovalRoute.objects.create(employee_id=7, category="CL", step_order=1,
                                      stage=Stage.UNIT_HEAD, approver_user_id=7)
    app = LeaveApplication.objects.create(
        employee_id=7, category="CL", start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 1), chargeable_days=Decimal(1), reason="test",
        current_step_order=1, current_stage=Stage.UNIT_HEAD,
    )
    with pytest.raises(PermissionDeniedError):
        leave.decide(actor=actor(7, leave.P_REVIEW), application_id=app.id, approve=True)


def test_director_self_sanction_is_limited_to_the_applicant():
    LeaveApprovalRoute.objects.create(employee_id=7, category="CL", step_order=1,
                                      stage=Stage.DIRECTOR_SELF, approver_user_id=7)
    balance = LeaveBalance.objects.create(employee_id=7, category="CL", year=2026,
                                          allotted=Decimal(8))
    director = actor(7, leave.P_APPLY, leave.P_REVIEW, roles=("Director",))
    app = leave.apply_for_leave(actor=director, category="CL", start_date=date(2026, 6, 1),
                                end_date=date(2026, 6, 1), reason="Official duty")
    assert leave.decide(actor=director, application_id=app.id, approve=True).status == "approved"
    balance.refresh_from_db()
    assert (balance.reserved, balance.used) == (Decimal(0), Decimal(1))


def test_application_requires_permission_before_writing():
    with pytest.raises(PermissionDeniedError):
        leave.apply_for_leave(actor=actor(7), category="CL", start_date=date(2026, 6, 1),
                              end_date=date(2026, 6, 1), reason="test")


def test_calendar_rejects_a_date_marked_both_closed_and_restricted():
    day = date(2026, 1, 1)
    with pytest.raises(ValueError, match="only one holiday kind"):
        leave.publish_calendar(actor=actor(1, leave.P_MANAGE), name="Test", dates=[
            {"day": day, "name": "Holiday", "kind": HolidayDate.Kind.CLOSED},
            {"day": day, "name": "Restricted", "kind": HolidayDate.Kind.RESTRICTED},
        ])
    assert not HolidayCalendar.objects.exists()
