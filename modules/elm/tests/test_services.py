"""Unit tests for ELM service operations and business workflows."""
import datetime

import pytest

from conftest import make_principal
from core.api.exceptions import ConflictError, PermissionDeniedError
from modules.elm.domain.state_machine import LeaveCategory, LeaveStatus
from modules.elm.models import LeaveApplication
from modules.elm.services.leave import apply_leave, cancel_leave, review_leave

pytestmark = pytest.mark.django_db


@pytest.fixture
def employee():
    return make_principal(
        user_id=101,
        modules=("elm",),
        permissions=("elm.leave_application.apply", "elm.leave_application.view_self"),
    )


@pytest.fixture
def hr_manager():
    return make_principal(
        user_id=202,
        modules=("elm",),
        permissions=(
            "elm.leave_application.view_self",
            "elm.leave_application.apply",
            "elm.leave_application.manage",
        ),
    )


def test_apply_leave_creates_pending_record(employee):
    app = apply_leave(
        principal=employee,
        category=LeaveCategory.CASUAL.value,
        start_date=datetime.date(2026, 12, 1),
        end_date=datetime.date(2026, 12, 3),
        reason="Family event",
    )
    assert app.pk is not None
    assert app.user_id == 101
    assert app.status == LeaveStatus.PENDING.value
    assert app.category == LeaveCategory.CASUAL.value


def test_apply_leave_rejects_overlapping_dates(employee):
    apply_leave(
        principal=employee,
        category=LeaveCategory.CASUAL.value,
        start_date=datetime.date(2026, 12, 10),
        end_date=datetime.date(2026, 12, 15),
        reason="Vacation",
    )
    with pytest.raises(ConflictError) as exc:
        apply_leave(
            principal=employee,
            category=LeaveCategory.MEDICAL.value,
            start_date=datetime.date(2026, 12, 12),
            end_date=datetime.date(2026, 12, 18),
            reason="Checkup",
        )
    assert exc.value.code == "overlapping_leave"


def test_hr_can_approve_leave(employee, hr_manager):
    app = apply_leave(
        principal=employee,
        category=LeaveCategory.MEDICAL.value,
        start_date=datetime.date(2026, 12, 20),
        end_date=datetime.date(2026, 12, 22),
        reason="Doctor advised rest",
    )
    reviewed = review_leave(
        principal=hr_manager,
        application_id=app.id,
        action="approve",
        remarks="Approved with medical certificate",
    )
    assert reviewed.status == LeaveStatus.APPROVED.value
    assert reviewed.reviewed_by_user_id == 202
    assert reviewed.reviewed_at is not None
    assert reviewed.remarks == "Approved with medical certificate"


def test_employee_cannot_review_leave(employee):
    app = LeaveApplication.objects.create(
        user_id=101,
        category=LeaveCategory.CASUAL.value,
        start_date=datetime.date(2026, 12, 1),
        end_date=datetime.date(2026, 12, 2),
        reason="Personal",
        status=LeaveStatus.PENDING.value,
    )
    with pytest.raises(PermissionDeniedError):
        review_leave(principal=employee, application_id=app.id, action="approve")


def test_cancel_pending_leave(employee):
    app = apply_leave(
        principal=employee,
        category=LeaveCategory.CASUAL.value,
        start_date=datetime.date(2026, 12, 5),
        end_date=datetime.date(2026, 12, 6),
        reason="Trip planned",
    )
    cancelled = cancel_leave(principal=employee, application_id=app.id)
    assert cancelled.status == LeaveStatus.CANCELLED.value


def test_cannot_cancel_already_approved_leave(employee, hr_manager):
    app = apply_leave(
        principal=employee,
        category=LeaveCategory.CASUAL.value,
        start_date=datetime.date(2026, 12, 5),
        end_date=datetime.date(2026, 12, 6),
        reason="Trip planned",
    )
    review_leave(principal=hr_manager, application_id=app.id, action="approve")
    with pytest.raises(ConflictError):
        cancel_leave(principal=employee, application_id=app.id)
