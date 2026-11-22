"""Access-scoped selector and public employment-contract tests."""

import pytest

from conftest import make_session
from fusion_auth.principal import Principal
from modules.hr import contracts
from modules.hr.models import (
    Appraisal,
    AppraisalWindow,
    AuditEvent,
    Claim,
    EmployeeRecord,
    HRNotification,
    LeaveBalance,
    LeaveRequest,
    WorkflowRoute,
)
from modules.hr.selectors import (
    appraisals,
    audit,
    claims,
    configuration,
    employees,
    leaves,
    notifications,
)

pytestmark = pytest.mark.django_db


def principal(user_id=1001, *permissions):
    return Principal.from_session(
        make_session(
            user_id=user_id,
            kind="staff",
            modules=("hr",),
            permissions=permissions,
        )
    )


@pytest.fixture
def records():
    first = EmployeeRecord.objects.create(
        user_id=1001,
        employee_category="staff",
        department="Research",
        designation="Officer",
        appointment_type="Permanent",
        appointment_start_date="2020-01-02",
        appointment_details={"grade": "A"},
        created_by_user_id=7,
        updated_by_user_id=7,
    )
    second = EmployeeRecord.objects.create(
        user_id=1002,
        employee_category="faculty",
        department="Physics",
        designation="Professor",
        created_by_user_id=7,
        updated_by_user_id=7,
    )
    return first, second


def test_employee_and_leave_selectors_apply_self_authority_and_empty_scopes(records):
    first, second = records
    own_request = LeaveRequest.objects.create(
        employee=first,
        leave_type="casual",
        duration_days="1.00",
        justification="Family",
        route_snapshot=[{"approver_user_id": 88}],
        current_authority_user_id=88,
        submitted_by_user_id=first.user_id,
    )
    other_request = LeaveRequest.objects.create(
        employee=second,
        leave_type="earned",
        duration_days="2.00",
        justification="Travel",
        route_snapshot=[{"approver_user_id": 99}],
        current_authority_user_id=99,
        submitted_by_user_id=second.user_id,
    )
    assert set(
        employees.visible_employee_records(principal()).values_list("user_id", flat=True)
    ) == {first.user_id}
    assert employees.visible_employee_records(principal(7, "hr.employee.view")).count() == 2
    assert employees.employee_record_for_user(user_id=999, principal=principal()) is None
    employee_reader = principal(1001, "hr.leave.view_self")
    assert set(leaves.visible_leave_requests(employee_reader).values_list("pk", flat=True)) == {
        own_request.pk
    }
    assert set(
        leaves.visible_leave_requests(principal(88, "hr.leave.approve")).values_list(
            "pk", flat=True
        )
    ) == {own_request.pk}
    assert not leaves.visible_leave_requests(principal(55)).exists()
    assert (
        leaves.leave_request_for_user(request_id=own_request.pk, principal=employee_reader).pk
        == own_request.pk
    )
    assert (
        leaves.leave_request_for_user(request_id=other_request.pk, principal=employee_reader)
        is None
    )
    LeaveBalance.objects.create(
        employee=first,
        leave_type="casual",
        available_days="3.00",
        is_eligible=True,
        updated_by_user_id=7,
    )
    assert list(
        leaves.leave_balances_for_employee(first.pk).values_list("leave_type", flat=True)
    ) == ["casual"]
    assert leaves.managed_leave_balances().count() == 1


def test_appraisal_selectors_scope_self_reviewer_and_assigner(records):
    mine, other = records
    own = Appraisal.objects.create(employee_user_id=mine.user_id, period="2025", form_data={})
    assigned = Appraisal.objects.create(
        employee_user_id=other.user_id,
        period="2025",
        form_data={},
        reviewer_user_ids=[88],
        current_reviewer_user_id=88,
    )
    self_reader = principal(1001, "hr.appraisal.view_self")
    assert set(appraisals.visible_appraisals(self_reader).values_list("pk", flat=True)) == {own.pk}
    assert set(
        appraisals.visible_appraisals(principal(88, "hr.appraisal.review")).values_list(
            "pk", flat=True
        )
    ) == {assigned.pk}
    assert appraisals.visible_appraisals(principal(55)).count() == 0
    assert appraisals.visible_appraisals(principal(7, "hr.appraisal.assign")).count() == 2


def test_claim_selector_combines_scopes_and_returns_none_for_invisible_claims():
    own = Claim.objects.create(
        employee_user_id=1001,
        employee_category="staff",
        request_type="ltc_advance",
        form_data={"destination": "Delhi"},
    )
    pending = Claim.objects.create(
        employee_user_id=1002,
        employee_category="staff",
        request_type="ltc_advance",
        form_data={"destination": "Pune"},
        status="pending_verification",
    )
    finance = Claim.objects.create(
        employee_user_id=1003,
        employee_category="staff",
        request_type="ltc_advance",
        form_data={"destination": "Jaipur"},
        status="approved",
    )
    scoped = principal(1001, "hr.claim.view_self", "hr.claim.verify", "hr.claim.manage")
    assert set(claims.visible_claims(scoped).values_list("pk", flat=True)) == {
        own.pk,
        pending.pk,
        finance.pk,
    }
    assert claims.claim_for_user(claim_id=own.pk, principal=scoped).pk == own.pk
    assert claims.claim_for_user(claim_id=finance.pk, principal=principal(55)) is None


def test_configuration_audit_notification_and_public_contract_selectors(records):
    first, _ = records
    route = WorkflowRoute.objects.create(
        employee_category="staff",
        request_type="ltc_advance",
        steps=[{"approver_user_id": 88}],
        updated_by_user_id=7,
    )
    window = AppraisalWindow.objects.create(
        period="2026",
        opens_at="2026-01-01T00:00:00Z",
        closes_at="2026-12-31T00:00:00Z",
        updated_by_user_id=7,
    )
    event = AuditEvent.objects.create(
        entity_type="employee", entity_id=first.pk, actor_user_id=7, action="employee.created"
    )
    notice = HRNotification.objects.create(
        recipient_user_id=1001,
        topic="hr.notice",
        dedupe_key="notice-1",
        subject="Schedule",
        body="Review",
    )
    assert list(configuration.workflow_routes()) == [route]
    assert list(configuration.appraisal_windows()) == [window]
    assert list(audit.audit_events()) == [event]
    assert list(notifications.notifications_for(principal())) == [notice]

    assert contracts.get_employments([]) == {}
    mapping = contracts.get_employments([1001, None, 9999])
    assert set(mapping) == {1001}
    assert mapping[1001].appointment_start_date == "2020-01-02"
    assert mapping[1001].appointment_end_date is None
    assert mapping[1001].appointment_details == {"grade": "A"}


def test_hr_task_queue_and_schedule_registration():
    from modules.hr.schedule import BEAT_SCHEDULE, TASK_ROUTES

    assert TASK_ROUTES["hr.deliver_notifications"]["queue"] == "notifications"
    assert TASK_ROUTES["hr.generate_pending_reminders"]["queue"] == "default"
    assert BEAT_SCHEDULE["hr.deliver-notifications"]["task"] == "hr.deliver_notifications"
    assert BEAT_SCHEDULE["hr.generate-pending-reminders"]["task"] == "hr.generate_pending_reminders"
