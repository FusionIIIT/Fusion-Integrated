import pytest
from datetime import date
from decimal import Decimal
from modules.hreis.models import EmployeeServiceRecord, HrAuditLog, LeaveRequest
from modules.hreis.services.leaves import decide_leave_request, submit_leave_request

pytestmark = pytest.mark.django_db


def test_fr_047_employee_apply_leave():
    """TEST-FR-047 [HR-AFR-029]: Verify HR-EIS allows Employees to apply for leave requests."""
    EmployeeServiceRecord.objects.create(
        user_id=190,
        employee_id="EMP0190",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 5},
    )
    leave = submit_leave_request(
        user_id=190,
        username="u190",
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 2),
        duration_days=2,
        justification="Personal work",
    )
    assert leave.id is not None
    assert leave.status == "pending"


def test_fr_048_casual_leave_supported():
    """TEST-FR-048 [HR-AFR-030]: Verify HR-EIS supports Casual leave as an available leave request type."""
    EmployeeServiceRecord.objects.create(
        user_id=191,
        employee_id="EMP0191",
        department="ECE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 5},
    )
    leave = submit_leave_request(
        user_id=191,
        username="u191",
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 1),
        duration_days=1,
        justification="Personal",
    )
    assert leave.leave_type == "casual"


def test_fr_049_restricted_leave_supported():
    """TEST-FR-049 [HR-AFR-031]: Verify HR-EIS supports Restricted leave as an available leave request type."""
    EmployeeServiceRecord.objects.create(
        user_id=192,
        employee_id="EMP0192",
        department="ECE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"restricted": 2},
    )
    leave = submit_leave_request(
        user_id=192,
        username="u192",
        leave_type="restricted",
        start_date=date(2026, 12, 3),
        end_date=date(2026, 12, 3),
        duration_days=1,
        justification="Festival holiday",
    )
    assert leave.leave_type == "restricted"


def test_fr_050_medical_leave_supported():
    """TEST-FR-050 [HR-AFR-032]: Verify HR-EIS supports Medical leave as an available leave request type."""
    EmployeeServiceRecord.objects.create(
        user_id=193,
        employee_id="EMP0193",
        department="ME",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"medical": 10},
    )
    leave = submit_leave_request(
        user_id=193,
        username="u193",
        leave_type="medical",
        start_date=date(2026, 12, 4),
        end_date=date(2026, 12, 6),
        duration_days=3,
        justification="Doctor prescription attached",
    )
    assert leave.leave_type == "medical"


def test_fr_051_earned_leave_supported():
    """TEST-FR-051 [HR-AFR-033]: Verify HR-EIS supports Earned leave as an available leave request type."""
    EmployeeServiceRecord.objects.create(
        user_id=194,
        employee_id="EMP0194",
        department="ME",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"earned": 15},
    )
    leave = submit_leave_request(
        user_id=194,
        username="u194",
        leave_type="earned",
        start_date=date(2026, 12, 8),
        end_date=date(2026, 12, 10),
        duration_days=3,
        justification="Vacation period",
    )
    assert leave.leave_type == "earned"


def test_fr_052_vacation_leave_supported():
    """TEST-FR-052 [HR-AFR-034]: Verify HR-EIS supports Vacation leave as an available leave request type."""
    EmployeeServiceRecord.objects.create(
        user_id=195,
        employee_id="EMP0195",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"vacation": 30},
    )
    leave = submit_leave_request(
        user_id=195,
        username="u195",
        leave_type="vacation",
        start_date=date(2026, 12, 15),
        end_date=date(2026, 12, 20),
        duration_days=6,
        justification="Winter break",
    )
    assert leave.leave_type == "vacation"


def test_fr_053_sabbatical_leave_supported():
    """TEST-FR-053 [HR-AFR-035]: Verify HR-EIS supports Sabbatical leave as an available leave request type."""
    EmployeeServiceRecord.objects.create(
        user_id=196,
        employee_id="EMP0196",
        department="CSE",
        designation="Professor",
        category="faculty",
        leave_balances={"sabbatical": 365},
    )
    leave = submit_leave_request(
        user_id=196,
        username="u196",
        leave_type="sabbatical",
        start_date=date(2027, 1, 1),
        end_date=date(2027, 6, 30),
        duration_days=180,
        justification="Research fellowship abroad",
    )
    assert leave.leave_type == "sabbatical"


def test_fr_054_require_leave_type(auth_client_factory):
    """TEST-FR-054 [HR-AFR-036]: Verify HR-EIS requires each leave request to specify leave type."""
    EmployeeServiceRecord.objects.create(
        user_id=197,
        employee_id="EMP0197",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 5},
    )
    client, _ = auth_client_factory(user_id=197, role="faculty")
    resp = client.post(
        "/api/v1/hreis/leaves/",
        {
            "start_date": "2026-12-01",
            "end_date": "2026-12-02",
            "duration_days": 2,
            "justification": "Missing leave type",
        },
        format="json",
    )
    assert resp.status_code == 400


def test_fr_055_require_duration_and_dates(auth_client_factory):
    """TEST-FR-055 [HR-AFR-037]: Verify HR-EIS requires each leave request to specify duration / dates."""
    EmployeeServiceRecord.objects.create(
        user_id=198,
        employee_id="EMP0198",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 5},
    )
    client, _ = auth_client_factory(user_id=198, role="faculty")
    resp = client.post(
        "/api/v1/hreis/leaves/",
        {"leave_type": "casual", "justification": "Missing dates"},
        format="json",
    )
    assert resp.status_code == 400


def test_fr_056_require_justification(auth_client_factory):
    """TEST-FR-056 [HR-AFR-038]: Verify HR-EIS requires each leave request to specify justification."""
    EmployeeServiceRecord.objects.create(
        user_id=199,
        employee_id="EMP0199",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 5},
    )
    client, _ = auth_client_factory(user_id=199, role="faculty")
    resp = client.post(
        "/api/v1/hreis/leaves/",
        {
            "leave_type": "casual",
            "start_date": "2026-12-01",
            "end_date": "2026-12-02",
            "duration_days": 2,
            "justification": "",
        },
        format="json",
    )
    assert resp.status_code == 400


def test_fr_057_validate_leave_balance_boundary():
    """TEST-FR-057 [HR-AFR-039]: Verify HR-EIS validates employee leave balance before accepting submission."""
    from core.api.exceptions import BadRequestError

    EmployeeServiceRecord.objects.create(
        user_id=200,
        employee_id="EMP0200",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 2},
    )
    with pytest.raises(BadRequestError):
        submit_leave_request(
            user_id=200,
            username="u200",
            leave_type="casual",
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 5),
            duration_days=5,
            justification="Too many days requested",
        )


def test_fr_058_validate_leave_eligibility():
    """TEST-FR-058 [HR-AFR-040]: Verify HR-EIS validates employee leave eligibility before accepting submission."""
    from core.api.exceptions import BadRequestError

    EmployeeServiceRecord.objects.create(
        user_id=202,
        employee_id="EMP0202",
        department="Administration",
        designation="Junior Assistant",
        category="staff",
        leave_balances={"casual": 8, "vacation": 0},
    )
    # Staff is not eligible for faculty Vacation leave
    with pytest.raises(BadRequestError):
        submit_leave_request(
            user_id=202,
            username="u202",
            leave_type="vacation",
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 5),
            duration_days=5,
            justification="Staff attempting vacation leave",
        )


def test_fr_059_route_leave_hierarchy():
    """TEST-FR-059 [HR-AFR-041]: Verify HR-EIS routes leave requests through a predefined approval hierarchy."""
    EmployeeServiceRecord.objects.create(
        user_id=203,
        employee_id="EMP0203",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 5},
    )
    leave = submit_leave_request(
        user_id=203,
        username="u203",
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 2),
        duration_days=2,
        justification="Route check",
    )
    assert leave.current_authority_role == "hod"


def test_fr_060_automatic_balance_update_on_approval():
    """TEST-FR-060 [HR-AFR-042]: Verify HR-EIS updates leave balances automatically when leave is approved."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=204,
        employee_id="EMP0204",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 8},
    )
    leave = submit_leave_request(
        user_id=204,
        username="u204",
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 2),
        duration_days=2,
        justification="Trip",
    )
    decide_leave_request(
        leave_id=leave.id,
        outcome="approved",
        remarks="Approved",
        actor_id=302,
        actor_username="hod",
        actor_role="hod",
    )
    rec.refresh_from_db()
    assert rec.leave_balances["casual"] == 6


def test_fr_061_permanent_leave_logging():
    """TEST-FR-061 [HR-AFR-043]: Verify HR-EIS permanently logs all leave transactions."""
    EmployeeServiceRecord.objects.create(
        user_id=205,
        employee_id="EMP0205",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 5},
    )
    leave = submit_leave_request(
        user_id=205,
        username="u205",
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 1),
        duration_days=1,
        justification="Audit check",
    )
    logs = HrAuditLog.objects.filter(entity_type="leave_request", entity_id=str(leave.id))
    assert logs.exists()
    assert logs.first().action == "submit_leave_request"
