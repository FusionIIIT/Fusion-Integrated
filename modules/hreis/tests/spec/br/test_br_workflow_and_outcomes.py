from datetime import date

import pytest

from modules.hreis.models import EmployeeServiceRecord
from modules.hreis.services.leaves import decide_leave_request, submit_leave_request

pytestmark = pytest.mark.django_db


def test_br_036_approval_outcome_approved():
    """TEST-BR-036 [BR-HR-023 Approved Outcome]: Verify HR-EIS supports Approved outcome for routed HR request."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=401,
        employee_id="EMP0401",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 5},
    )
    leave = submit_leave_request(
        user_id=401,
        username="u401",
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 1),
        duration_days=1,
        justification="Personal",
    )
    decided = decide_leave_request(
        leave_id=leave.id,
        outcome="approved",
        remarks="Approved",
        actor_id=301,
        actor_username="hod",
        actor_role="hod",
    )
    assert decided.status == "approved"


def test_br_037_approval_outcome_rejected():
    """TEST-BR-037 [BR-HR-023 Rejected Outcome]: Verify HR-EIS supports Rejected outcome ending approval path."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=402,
        employee_id="EMP0402",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 5},
    )
    leave = submit_leave_request(
        user_id=402,
        username="u402",
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 1),
        duration_days=1,
        justification="Personal",
    )
    decided = decide_leave_request(
        leave_id=leave.id,
        outcome="rejected",
        remarks="Rejected",
        actor_id=301,
        actor_username="hod",
        actor_role="hod",
    )
    assert decided.status == "rejected"


def test_br_038_approval_outcome_forwarded():
    """TEST-BR-038 [BR-HR-023 Forwarded Outcome]: Verify HR-EIS supports Forwarded outcome advancing request to next authority."""
    EmployeeServiceRecord.objects.create(
        user_id=403,
        employee_id="EMP0403",
        department="CSE",
        designation="Professor",
        category="faculty",
        leave_balances={"sabbatical": 180},
    )
    leave = submit_leave_request(
        user_id=403,
        username="u403",
        leave_type="sabbatical",
        start_date=date(2026, 12, 1),
        end_date=date(2027, 2, 28),
        duration_days=90,
        justification="Sabbatical research",
    )
    decided = decide_leave_request(
        leave_id=leave.id,
        outcome="forwarded",
        remarks="Forwarding to Director",
        actor_id=301,
        actor_username="hod",
        actor_role="hod",
    )
    assert decided.status == "forwarded"
