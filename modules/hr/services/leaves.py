from decimal import Decimal

from django.db import IntegrityError, transaction

from core.api.exceptions import ConflictError, NotFoundError
from modules.hr.domain import state_machine
from modules.hr.models import (
    LEAVE_TYPES,
    EmployeeRecord,
    LeaveBalance,
    LeaveLedgerEntry,
    LeaveRequest,
    WorkflowRoute,
)
from modules.hr.services import authz, notifications
from modules.hr.services.common import audit

LEAVE_TYPE_CODES = {code for code, _ in LEAVE_TYPES}


def _leave_route_type(leave_type: str) -> str:
    return f"leave_{leave_type}"


@transaction.atomic
def set_leave_balance(
    *,
    actor,
    employee_user_id: int,
    leave_type: str,
    available_days: Decimal,
    is_eligible: bool,
) -> LeaveBalance:
    authz.require(actor, "hr.leave_balance.manage")
    if leave_type not in LEAVE_TYPE_CODES or available_days < 0:
        raise ConflictError(
            "Choose a supported leave type and non-negative balance.", code="invalid_leave_balance"
        )
    employee = EmployeeRecord.objects.select_for_update().filter(user_id=employee_user_id).first()
    if employee is None:
        raise NotFoundError("No employee service record is available.")
    balance = (
        LeaveBalance.objects.select_for_update()
        .filter(employee=employee, leave_type=leave_type)
        .first()
    )
    if balance is None:
        try:
            balance = LeaveBalance.objects.create(
                employee=employee,
                leave_type=leave_type,
                available_days=available_days,
                is_eligible=is_eligible,
                updated_by_user_id=actor.user_id,
            )
        except IntegrityError as exc:
            raise ConflictError(
                "The leave balance was changed concurrently; reload it.",
                code="leave_balance_conflict",
            ) from exc
        delta = available_days
        action = "leave.balance_configured"
    else:
        delta = available_days - balance.available_days
        changed = delta != 0 or balance.is_eligible != is_eligible
        if not changed:
            return balance
        balance.available_days = available_days
        balance.is_eligible = is_eligible
        balance.updated_by_user_id = actor.user_id
        balance.save(
            update_fields=[
                "available_days",
                "is_eligible",
                "updated_by_user_id",
                "updated_at",
            ]
        )
        action = "leave.balance_adjusted"
    LeaveLedgerEntry.objects.create(
        balance=balance,
        entry_type="balance_configured",
        amount_delta=delta,
        actor_user_id=actor.user_id,
        details={"is_eligible": is_eligible},
    )
    audit(
        actor=actor,
        entity_type="leave_balance",
        entity_id=balance.pk,
        action=action,
        details={
            "employee_user_id": employee_user_id,
            "leave_type": leave_type,
            "amount_delta": str(delta),
            "is_eligible": is_eligible,
        },
    )
    return balance


@transaction.atomic
def submit_leave_request(
    *, actor, leave_type: str, duration_days: Decimal, justification: str
) -> LeaveRequest:
    authz.require(actor, "hr.leave.create")
    if leave_type not in LEAVE_TYPE_CODES:
        raise ConflictError(
            "Choose one of the supported leave types.", code="unsupported_leave_type"
        )
    justification = justification.strip()
    if duration_days <= 0 or not justification:
        raise ConflictError(
            "Enter a positive leave duration and justification.", code="leave_fields_required"
        )
    employee = EmployeeRecord.objects.filter(user_id=actor.user_id).first()
    if employee is None:
        raise ConflictError(
            "An employee service record is required to apply for leave.",
            code="employee_record_required",
        )
    balance = (
        LeaveBalance.objects.select_for_update()
        .filter(employee=employee, leave_type=leave_type)
        .first()
    )
    if balance is None:
        raise ConflictError(
            "HR has not configured this leave balance yet.", code="leave_balance_unavailable"
        )
    if not balance.is_eligible:
        raise ConflictError(
            "Your configured eligibility does not allow this leave request.",
            code="leave_not_eligible",
        )
    if duration_days > balance.available_days:
        raise ConflictError(
            "The requested duration exceeds your available leave balance.",
            code="leave_balance_insufficient",
        )
    route = WorkflowRoute.objects.filter(
        employee_category=employee.employee_category,
        request_type=_leave_route_type(leave_type),
    ).first()
    if route is None or not state_machine.supports_leave_route_length(len(route.steps)):
        raise ConflictError(
            "HR has not configured an approval route for this leave type.",
            code="leave_route_unavailable",
        )
    first_step = route.steps[0]
    request = LeaveRequest.objects.create(
        employee=employee,
        leave_type=leave_type,
        duration_days=duration_days,
        justification=justification,
        route_snapshot=route.steps,
        current_authority_user_id=int(first_step["approver_user_id"]),
        submitted_by_user_id=actor.user_id,
    )
    audit(
        actor=actor,
        entity_type="leave_request",
        entity_id=request.pk,
        action="leave.submitted",
        details={"leave_type": leave_type, "duration_days": str(duration_days)},
    )
    notifications.enqueue(
        recipient_user_id=actor.user_id,
        topic="leave.submitted",
        dedupe_key=f"leave:{request.pk}:submitted",
        subject="Leave request submitted",
        body="Your leave request was submitted for approval.",
        payload={"leave_request_id": request.pk, "status": request.status},
    )
    notifications.enqueue(
        recipient_user_id=request.current_authority_user_id,
        topic="leave.awaiting_authority",
        dedupe_key=f"leave:{request.pk}:authority:0",
        subject="Leave request awaiting review",
        body="A leave request is ready for your review.",
        payload={"leave_request_id": request.pk, "status": request.status},
    )
    return request


@transaction.atomic
def decide_leave_request(*, actor, request_id: int, action: str, note: str = "") -> LeaveRequest:
    authz.require(actor, "hr.leave.approve")
    request = (
        LeaveRequest.objects.select_for_update()
        .select_related("employee")
        .filter(pk=request_id)
        .first()
    )
    if request is None:
        raise NotFoundError("No such leave request is assigned to you.")
    if (
        request.current_authority_user_id != actor.user_id
        or request.employee.user_id == actor.user_id
    ):
        raise NotFoundError("No such leave request is assigned to you.")
    try:
        transition = state_machine.decide_leave(
            request.status,
            action=action,
            authority_step=request.authority_step,
            route_length=len(request.route_snapshot),
        )
    except state_machine.InvalidTransition as exc:
        code = (
            "workflow_order"
            if exc.action in {"approval_must_follow_route", "no_next_authority"}
            else "invalid_transition"
        )
        raise ConflictError(
            "The requested decision is not valid at this workflow step.", code=code
        ) from exc
    before = request.status
    if action == "approve":
        balance = (
            LeaveBalance.objects.select_for_update()
            .filter(employee=request.employee, leave_type=request.leave_type)
            .first()
        )
        if balance is None or not balance.is_eligible:
            raise ConflictError(
                "The leave balance or eligibility is no longer valid.", code="leave_not_eligible"
            )
        if request.duration_days > balance.available_days:
            raise ConflictError(
                "The available leave balance no longer covers this request.",
                code="leave_balance_insufficient",
            )
        balance.available_days -= request.duration_days
        balance.updated_by_user_id = actor.user_id
        balance.save(update_fields=["available_days", "updated_by_user_id", "updated_at"])
        LeaveLedgerEntry.objects.create(
            balance=balance,
            leave_request=request,
            entry_type="leave_approved",
            amount_delta=-request.duration_days,
            actor_user_id=actor.user_id,
            details={"leave_type": request.leave_type},
        )
    request.status = transition.state
    request.authority_step = transition.authority_step
    if action == "forward":
        request.current_authority_user_id = int(
            request.route_snapshot[transition.authority_step]["approver_user_id"]
        )
    else:
        request.current_authority_user_id = None
    request.save(
        update_fields=[
            "status",
            "authority_step",
            "current_authority_user_id",
            "updated_at",
        ]
    )
    audit(
        actor=actor,
        entity_type="leave_request",
        entity_id=request.pk,
        action=f"leave.{action}",
        details={
            "from_status": before,
            "to_status": request.status,
            "leave_type": request.leave_type,
            "duration_days": str(request.duration_days),
            "note": note.strip(),
        },
    )
    if action == "forward":
        notifications.enqueue(
            recipient_user_id=request.current_authority_user_id,
            topic="leave.forwarded",
            dedupe_key=f"leave:{request.pk}:authority:{request.authority_step}",
            subject="Leave request forwarded to you",
            body="A leave request is ready for your review.",
            payload={"leave_request_id": request.pk, "status": request.status},
        )
    result_word = {"approve": "approved", "reject": "rejected", "forward": "forwarded"}[action]
    notifications.enqueue(
        recipient_user_id=request.employee.user_id,
        topic=f"leave.{action}",
        dedupe_key=f"leave:{request.pk}:{action}:{request.authority_step}",
        subject=f"Leave request {result_word}",
        body=f"Your leave request was {result_word} by its current approving authority.",
        payload={"leave_request_id": request.pk, "status": request.status},
    )
    return request
