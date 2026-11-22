from datetime import date

import pytest
from rest_framework import status

from core.api.exceptions import BadRequestError
from modules.hreis.models import EmployeeServiceRecord, HrAuditLog
from modules.hreis.services.leaves import decide_leave_request, submit_leave_request

pytestmark = pytest.mark.django_db


def test_br_011_leave_required_fields_permitted():
    """TEST-BR-011 [BR-HR-007 Permitted]: Verify leave request with required fields is accepted."""
    EmployeeServiceRecord.objects.create(
        user_id=320,
        employee_id="EMP0320",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 5},
    )
    leave = submit_leave_request(
        user_id=320,
        username="u320",
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 2),
        duration_days=2,
        justification="Personal errand",
    )
    assert leave.id is not None
    assert leave.status == "pending"


def test_br_012_leave_missing_justification_prohibited(auth_client_factory):
    """TEST-BR-012 [BR-HR-007 Prohibited]: Verify leave request missing justification is rejected."""
    EmployeeServiceRecord.objects.create(
        user_id=321,
        employee_id="EMP0321",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 5},
    )
    client, _ = auth_client_factory(user_id=321, role="faculty")
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
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_br_013_leave_balance_boundary_permitted():
    """TEST-BR-013 [BR-HR-008 Permitted Threshold]: Verify leave request within available balance is accepted (duration <= balance)."""
    EmployeeServiceRecord.objects.create(
        user_id=322,
        employee_id="EMP0322",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 5},
    )
    leave = submit_leave_request(
        user_id=322,
        username="u322",
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 5),
        duration_days=5,
        justification="Exact balance leave",
    )
    assert leave.duration_days == 5


def test_br_014_leave_balance_boundary_prohibited():
    """TEST-BR-014 [BR-HR-008 Prohibited Threshold]: Verify leave request exceeding balance is rejected (duration > balance)."""
    EmployeeServiceRecord.objects.create(
        user_id=323,
        employee_id="EMP0323",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 5},
    )
    with pytest.raises(BadRequestError):
        submit_leave_request(
            user_id=323,
            username="u323",
            leave_type="casual",
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 6),
            duration_days=6,
            justification="Exceeding balance",
        )


def test_br_015_ineligible_leave_type_prohibited():
    """TEST-BR-015 [BR-HR-008 Ineligible Leave Type]: Verify staff employee cannot apply for faculty-specific leave."""
    EmployeeServiceRecord.objects.create(
        user_id=324,
        employee_id="EMP0324",
        department="Administration",
        designation="Junior Assistant",
        category="staff",
        leave_balances={"casual": 10, "vacation": 0},
    )
    with pytest.raises(BadRequestError):
        submit_leave_request(
            user_id=324,
            username="u324",
            leave_type="vacation",
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 5),
            duration_days=5,
            justification="Staff applying vacation",
        )


def test_br_016_approval_authority_routing():
    """TEST-BR-016 [BR-HR-009 Permitted]: Verify leave request is routed to configured initial authority (HOD)."""
    EmployeeServiceRecord.objects.create(
        user_id=325,
        employee_id="EMP0325",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 5},
    )
    leave = submit_leave_request(
        user_id=325,
        username="u325",
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 2),
        duration_days=2,
        justification="Route test",
    )
    assert leave.current_authority_role == "hod"


def test_br_017_approved_leave_balance_auto_deduction():
    """TEST-BR-017 [BR-HR-010 Auto Deduction]: Verify approving leave deducts exact duration from balance."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=326,
        employee_id="EMP0326",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 10},
    )
    leave = submit_leave_request(
        user_id=326,
        username="u326",
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 3),
        duration_days=3,
        justification="Deduction check",
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
    assert rec.leave_balances["casual"] == 7


def test_br_018_leave_transaction_audit_logged():
    """TEST-BR-018 [BR-HR-011 Audit]: Verify all leave lifecycle transactions are permanently logged."""
    EmployeeServiceRecord.objects.create(
        user_id=327,
        employee_id="EMP0327",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 5},
    )
    leave = submit_leave_request(
        user_id=327,
        username="u327",
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 1),
        duration_days=1,
        justification="Audit check",
    )
    logs = HrAuditLog.objects.filter(entity_type="leave_request", entity_id=str(leave.id))
    assert logs.exists()


def test_br_053_supported_leave_types():
    """TEST-BR-053 [BR-HR-034 Supported Types]: Verify HR-EIS supports Casual, Restricted, Medical, Earned, Vacation, and Sabbatical."""
    types = ["casual", "restricted", "medical", "earned", "vacation", "sabbatical"]
    for idx, t in enumerate(types):
        user_id = 350 + idx
        EmployeeServiceRecord.objects.create(
            user_id=user_id,
            employee_id=f"EMP{user_id}",
            department="CSE",
            designation="Professor",
            category="faculty",
            leave_balances={t: 50},
        )
        leave = submit_leave_request(
            user_id=user_id,
            username=f"u{user_id}",
            leave_type=t,
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 2),
            duration_days=2,
            justification=f"Testing {t}",
        )
        assert leave.leave_type == t


def test_br_054_unsupported_leave_type_prohibited():
    """TEST-BR-054 [BR-HR-034 Unsupported Type]: Verify unsupported leave type is rejected."""
    EmployeeServiceRecord.objects.create(
        user_id=360,
        employee_id="EMP0360",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 5},
    )
    with pytest.raises(BadRequestError):
        submit_leave_request(
            user_id=360,
            username="u360",
            leave_type="study_leave_abroad",
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 2),
            duration_days=2,
            justification="Unsupported type",
        )
