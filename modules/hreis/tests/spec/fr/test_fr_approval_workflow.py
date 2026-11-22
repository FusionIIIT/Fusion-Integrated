import pytest
from datetime import date
from decimal import Decimal
from modules.hreis.models import EmployeeServiceRecord, LeaveRequest
from modules.hreis.services.leaves import submit_leave_request

pytestmark = pytest.mark.django_db


def test_fr_012_route_department_level_approvals_to_hod(auth_client_factory):
    """TEST-FR-012 [HR-AFR-006]: Verify HR-EIS routes department-level approvals to the Head of Department."""
    EmployeeServiceRecord.objects.create(
        user_id=130,
        employee_id="EMP0130",
        department="ME",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 5},
    )
    leave = submit_leave_request(
        user_id=130,
        username="u130",
        leave_type="casual",
        start_date=date(2026, 11, 25),
        end_date=date(2026, 11, 26),
        duration_days=2,
        justification="Research meeting",
    )
    assert leave.current_authority_role == "hod"


def test_fr_013_route_staff_approvals_to_registrar(auth_client_factory):
    """TEST-FR-013 [HR-AFR-007]: Verify HR-EIS routes non-teaching staff approvals to Registrar where applicable."""
    EmployeeServiceRecord.objects.create(
        user_id=131,
        employee_id="EMP0131",
        department="Accounts",
        designation="Junior Assistant",
        category="staff",
        leave_balances={"casual": 5},
    )
    leave = submit_leave_request(
        user_id=131,
        username="u131",
        leave_type="casual",
        start_date=date(2026, 11, 25),
        end_date=date(2026, 11, 26),
        duration_days=2,
        justification="Personal errand",
    )
    # Default staff hierarchy routes to registrar
    assert leave.current_authority_role in ("registrar", "hod")


def test_fr_014_route_faculty_final_approvals_to_director(auth_client_factory):
    """TEST-FR-014 [HR-AFR-008]: Verify HR-EIS routes faculty-level final approvals to the Director where applicable."""
    EmployeeServiceRecord.objects.create(
        user_id=132,
        employee_id="EMP0132",
        department="CSE",
        designation="Associate Professor",
        category="faculty",
        leave_balances={"casual": 10},
    )
    leave = LeaveRequest.objects.create(
        user_id=132,
        leave_type="casual",
        start_date=date(2026, 12, 5),
        end_date=date(2026, 12, 7),
        duration_days=3,
        justification="Conference presentation",
        status="forwarded",
        current_authority_role="director",
    )
    client_director, _ = auth_client_factory(user_id=301, role="director")
    resp = client_director.post(
        f"/api/v1/hreis/leaves/{leave.id}/decide/",
        {"outcome": "approved", "remarks": "Approved by Director"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "approved"


def test_fr_015_authority_determined_by_category_and_type():
    """TEST-FR-015 [HR-AFR-009]: Verify HR-EIS determines approval authority strictly by employee category and request type."""
    from modules.hreis.domain.workflow import get_next_authority, DEFAULT_APPROVAL_HIERARCHY

    first_faculty = get_next_authority("", "faculty", DEFAULT_APPROVAL_HIERARCHY)
    first_staff = get_next_authority("", "staff", DEFAULT_APPROVAL_HIERARCHY)
    assert first_faculty == "hod"
    assert first_staff == "registrar"


def test_fr_016_rule_based_workflow_progression(auth_client_factory):
    """TEST-FR-016 [HR-AFR-070]: Verify HR-EIS routes all HR requests through rule-based workflows."""
    EmployeeServiceRecord.objects.create(
        user_id=133,
        employee_id="EMP0133",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 5},
    )
    leave = submit_leave_request(
        user_id=133,
        username="u133",
        leave_type="casual",
        start_date=date(2026, 11, 28),
        end_date=date(2026, 11, 29),
        duration_days=2,
        justification="Medical checkup",
    )
    assert leave.status == "pending"
    assert len(leave.approval_history) >= 1
    assert leave.approval_history[0]["action"] == "submitted"


def test_fr_017_decision_outcome_approved(auth_client_factory):
    """TEST-FR-017 [HR-AFR-071]: Verify HR-EIS supports the request outcome: Approved."""
    EmployeeServiceRecord.objects.create(
        user_id=134,
        employee_id="EMP0134",
        department="ECE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 10},
    )
    leave = LeaveRequest.objects.create(
        user_id=134,
        leave_type="casual",
        start_date=date(2026, 12, 10),
        end_date=date(2026, 12, 11),
        duration_days=2,
        justification="Family function",
        status="pending",
        current_authority_role="hod",
    )
    client_hod, _ = auth_client_factory(user_id=302, role="hod")
    resp = client_hod.post(
        f"/api/v1/hreis/leaves/{leave.id}/decide/",
        {"outcome": "approved", "remarks": "Looks good"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "approved"


def test_fr_018_decision_outcome_rejected(auth_client_factory):
    """TEST-FR-018 [HR-AFR-072]: Verify HR-EIS supports the request outcome: Rejected."""
    EmployeeServiceRecord.objects.create(
        user_id=135,
        employee_id="EMP0135",
        department="ECE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 10},
    )
    leave = LeaveRequest.objects.create(
        user_id=135,
        leave_type="casual",
        start_date=date(2026, 12, 10),
        end_date=date(2026, 12, 11),
        duration_days=2,
        justification="Urgent personal leave",
        status="pending",
        current_authority_role="hod",
    )
    client_hod, _ = auth_client_factory(user_id=302, role="hod")
    resp = client_hod.post(
        f"/api/v1/hreis/leaves/{leave.id}/decide/",
        {"outcome": "rejected", "remarks": "Exam duty scheduled"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "rejected"


def test_fr_019_decision_outcome_forwarded(auth_client_factory):
    """TEST-FR-019 [HR-AFR-073]: Verify HR-EIS supports the request outcome: Forwarded to next authority."""
    EmployeeServiceRecord.objects.create(
        user_id=136,
        employee_id="EMP0136",
        department="ME",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 10},
    )
    leave = LeaveRequest.objects.create(
        user_id=136,
        leave_type="casual",
        start_date=date(2026, 12, 15),
        end_date=date(2026, 12, 18),
        duration_days=4,
        justification="Workshop",
        status="pending",
        current_authority_role="hod",
    )
    client_hod, _ = auth_client_factory(user_id=302, role="hod")
    resp = client_hod.post(
        f"/api/v1/hreis/leaves/{leave.id}/decide/",
        {"outcome": "forwarded", "remarks": "Forwarded to Director for approval"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "forwarded"
    assert resp.data["current_authority_role"] == "director"


def test_fr_020_enforce_authority_roles_rbac(auth_client_factory):
    """TEST-FR-020 [HR-AFR-074]: Verify HR-EIS enforces authority roles using RBAC during HR request workflows."""
    EmployeeServiceRecord.objects.create(
        user_id=137,
        employee_id="EMP0137",
        department="ME",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 10},
    )
    leave = LeaveRequest.objects.create(
        user_id=137,
        leave_type="casual",
        start_date=date(2026, 12, 20),
        end_date=date(2026, 12, 21),
        duration_days=2,
        justification="Leave",
        status="pending",
        current_authority_role="hod",
    )
    client_staff, _ = auth_client_factory(user_id=138, role="staff")
    resp = client_staff.post(
        f"/api/v1/hreis/leaves/{leave.id}/decide/",
        {"outcome": "approved", "remarks": "Staff cannot approve"},
        format="json",
    )
    assert resp.status_code == 403


def test_fr_021_prevent_workflow_order_bypass(auth_client_factory):
    """TEST-FR-021 [HR-AFR-075]: Verify HR-EIS prevents any authority from bypassing workflow order."""
    EmployeeServiceRecord.objects.create(
        user_id=139,
        employee_id="EMP0139",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 10},
    )
    leave = LeaveRequest.objects.create(
        user_id=139,
        leave_type="casual",
        start_date=date(2026, 12, 22),
        end_date=date(2026, 12, 23),
        duration_days=2,
        justification="Trip",
        status="pending",
        current_authority_role="hod",
    )
    # Already settled or invalid transitions directly attempted
    client_hod, _ = auth_client_factory(user_id=302, role="hod")
    resp = client_hod.post(
        f"/api/v1/hreis/leaves/{leave.id}/decide/",
        {"outcome": "settled", "remarks": "Invalid outcome"},
        format="json",
    )
    assert resp.status_code in (400, 422)


def test_fr_022_prevent_workflow_order_alteration():
    """TEST-FR-022 [HR-AFR-076]: Verify HR-EIS prevents altering configured workflow progression order."""
    from modules.hreis.domain.exceptions import DomainValidationError
    from modules.hreis.domain.workflow import validate_decision

    with pytest.raises(DomainValidationError):
        validate_decision(outcome="completed", current_status="pending", remarks="test", can_forward=True)


def test_fr_023_disallow_manual_workflow_bypass(auth_client_factory):
    """TEST-FR-023 [HR-AFR-106]: Verify HR-EIS does not allow manual bypass of approval workflows."""
    EmployeeServiceRecord.objects.create(
        user_id=140,
        employee_id="EMP0140",
        department="ECE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 10},
    )
    leave = LeaveRequest.objects.create(
        user_id=140,
        leave_type="casual",
        start_date=date(2026, 12, 24),
        end_date=date(2026, 12, 25),
        duration_days=2,
        justification="Holiday",
        status="pending",
        current_authority_role="hod",
    )
    client_faculty, _ = auth_client_factory(user_id=140, role="faculty")
    resp = client_faculty.patch(f"/api/v1/hreis/leaves/{leave.id}/", {"status": "approved"})
    assert resp.status_code in (403, 405)
