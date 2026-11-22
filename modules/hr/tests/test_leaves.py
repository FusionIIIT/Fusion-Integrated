from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from conftest import make_session
from core.api.exceptions import ConflictError, NotFoundError
from fusion_auth.principal import Principal
from modules.hr.api.serializers import LeaveRequestCreateSerializer
from modules.hr.domain import state_machine
from modules.hr.models import (
    LEAVE_TYPES,
    AuditEvent,
    EmployeeRecord,
    HRNotification,
    LeaveBalance,
    LeaveLedgerEntry,
    LeaveRequest,
    WorkflowRoute,
)
from modules.hr.selectors.leaves import visible_leave_requests
from modules.hr.services import configuration, leaves
from modules.hr.tasks import generate_pending_reminders


def actor(user_id: int, *permissions: str, modules=("hr",)) -> Principal:
    return Principal.from_session(
        make_session(
            user_id=user_id,
            kind="staff",
            permissions=permissions,
            modules=modules,
        )
    )


@pytest.mark.parametrize(
    ("state", "action", "step", "length", "expected"),
    [
        (state_machine.LEAVE_PENDING, "approve", 0, 1, "approved"),
        (state_machine.LEAVE_PENDING, "reject", 0, 2, "rejected"),
        (state_machine.LEAVE_PENDING, "forward", 0, 2, "pending_next_authority"),
        (state_machine.LEAVE_PENDING_NEXT, "approve", 1, 2, "approved"),
    ],
)
def test_leave_decision_paths(state, action, step, length, expected):
    result = state_machine.decide_leave(
        state,
        action=action,
        authority_step=step,
        route_length=length,
    )
    assert result.state == expected


@pytest.mark.parametrize(
    ("state", "action", "step", "length"),
    [
        ("approved", "approve", 0, 1),
        (state_machine.LEAVE_PENDING, "approve", 0, 2),
        (state_machine.LEAVE_PENDING, "forward", 1, 2),
        (state_machine.LEAVE_PENDING_NEXT, "forward", 1, 3),
        (state_machine.LEAVE_PENDING_NEXT, "forward", 1, 2),
        (state_machine.LEAVE_PENDING, "approve", 0, 3),
    ],
)
def test_leave_decision_rejects_invalid_order(state, action, step, length):
    with pytest.raises(state_machine.InvalidTransition):
        state_machine.decide_leave(
            state,
            action=action,
            authority_step=step,
            route_length=length,
        )


@pytest.mark.parametrize("route_length", [0, 3])
def test_leave_route_supports_at_most_one_forwarding_authority(route_length):
    assert not state_machine.supports_leave_route_length(route_length)


@pytest.mark.parametrize(
    ("leave_type", "source_id"),
    [
        ("casual", "HR-AFR-030 BR-HR-034"),
        ("restricted", "HR-AFR-031 BR-HR-034"),
        ("medical", "HR-AFR-032 BR-HR-034"),
        ("earned", "HR-AFR-033 BR-HR-034"),
        ("vacation", "HR-AFR-034 BR-HR-034"),
        ("sabbatical", "HR-AFR-035 BR-HR-034"),
    ],
    ids=lambda value: value,
)
def test_supported_leave_types_match_spec(leave_type, source_id):
    payload = {
        "leave_type": leave_type,
        "duration_days": "1.00",
        "justification": "Family commitment",
    }
    serializer = LeaveRequestCreateSerializer(data=payload)
    assert serializer.is_valid(), (source_id, serializer.errors)
    assert leave_type in {code for code, _ in LEAVE_TYPES}


@pytest.mark.parametrize(
    ("missing_field", "source_id"),
    [
        ("leave_type", "HR-AFR-036 BR-HR-007"),
        ("duration_days", "HR-AFR-037 BR-HR-007"),
        ("justification", "HR-AFR-038 BR-HR-007"),
    ],
    ids=lambda value: value,
)
def test_leave_request_requires_each_specified_field(missing_field, source_id):
    payload = {
        "leave_type": "casual",
        "duration_days": "1.00",
        "justification": "Family commitment",
    }
    payload.pop(missing_field)
    serializer = LeaveRequestCreateSerializer(data=payload)
    assert not serializer.is_valid(), source_id
    assert missing_field in serializer.errors


@pytest.mark.django_db
def test_leave_route_rejects_more_than_one_forwarding_authority():
    with pytest.raises(ConflictError) as error:
        configuration.save_workflow_route(
            actor=actor(7, "hr.workflow.manage"),
            employee_category="staff",
            request_type="leave_casual",
            steps=[
                {"approver_user_id": user_id, "authority_label": f"Authority {user_id}"}
                for user_id in (88, 99, 100)
            ],
        )
    assert error.value.code == "leave_route_too_long"


@pytest.fixture
def configured_leave():
    employee = EmployeeRecord.objects.create(
        user_id=1001,
        employee_category="staff",
        department="Research",
        designation="Assistant",
        created_by_user_id=7,
        updated_by_user_id=7,
    )
    leaves.set_leave_balance(
        actor=actor(7, "hr.leave_balance.manage"),
        employee_user_id=1001,
        leave_type="casual",
        available_days=Decimal("8.00"),
        is_eligible=True,
    )
    WorkflowRoute.objects.create(
        employee_category="staff",
        request_type="leave_casual",
        steps=[
            {"approver_user_id": 88, "authority_label": "HOD"},
            {"approver_user_id": 99, "authority_label": "Registrar"},
        ],
        updated_by_user_id=7,
    )
    return employee


@pytest.mark.django_db
@pytest.mark.parametrize(
    "source_ids",
    ["HR-AFR-039 HR-AFR-040 BR-HR-008"],
    ids=lambda value: value,
)
def test_leave_submission_checks_balance_and_eligibility(configured_leave, source_ids):
    employee = configured_leave
    balance = LeaveBalance.objects.get(employee=employee, leave_type="casual")
    balance.is_eligible = False
    balance.save(update_fields=["is_eligible", "updated_at"])

    with pytest.raises(ConflictError) as not_eligible:
        leaves.submit_leave_request(
            actor=actor(1001, "hr.leave.create"),
            leave_type="casual",
            duration_days=Decimal("1"),
            justification="Family commitment",
        )
    assert not_eligible.value.code == "leave_not_eligible"

    balance.is_eligible = True
    balance.save(update_fields=["is_eligible", "updated_at"])
    with pytest.raises(ConflictError) as insufficient:
        leaves.submit_leave_request(
            actor=actor(1001, "hr.leave.create"),
            leave_type="casual",
            duration_days=Decimal("9"),
            justification="Family commitment",
        )
    assert insufficient.value.code == "leave_balance_insufficient"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "source_ids",
    [
        (
            "HR-UC-003 HR-UC-004 CW-HR-01 HR-AFR-029 HR-AFR-041 HR-AFR-042 "
            "BW-HR-01 BW-HR-03 BR-HR-009 BR-HR-010"
        )
    ],
    ids=lambda value: value,
)
def test_leave_routes_and_deducts_balance(configured_leave, source_ids):
    request = leaves.submit_leave_request(
        actor=actor(1001, "hr.leave.create"),
        leave_type="casual",
        duration_days=Decimal("3.5"),
        justification="Family commitment",
    )
    balance = LeaveBalance.objects.get(employee=configured_leave, leave_type="casual")
    assert request.status == "pending_authority"
    assert request.current_authority_user_id == 88
    assert balance.available_days == Decimal("8.00")

    with pytest.raises(NotFoundError):
        leaves.decide_leave_request(
            actor=actor(77, "hr.leave.approve"),
            request_id=request.pk,
            action="forward",
        )
    with pytest.raises(ConflictError) as order_error:
        leaves.decide_leave_request(
            actor=actor(88, "hr.leave.approve"),
            request_id=request.pk,
            action="approve",
        )
    assert order_error.value.code == "workflow_order"

    forwarded = leaves.decide_leave_request(
        actor=actor(88, "hr.leave.approve"),
        request_id=request.pk,
        action="forward",
    )
    assert forwarded.current_authority_user_id == 99
    approved = leaves.decide_leave_request(
        actor=actor(99, "hr.leave.approve"),
        request_id=request.pk,
        action="approve",
    )
    balance.refresh_from_db()
    assert approved.status == "approved"
    assert balance.available_days == Decimal("4.50")
    assert list(
        LeaveLedgerEntry.objects.filter(leave_request=request).values_list(
            "amount_delta", flat=True
        )
    ) == [Decimal("-3.50")]
    assert AuditEvent.objects.filter(entity_type="leave_request", entity_id=request.pk).count() == 3

    with pytest.raises(NotFoundError):
        leaves.decide_leave_request(
            actor=actor(99, "hr.leave.approve"),
            request_id=request.pk,
            action="approve",
        )
    balance.refresh_from_db()
    assert balance.available_days == Decimal("4.50")


@pytest.mark.django_db
@pytest.mark.parametrize("source_ids", ["BR-HR-023 BW-HR-02"], ids=lambda value: value)
def test_rejected_leave_does_not_deduct_balance(configured_leave, source_ids):
    request = leaves.submit_leave_request(
        actor=actor(1001, "hr.leave.create"),
        leave_type="casual",
        duration_days=Decimal("2"),
        justification="Family commitment",
    )
    rejected = leaves.decide_leave_request(
        actor=actor(88, "hr.leave.approve"),
        request_id=request.pk,
        action="reject",
    )
    balance = LeaveBalance.objects.get(employee=configured_leave, leave_type="casual")
    assert rejected.status == "rejected"
    assert balance.available_days == Decimal("8.00")
    assert not LeaveLedgerEntry.objects.filter(leave_request=request).exists()
    assert AuditEvent.objects.filter(entity_type="leave_request", entity_id=request.pk).count() == 2


@pytest.mark.django_db
def test_employee_and_approver_only_see_their_leave_rows(configured_leave):
    own = leaves.submit_leave_request(
        actor=actor(1001, "hr.leave.create"),
        leave_type="casual",
        duration_days=Decimal("1"),
        justification="Family commitment",
    )
    other_employee = EmployeeRecord.objects.create(
        user_id=1002,
        employee_category="staff",
        department="Research",
        designation="Assistant",
        created_by_user_id=7,
        updated_by_user_id=7,
    )
    other = LeaveRequest.objects.create(
        employee=other_employee,
        leave_type="casual",
        duration_days=Decimal("1"),
        justification="Personal matter",
        route_snapshot=[{"approver_user_id": 99}],
        current_authority_user_id=99,
        submitted_by_user_id=1002,
    )
    assert set(
        visible_leave_requests(actor(1001, "hr.leave.view_self")).values_list("id", flat=True)
    ) == {own.pk}
    assert set(
        visible_leave_requests(actor(88, "hr.leave.approve")).values_list("id", flat=True)
    ) == {own.pk}
    assert set(visible_leave_requests(actor(7, "hr.leave.view")).values_list("id", flat=True)) == {
        own.pk,
        other.pk,
    }


@pytest.mark.django_db
@pytest.mark.parametrize("source_ids", ["HR-AFR-043 BR-HR-011"], ids=lambda value: value)
def test_leave_ledger_entries_are_immutable(configured_leave, source_ids):
    entry = LeaveLedgerEntry.objects.get(entry_type="balance_configured")
    with pytest.raises(TypeError):
        entry.delete()
    with pytest.raises(TypeError):
        LeaveLedgerEntry.objects.filter(pk=entry.pk).update(amount_delta=Decimal("1"))


@pytest.mark.django_db
@pytest.mark.parametrize("source_id", ["BR-HR-024"], ids=lambda value: value)
def test_leave_pending_reminder_is_generated_once(configured_leave, source_id):
    route = WorkflowRoute.objects.get(employee_category="staff", request_type="leave_casual")
    route.reminder_after_hours = 1
    route.save(update_fields=["reminder_after_hours", "updated_at"])
    request = leaves.submit_leave_request(
        actor=actor(1001, "hr.leave.create"),
        leave_type="casual",
        duration_days=Decimal("1"),
        justification="Family commitment",
    )
    now = timezone.now()
    LeaveRequest.objects.filter(pk=request.pk).update(updated_at=now - timedelta(hours=2))

    assert generate_pending_reminders(now_iso=now.isoformat()) == 1
    assert generate_pending_reminders(now_iso=now.isoformat()) == 0
    reminder = HRNotification.objects.get(topic="leave.pending_reminder")
    assert reminder.recipient_user_id == 88
    assert reminder.payload == {
        "leave_request_id": request.pk,
        "status": "pending_authority",
    }
    assert (
        AuditEvent.objects.filter(
            entity_type="leave_request", entity_id=request.pk, action="leave.reminder_generated"
        ).count()
        == 1
    ), source_id


@pytest.mark.django_db
def test_leave_api_requires_module_grant_and_permission(stub_iam):
    from rest_framework.test import APIClient

    payload = {
        "leave_type": "casual",
        "duration_days": "1.00",
        "justification": "Family commitment",
    }
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test")

    stub_iam(make_session(user_id=1001, kind="staff", modules=("hr",), permissions=()))
    assert client.post("/api/v1/hr/leaves/create/", payload).status_code == 403

    stub_iam(
        make_session(
            user_id=1001,
            kind="staff",
            modules=(),
            permissions=("hr.leave.create",),
        )
    )
    assert client.post("/api/v1/hr/leaves/create/", payload).status_code == 403
