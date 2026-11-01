"""Leave service (BR-HR-007 to BR-HR-011, BR-HR-023, BW-HR-01, 02, 03)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, NotFoundError
from modules.hreis.domain.leave import (
    LeaveStatus,
    LeaveType,
    calculate_new_balance,
    validate_leave_submission,
)
from modules.hreis.domain.workflow import DecisionOutcome, get_next_authority, validate_decision
from modules.hreis.models import EmployeeServiceRecord, LeaveRequest
from modules.hreis.services.audit import log_hr_action
from modules.hreis.services.notifications import send_hr_notification
from modules.hreis.services.service_records import get_or_create_service_record
from modules.hreis.services.workflow_config import get_workflow_config


@transaction.atomic
def submit_leave_request(
    *,
    user_id: int,
    username: str,
    leave_type: str,
    start_date: date,
    end_date: date,
    duration_days: float,
    justification: str,
) -> LeaveRequest:
    service_rec = get_or_create_service_record(user_id)

    try:
        validate_leave_submission(
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            duration_days=duration_days,
            justification=justification,
            category=service_rec.category,
            current_balances=service_rec.leave_balances or {},
        )
    except Exception as e:
        raise BadRequestError(str(e)) from e

    hierarchy = get_workflow_config("approval_hierarchy")
    first_role = get_next_authority("", service_rec.category, hierarchy) or "hod"

    leave = LeaveRequest.objects.create(
        user_id=user_id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        duration_days=Decimal(str(duration_days)),
        justification=justification,
        status=LeaveStatus.PENDING.value,
        current_authority_role=first_role,
        approval_history=[
            {
                "action": "submitted",
                "actor_id": user_id,
                "actor_username": username,
                "timestamp": timezone.now().isoformat(),
                "duration_days": duration_days,
            }
        ],
    )

    log_hr_action(
        actor_id=user_id,
        actor_username=username,
        actor_role="employee",
        action="submit_leave_request",
        entity_type="leave_request",
        entity_id=leave.id,
        details={
            "leave_type": leave_type,
            "duration": duration_days,
            "start": str(start_date),
            "end": str(end_date),
        },
    )

    send_hr_notification(
        user_id=user_id,
        title="Leave Request Submitted",
        message=f"Your {leave_type.capitalize()} leave request for {duration_days} days was submitted.",
        category="submission",
        link=f"/hr/leaves/{leave.id}",
    )

    return leave


@transaction.atomic
def decide_leave_request(
    *,
    leave_id: int,
    outcome: str,
    remarks: str,
    actor_id: int,
    actor_username: str,
    actor_role: str,
) -> LeaveRequest:
    leave = LeaveRequest.objects.select_for_update().filter(id=leave_id).first()
    if not leave:
        raise NotFoundError("Leave request not found.")

    service_rec = get_or_create_service_record(leave.user_id)
    hierarchy = get_workflow_config("approval_hierarchy")
    next_role = get_next_authority(leave.current_authority_role, service_rec.category, hierarchy)

    try:
        validate_decision(
            outcome=outcome,
            current_status=leave.status,
            remarks=remarks,
            can_forward=next_role is not None,
        )
    except Exception as e:
        raise BadRequestError(str(e)) from e

    history_entry = {
        "action": outcome,
        "actor_id": actor_id,
        "actor_username": actor_username,
        "actor_role": actor_role,
        "remarks": remarks,
        "timestamp": timezone.now().isoformat(),
    }

    if outcome == DecisionOutcome.FORWARDED.value:
        leave.status = LeaveStatus.FORWARDED.value
        leave.current_authority_role = next_role or leave.current_authority_role
        notify_msg = f"Your leave request has been forwarded to {leave.current_authority_role.upper()}."
    elif outcome == DecisionOutcome.APPROVED.value:
        leave.status = LeaveStatus.APPROVED.value
        # Deduct balance permanently (BR-HR-010, AFR-042)
        service_rec = EmployeeServiceRecord.objects.select_for_update().get(id=service_rec.id)
        service_rec.leave_balances = calculate_new_balance(
            service_rec.leave_balances or {},
            leave.leave_type,
            float(leave.duration_days),
        )
        service_rec.save()
        notify_msg = f"Your {leave.leave_type.capitalize()} leave request was approved."
    else:  # Rejected
        leave.status = LeaveStatus.REJECTED.value
        notify_msg = f"Your leave request was rejected. Reason: {remarks}"

    hist = list(leave.approval_history or [])
    hist.append(history_entry)
    leave.approval_history = hist
    leave.save()

    # Permanent audit log (AFR-043, BR-HR-011)
    log_hr_action(
        actor_id=actor_id,
        actor_username=actor_username,
        actor_role=actor_role,
        action=f"leave_{outcome}",
        entity_type="leave_request",
        entity_id=leave.id,
        details={
            "outcome": outcome,
            "remarks": remarks,
            "applicant_id": leave.user_id,
            "new_status": leave.status,
        },
    )

    send_hr_notification(
        user_id=leave.user_id,
        title=f"Leave Request {outcome.capitalize()}",
        message=notify_msg,
        category=outcome,
        link=f"/hr/leaves/{leave.id}",
    )

    return leave
