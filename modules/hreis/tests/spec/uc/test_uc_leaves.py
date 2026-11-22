import pytest
from datetime import date
from core.api.exceptions import BadRequestError, PermissionDeniedError
from modules.hreis.models import EmployeeServiceRecord, HrAuditLog, LeaveRequest
from modules.hreis.services.leaves import decide_leave_request, submit_leave_request
from rest_framework import status

pytestmark = pytest.mark.django_db


def test_uc_007_submit_valid_leave_request():
    """TEST-UC-007 [HR-UC-003 Main Flow]: Verify employee can submit a valid leave request and it enters Pending Current Authority state."""
    EmployeeServiceRecord.objects.create(
        user_id=210,
        employee_id="EMP0210",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 5},
    )
    leave = submit_leave_request(
        user_id=210,
        username="u210",
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 2),
        duration_days=2,
        justification="Personal work",
    )
    assert leave.id is not None
    assert leave.status == "pending"
    assert leave.current_authority_role == "hod"


def test_uc_008_leave_validation_failure_insufficient_balance():
    """TEST-UC-008 [HR-UC-003 Alternative A1]: Verify leave request with insufficient balance is rejected at submission."""
    EmployeeServiceRecord.objects.create(
        user_id=211,
        employee_id="EMP0211",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 1},
    )
    with pytest.raises(BadRequestError):
        submit_leave_request(
            user_id=211,
            username="u211",
            leave_type="casual",
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 3),
            duration_days=3,
            justification="Balance exceeded",
        )


def test_uc_009_leave_submission_unauthenticated(auth_client_factory):
    """TEST-UC-009 [HR-UC-003 Exception E1]: Verify unauthenticated actor cannot submit leave."""
    from rest_framework.test import APIClient
    client = APIClient()
    response = client.post(
        "/api/v1/hreis/leaves/",
        {
            "leave_type": "casual",
            "start_date": "2026-12-01",
            "end_date": "2026-12-02",
            "duration_days": 2,
            "justification": "Personal",
        },
        format="json",
    )
    assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


def test_uc_010_authority_approves_request():
    """TEST-UC-010 [HR-UC-004 Main Flow]: Verify designated approving authority can approve a pending HR request."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=212,
        employee_id="EMP0212",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 6},
    )
    leave = submit_leave_request(
        user_id=212,
        username="u212",
        leave_type="casual",
        start_date=date(2026, 12, 5),
        end_date=date(2026, 12, 6),
        duration_days=2,
        justification="Conference",
    )
    decided = decide_leave_request(
        leave_id=leave.id,
        outcome="approved",
        remarks="Approved by HOD",
        actor_id=301,
        actor_username="hod_cse",
        actor_role="hod",
    )
    assert decided.status == "approved"
    rec.refresh_from_db()
    assert rec.leave_balances["casual"] == 4


def test_uc_011_authority_rejects_request():
    """TEST-UC-011 [HR-UC-004 Alternative A1]: Verify designated approving authority can reject a pending HR request ending approval path."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=213,
        employee_id="EMP0213",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 5},
    )
    leave = submit_leave_request(
        user_id=213,
        username="u213",
        leave_type="casual",
        start_date=date(2026, 12, 5),
        end_date=date(2026, 12, 6),
        duration_days=2,
        justification="Conference",
    )
    decided = decide_leave_request(
        leave_id=leave.id,
        outcome="rejected",
        remarks="Not approved due to semester exams",
        actor_id=301,
        actor_username="hod_cse",
        actor_role="hod",
    )
    assert decided.status == "rejected"
    rec.refresh_from_db()
    assert rec.leave_balances["casual"] == 5


def test_uc_012_authority_forwards_request():
    """TEST-UC-012 [HR-UC-004 Alternative A2]: Verify approving authority can forward request to next configured authority."""
    EmployeeServiceRecord.objects.create(
        user_id=214,
        employee_id="EMP0214",
        department="CSE",
        designation="Professor",
        category="faculty",
        leave_balances={"sabbatical": 180},
    )
    leave = submit_leave_request(
        user_id=214,
        username="u214",
        leave_type="sabbatical",
        start_date=date(2026, 12, 1),
        end_date=date(2027, 2, 28),
        duration_days=90,
        justification="Research sabbatical",
    )
    decided = decide_leave_request(
        leave_id=leave.id,
        outcome="forwarded",
        remarks="Forwarding to Director",
        actor_id=301,
        actor_username="hod_cse",
        actor_role="hod",
    )
    assert decided.status == "pending"
    assert decided.current_authority_role in ("director", "dean", "registrar")


def test_uc_013_unauthorized_authority_decision_blocked():
    """TEST-UC-013 [HR-UC-004 Exception E1]: Verify non-designated authority cannot decide a request."""
    EmployeeServiceRecord.objects.create(
        user_id=215,
        employee_id="EMP0215",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 5},
    )
    leave = submit_leave_request(
        user_id=215,
        username="u215",
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 2),
        duration_days=2,
        justification="Personal",
    )
    with pytest.raises((BadRequestError, PermissionDeniedError)):
        decide_leave_request(
            leave_id=leave.id,
            outcome="approved",
            remarks="Unauthorized approval attempt",
            actor_id=999,
            actor_username="unauthorized_staff",
            actor_role="staff",
        )
