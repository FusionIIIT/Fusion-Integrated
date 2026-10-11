from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from core.api.exceptions import ConflictError
from modules.elm.models import (
    ApprovalRoute,
    EmployeeProfile,
    LeaveAccount,
    LeaveCalendarDate,
    OrganizationUnit,
)
from modules.elm.services import leave_management as service


class Actor:
    def __init__(self, user_id, *permissions, roles=()):
        self.user_id = user_id
        self.permissions = frozenset(permissions)
        self.roles = tuple(roles)

    def has_permission(self, code):
        return code in self.permissions


@pytest.mark.django_db
def test_half_day_cl_is_deducted_only_after_unit_head_approval():
    unit = OrganizationUnit.objects.create(code="IT", name="IT", unit_head_user_id=20)
    EmployeeProfile.objects.create(
        user_id=10, employee_type="staff", organization_unit=unit)
    employee = Actor(10, "elm.leave.apply", "elm.leave.view_self",
                     "elm.leave.withdraw")
    unit_head = Actor(20, "elm.leave.review")

    leave = service.apply_for_leave(employee, {
        "category": "CL", "start_date": date(2026, 10, 13),
        "end_date": date(2026, 10, 13), "half_day": "first_half",
        "purpose": "Appointment",
    })

    assert leave.status == "pending_unit_head"
    account = LeaveAccount.objects.get(
        user_id=10, category="CL", year=2026)
    assert account.balance == Decimal("8.00")

    service.decide_leave(unit_head, leave, "approve")
    account.refresh_from_db()
    leave.refresh_from_db()
    assert leave.status == "approved"
    assert account.used == Decimal("0.50")
    assert account.balance == Decimal("7.50")


@pytest.mark.django_db
def test_rh_requires_published_calendar_entry():
    unit = OrganizationUnit.objects.create(code="ADM", name="Admin", unit_head_user_id=20)
    EmployeeProfile.objects.create(
        user_id=10, employee_type="staff", organization_unit=unit)
    employee = Actor(10, "elm.leave.apply")
    payload = {
        "category": "RH", "start_date": date(2026, 10, 15),
        "end_date": date(2026, 10, 15), "purpose": "Restricted holiday",
    }

    with pytest.raises(ConflictError, match="published Restricted Holiday"):
        service.apply_for_leave(employee, payload)

    LeaveCalendarDate.objects.create(
        date=date(2026, 10, 15), kind="restricted_holiday", is_published=True)
    request = service.apply_for_leave(employee, payload)
    assert request.status == "pending_unit_head"


@pytest.mark.django_db
def test_higher_sanction_leave_moves_from_unit_head_recommendation_to_authority():
    unit = OrganizationUnit.objects.create(code="SCI", name="Science", unit_head_user_id=20)
    EmployeeProfile.objects.create(
        user_id=10, employee_type="staff", organization_unit=unit)
    ApprovalRoute.objects.create(
        category="EL", approver_user_id=30, approver_role="Registrar")
    employee = Actor(10, "elm.leave.apply")
    head = Actor(20, "elm.leave.review")
    registrar = Actor(30, "elm.leave.sanction", roles=("Registrar",))
    leave = service.apply_for_leave(employee, {
        "category": "EL", "start_date": date(2026, 10, 13),
        "end_date": date(2026, 10, 14), "purpose": "Personal leave",
    })

    service.decide_leave(head, leave, "recommend", "Recommended")
    leave.refresh_from_db()
    assert leave.status == "pending_sanction"
    assert leave.assigned_user_id == 30

    service.decide_leave(registrar, leave, "approve")
    leave.refresh_from_db()
    account = LeaveAccount.objects.get(user_id=10, category="EL", year=2026)
    assert leave.status == "approved"
    assert account.used == Decimal("2.00")
    assert account.balance == Decimal("28.00")


@pytest.mark.django_db
def test_withdrawal_is_immediate_and_stale_approval_is_rejected():
    unit = OrganizationUnit.objects.create(code="OPS", name="Operations", unit_head_user_id=20)
    EmployeeProfile.objects.create(
        user_id=10, employee_type="staff", organization_unit=unit)
    employee = Actor(10, "elm.leave.apply", "elm.leave.withdraw")
    head = Actor(20, "elm.leave.review")
    leave = service.apply_for_leave(employee, {
        "category": "CL", "start_date": date(2026, 10, 13),
        "end_date": date(2026, 10, 13), "purpose": "Appointment",
    })

    service.withdraw(employee, leave)
    leave.refresh_from_db()
    assert leave.status == "withdrawn"
    with pytest.raises(ConflictError, match="no longer awaiting"):
        service.decide_leave(head, leave, "approve")


@pytest.mark.django_db
def test_year_end_converts_fractional_faculty_vl_without_carrying_vl():
    EmployeeProfile.objects.create(user_id=10, employee_type="faculty")
    vl = LeaveAccount.objects.create(
        user_id=10, category="VL", year=2025, credited=Decimal("5.50"),
        closing_balance=Decimal("5.50"))
    actor = SimpleNamespace(
        user_id=0, has_permission=lambda code: code == "elm.leave.year_end")

    result = service.process_year_end(actor, 2025)

    vl.refresh_from_db()
    next_vl = LeaveAccount.objects.get(user_id=10, category="VL", year=2026)
    next_el = LeaveAccount.objects.get(user_id=10, category="EL", year=2026)
    assert result == {"processed": 1, "exceptions": []}
    assert vl.balance == Decimal("0.00")
    assert vl.year_end_processed is True
    assert next_vl.credited == Decimal("60.00")
    assert next_el.credited == Decimal("2.75")
