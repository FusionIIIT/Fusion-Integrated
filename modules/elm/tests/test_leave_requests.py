from datetime import date

import pytest

from core.api.exceptions import ConflictError
from modules.elm.models import LeaveBalance, LeaveRequest
from modules.elm.services.leave_requests import submit_leave_request

pytestmark = pytest.mark.django_db


def submit(**overrides):
    LeaveBalance.objects.get_or_create(
        employee_id=overrides.get("employee_id", 101),
        leave_category=overrides.get("leave_category", "EL"),
        year=overrides.get("start_date", date(2026, 11, 2)).year,
        defaults={"entitled_days": 30},
    )
    data = {
        "employee_id": 101,
        "leave_category": "EL",
        "start_date": date(2026, 11, 2),
        "end_date": date(2026, 11, 4),
        "reason": "Personal work",
    }
    data.update(overrides)
    return submit_leave_request(**data)


def test_valid_request_is_created():
    request = submit()

    assert request.pk is not None
    assert request.employee_id == 101
    assert request.status == LeaveRequest.Status.PENDING
    assert request.approval_stage == LeaveRequest.ApprovalStage.UNIT_HEAD


def test_end_date_before_start_date_is_rejected():
    with pytest.raises(ConflictError):
        submit(
            start_date=date(2026, 11, 5),
            end_date=date(2026, 11, 2),
        )


def test_empty_reason_is_rejected():
    with pytest.raises(ConflictError):
        submit(reason="   ")


def test_unsupported_category_is_rejected():
    with pytest.raises(ConflictError):
        submit(leave_category="XYZ")


def test_overlapping_pending_request_is_rejected():
    submit()

    with pytest.raises(ConflictError) as exc:
        submit(
            start_date=date(2026, 11, 3),
            end_date=date(2026, 11, 6),
        )

    assert exc.value.code == "leave_overlap"


def test_non_overlapping_request_is_allowed():
    submit()

    request = submit(
        start_date=date(2026, 11, 5),
        end_date=date(2026, 11, 7),
    )

    assert request.pk is not None
