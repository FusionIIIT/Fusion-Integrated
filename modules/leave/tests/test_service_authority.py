"""Service-level authority scoping for ELM decisions."""
from datetime import date

import pytest
from django.core.exceptions import ValidationError

from modules.leave import domain
from modules.leave.models import (
    AttendanceSyncOutbox,
    LeaveAccount,
    LeaveHierarchyConfig,
    LeaveRequest,
)
from modules.leave.services.leave_services import (
    review_resumption,
    review_unit_head,
    sanction_decision,
)

pytestmark = pytest.mark.django_db


def _request(**overrides):
    values = {
        "applicant_id": "employee-1",
        "applicant_role": "staff",
        "department": "CSE",
        "category": "EL",
        "start_date": date(2026, 5, 1),
        "end_date": date(2026, 5, 3),
        "purpose": "Authority scoping test",
        "unit_head_id": "unit-head-1",
        "sanctioning_authority_id": "sanctioner-1",
    }
    values.update(overrides)
    route, _ = LeaveHierarchyConfig.objects.get_or_create(
        department=values["department"], applicant_role=values["applicant_role"],
        category=values["category"], defaults={
            "unit_head_id": values["unit_head_id"],
            "sanctioning_authority_id": values["sanctioning_authority_id"],
        },
    )
    values["routing_config"] = route
    return LeaveRequest.objects.create(**values)


def test_unit_head_cannot_review_request_assigned_to_another_unit_head():
    request = _request(status=domain.rules.ST_AWAITING_UNIT_HEAD)

    with pytest.raises(ValidationError, match="not assigned to this Unit Head"):
        review_unit_head(request.pk, "unit-head-2", "RECOMMEND")

    request.refresh_from_db()
    assert request.status == domain.rules.ST_AWAITING_UNIT_HEAD


def test_sanctioner_cannot_decide_request_assigned_to_another_authority():
    request = _request(status=domain.rules.ST_AWAITING_SANCTION)

    with pytest.raises(ValidationError, match="not assigned to this sanctioning authority"):
        sanction_decision(request.pk, "sanctioner-2", False)

    request.refresh_from_db()
    assert request.status == domain.rules.ST_AWAITING_SANCTION


def test_other_authority_cannot_review_resumption():
    request = _request(
        status=domain.rules.ST_RESUMPTION_PENDING,
        actual_resumption_date=date(2026, 5, 3),
    )

    with pytest.raises(ValidationError, match="not assigned to this sanctioning authority"):
        review_resumption(request.pk, "sanctioner-2")

    request.refresh_from_db()
    assert request.status == domain.rules.ST_RESUMPTION_PENDING


def test_reviewed_early_resumption_updates_period_and_restores_balance():
    request = _request(
        status=domain.rules.ST_RESUMPTION_PENDING,
        actual_resumption_date=date(2026, 5, 1),
    )
    account = LeaveAccount.objects.create(
        user_id=request.applicant_id, employee_type="staff",
        category=request.category, year=request.start_date.year, balance=7.0,
    )
    result = review_resumption(request.pk, "sanctioner-1")
    assert result.end_date == date(2026, 5, 1)
    account.refresh_from_db()
    assert account.balance == 9.0
    event = AttendanceSyncOutbox.objects.get(request=request)
    assert event.status == "pending"
    assert event.payload["approved_end_date"] == "2026-05-03"
    assert event.payload["recorded_leave_end_date"] == "2026-05-01"


def test_reviewed_late_resumption_updates_period_and_deducts_balance():
    request = _request(
        status=domain.rules.ST_RESUMPTION_PENDING,
        actual_resumption_date=date(2026, 5, 5),
    )
    account = LeaveAccount.objects.create(
        user_id=request.applicant_id, employee_type="staff",
        category=request.category, year=request.start_date.year, balance=7.0,
    )
    result = review_resumption(request.pk, "sanctioner-1")
    assert result.end_date == date(2026, 5, 5)
    account.refresh_from_db()
    assert account.balance == 5.0


def test_reviewed_normal_resumption_keeps_approved_period_and_balance():
    request = _request(
        status=domain.rules.ST_RESUMPTION_PENDING,
        actual_resumption_date=date(2026, 5, 3),
    )
    account = LeaveAccount.objects.create(
        user_id=request.applicant_id, employee_type="staff",
        category=request.category, year=request.start_date.year, balance=7.0,
    )
    result = review_resumption(request.pk, "sanctioner-1")
    assert result.end_date == date(2026, 5, 3)
    account.refresh_from_db()
    assert account.balance == 7.0
