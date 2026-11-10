from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIRequestFactory

from modules.leave_elm.api.views import (
    LeaveApplicationDetailView,
    LeaveReviewView,
    ResumptionReviewView,
)
from modules.leave_elm.models import (
    LeaveApplication,
    LeaveBalance,
    LeaveCategory,
    ResumptionRecord,
)


class Principal:
    def __init__(self, user_id, role, permissions):
        self.user_id = user_id
        self.active_role = role
        self.roles = (role,)
        self._permissions = set(permissions)

    def has_module(self, code):
        return code == "leave_elm"

    def has_permission(self, code):
        return code in self._permissions

    def has_any_permission(self, *codes):
        return any(code in self._permissions for code in codes)


@pytest.mark.django_db
def test_employee_cannot_read_another_employees_application():
    category = LeaveCategory.objects.create(code="CL", name="Casual Leave")
    application = LeaveApplication.objects.create(
        user_id=10,
        category=category,
        starts_on=date(2026, 10, 26),
        ends_on=date(2026, 10, 26),
        requested_days=Decimal("1"),
        purpose="Personal",
    )
    request = APIRequestFactory().get(f"/applications/{application.pk}")
    request.principal = Principal(11, "employee", {"leave_elm.application.view_self"})

    response = LeaveApplicationDetailView.as_view()(request, pk=application.pk)

    assert response.status_code == 404


@pytest.mark.django_db
def test_wrong_assigned_role_cannot_review_application():
    category = LeaveCategory.objects.create(code="CL", name="Casual Leave")
    application = LeaveApplication.objects.create(
        user_id=10,
        category=category,
        starts_on=date(2026, 10, 26),
        ends_on=date(2026, 10, 26),
        requested_days=Decimal("1"),
        purpose="Personal",
        status="awaiting_unit_head",
        assigned_role="unit_head",
    )
    request = APIRequestFactory().post(
        f"/applications/{application.pk}/review", {"outcome": "approved"}, format="json"
    )
    request.principal = Principal(12, "registrar", {"leave_elm.application.review"})

    response = LeaveReviewView.as_view()(request, pk=application.pk)

    assert response.status_code == 400


@pytest.mark.django_db
def test_assigned_authority_can_review_normal_resumption_without_balance_change():
    category = LeaveCategory.objects.create(code="EL", name="Earned Leave")
    application = LeaveApplication.objects.create(
        user_id=10,
        category=category,
        starts_on=date(2026, 10, 20),
        ends_on=date(2026, 10, 24),
        requested_days=Decimal("5"),
        requested_days_by_year={"2026": "5"},
        purpose="Personal",
        status="approved",
    )
    balance = LeaveBalance.objects.create(
        user_id=10, category=category, year=2026, used=Decimal("5"), closing_balance=Decimal("25")
    )
    record = ResumptionRecord.objects.create(
        application=application,
        user_id=10,
        actual_resumption_date=date(2026, 10, 24),
        assigned_role="registrar",
    )
    request = APIRequestFactory().post(f"/resumptions/{record.pk}/review", {}, format="json")
    request.principal = Principal(12, "registrar", {"leave_elm.application.review"})

    response = ResumptionReviewView.as_view()(request, pk=record.pk)
    balance.refresh_from_db()

    assert response.status_code == 200
    assert balance.used == Decimal("5")
    assert balance.closing_balance == Decimal("25")
