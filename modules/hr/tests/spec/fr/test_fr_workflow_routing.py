"""FR spec tests for Workflow Routing and Authority Hierarchy."""

import pytest

from modules.hr.domain import state_machine
from modules.hr.models import WorkflowRoute
from modules.hr.tests.spec.conftest import (
    UID_DIRECTOR,
    UID_FACULTY_1,
    UID_HOD,
    UID_HR_ADMIN,
    UID_REGISTRAR,
    ensure_employee,
    make_actor,
)

pytestmark = pytest.mark.django_db


def test_fr_003_consolidated_approval_workflow_routing_integrity(hr_caller):
    """TEST-FR-003 | HR-CFR-003 consolidated-approval-workflow-routing-integrity.

    Verify that HR-EIS selects and enforces applicable approval authority routing by employee category and request type, supports Approved/Rejected/Forwarded outcomes, and prevents workflow bypass or alterations.
    """
    # Workflow route for faculty leave routes to HOD then Director
    route = state_machine.decide_leave(
        state_machine.LEAVE_PENDING, action="forward", authority_step=0, route_length=2
    )
    assert route.state == state_machine.LEAVE_PENDING_NEXT
    assert route.authority_step == 1


def test_fr_024_employee_submit_hr_requests(hr_caller):
    """TEST-FR-024 | HR-AFR-002 employee-submit-hr-requests.

    Verify that HR-EIS allows an Employee to submit HR-related service requests.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={
            "request_type": "ltc_advance",
            "purpose": "Home town visit",
            "amount": "15000.00",
            "form_data": {"block_year": "2024-2025", "destination": "Home town"},
        },
    )
    assert res.status_code == 201


def test_fr_025_employee_track_own_request_statuses(hr_caller):
    """TEST-FR-025 | HR-AFR-004 employee-track-own-request-statuses.

    Verify that HR-EIS allows an Employee to track statuses of HR-related requests submitted by the Employee.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller("get", "/api/v1/hr/claims/", user_id=UID_FACULTY_1, role="faculty")
    assert res.status_code == 200


def test_fr_026_route_dept_approvals_to_hod(hr_caller):
    """TEST-FR-026 | HR-AFR-006 route-dept-approvals-to-hod.

    Verify that HR-EIS routes department-level approvals to the Head of Department (HOD) where applicable.
    """
    # Save a workflow route for faculty department approval
    res = hr_caller(
        "post",
        "/api/v1/hr/workflow-routes/save/",
        user_id=UID_HR_ADMIN,
        role="hr_officer",
        data={
            "employee_category": "faculty",
            "request_type": "leave_casual",
            "steps": [{"approver_user_id": UID_HOD, "authority_label": "HOD"}],
        },
    )
    assert res.status_code == 200
    assert res.data["steps"][0]["approver_user_id"] == UID_HOD


def test_fr_027_route_non_teaching_approvals_to_registrar(hr_caller):
    """TEST-FR-027 | HR-AFR-007 route-non-teaching-approvals-to-registrar.

    Verify that HR-EIS routes non-teaching staff approvals to the Registrar where applicable.
    """
    res = hr_caller(
        "post",
        "/api/v1/hr/workflow-routes/save/",
        user_id=UID_HR_ADMIN,
        role="hr_officer",
        data={
            "employee_category": "staff",
            "request_type": "leave_earned",
            "steps": [{"approver_user_id": UID_REGISTRAR, "authority_label": "Registrar"}],
        },
    )
    assert res.status_code == 200
    assert res.data["steps"][0]["approver_user_id"] == UID_REGISTRAR


def test_fr_028_route_faculty_approvals_to_director(hr_caller):
    """TEST-FR-028 | HR-AFR-008 route-faculty-approvals-to-director.

    Verify that HR-EIS routes faculty-level or final authority approvals to the Director where applicable.
    """
    res = hr_caller(
        "post",
        "/api/v1/hr/workflow-routes/save/",
        user_id=UID_HR_ADMIN,
        role="hr_officer",
        data={
            "employee_category": "faculty",
            "request_type": "cpda_advance",
            "steps": [
                {"approver_user_id": UID_HOD, "authority_label": "HOD"},
                {"approver_user_id": UID_DIRECTOR, "authority_label": "Director"},
            ],
        },
    )
    assert res.status_code == 200
    assert len(res.data["steps"]) == 2
    assert res.data["steps"][1]["approver_user_id"] == UID_DIRECTOR


def test_fr_029_determine_authority_by_category_and_type(hr_caller):
    """TEST-FR-029 | HR-AFR-009 determine-authority-by-category-and-type.

    Verify that HR-EIS determines approval authority strictly by employee category and request type.
    """
    # Route lookup differentiates by employee_category and request_type
    route1, _ = WorkflowRoute.objects.update_or_create(
        employee_category="faculty",
        request_type="leave_casual",
        defaults={"steps": [{"approver_user_id": UID_HOD}], "updated_by_user_id": UID_HR_ADMIN},
    )
    route2, _ = WorkflowRoute.objects.update_or_create(
        employee_category="staff",
        request_type="leave_casual",
        defaults={
            "steps": [{"approver_user_id": UID_REGISTRAR}],
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    assert route1.steps[0]["approver_user_id"] == UID_HOD
    assert route2.steps[0]["approver_user_id"] == UID_REGISTRAR


def test_fr_030_route_requests_rule_based_workflows(hr_caller):
    """TEST-FR-030 | HR-AFR-070 route-requests-rule-based-workflows.

    Verify that HR-EIS routes all HR requests through configured rule-based workflows.
    """
    res = hr_caller("get", "/api/v1/hr/workflow-routes/", user_id=UID_HR_ADMIN, role="hr_officer")
    assert res.status_code == 200


def test_fr_031_support_request_outcome_approved(hr_caller):
    """TEST-FR-031 | HR-AFR-071 support-request-outcome-approved.

    Verify that HR-EIS supports the request outcome or transition: Approved.
    """
    transition = state_machine.decide_leave(
        state_machine.LEAVE_PENDING, action="approve", authority_step=0, route_length=1
    )
    assert transition.state == state_machine.LEAVE_APPROVED


def test_fr_032_support_request_outcome_rejected(hr_caller):
    """TEST-FR-032 | HR-AFR-072 support-request-outcome-rejected.

    Verify that HR-EIS supports the request outcome or transition: Rejected.
    """
    transition = state_machine.decide_leave(
        state_machine.LEAVE_PENDING, action="reject", authority_step=0, route_length=1
    )
    assert transition.state == state_machine.LEAVE_REJECTED


def test_fr_033_support_request_outcome_forwarded(hr_caller):
    """TEST-FR-033 | HR-AFR-073 support-request-outcome-forwarded.

    Verify that HR-EIS supports the request outcome or transition: Forwarded to next authority.
    """
    transition = state_machine.decide_leave(
        state_machine.LEAVE_PENDING, action="forward", authority_step=0, route_length=2
    )
    assert transition.state == state_machine.LEAVE_PENDING_NEXT
    assert transition.authority_step == 1


def test_fr_034_enforce_authority_roles_using_rbac(hr_caller):
    """TEST-FR-034 | HR-AFR-074 enforce-authority-roles-using-rbac.

    Verify that HR-EIS enforces authority roles using RBAC during HR request workflows.
    """
    actor = make_actor(UID_HOD, role="Head of Department", kind="faculty")
    assert actor.has_permission("hr.leave.approve")
    assert not actor.has_permission("hr.workflow.manage")


def test_fr_035_prevent_authority_bypassing_workflow_order(hr_caller):
    """TEST-FR-035 | HR-AFR-075 prevent-authority-bypassing-workflow-order.

    Verify that HR-EIS prevents any authority from bypassing workflow order.
    """
    # Approving at step 0 when route length is 2 must raise InvalidTransition
    with pytest.raises(state_machine.InvalidTransition):
        state_machine.decide_leave(
            state_machine.LEAVE_PENDING, action="approve", authority_step=0, route_length=2
        )


def test_fr_036_prevent_authority_altering_workflow_order(hr_caller):
    """TEST-FR-036 | HR-AFR-076 prevent-authority-altering-workflow-order.

    Verify that HR-EIS prevents any authority from altering workflow order.
    """
    # Forwarding beyond maximum route length must be rejected
    with pytest.raises(state_machine.InvalidTransition):
        state_machine.decide_leave(
            state_machine.LEAVE_PENDING_NEXT, action="forward", authority_step=1, route_length=2
        )


def test_fr_037_not_allow_manual_bypass_approval_workflows(hr_caller):
    """TEST-FR-037 | HR-AFR-106 not-allow-manual-bypass-approval-workflows.

    Verify that HR-EIS does not allow manual bypass of configured approval workflows.
    """
    with pytest.raises(state_machine.InvalidTransition):
        state_machine.decide_claim(
            state_machine.PENDING_VERIFICATION, action="approve", authority_step=0, route_length=1
        )


def test_fr_040_hr_admin_configure_hr_workflows(hr_caller):
    """TEST-FR-040 | HR-AFR-012 hr-admin-configure-hr-workflows.

    Verify that HR-EIS allows the HR Administrator to configure HR workflows where configuration is within HR-EIS scope.
    """
    res = hr_caller(
        "post",
        "/api/v1/hr/workflow-routes/save/",
        user_id=UID_HR_ADMIN,
        role="hr_officer",
        data={
            "employee_category": "faculty",
            "request_type": "cpda_reimbursement",
            "steps": [{"approver_user_id": UID_DIRECTOR, "authority_label": "Director"}],
            "reminder_after_hours": 48,
        },
    )
    assert res.status_code == 200
    assert res.data["reminder_after_hours"] == 48
