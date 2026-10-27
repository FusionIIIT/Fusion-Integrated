"""Transactional workflow services for Employee Leave Management."""
from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Optional

from django.db import transaction

from modules.elm.domain.errors import (
    ELMValidationError,
    InvalidStateTransitionError,
    SubstituteError,
    UnauthorizedActionError,
)
from modules.elm.domain.policy import calculate_resumption_adjustment
from modules.elm.domain.workflow import LeaveEvent, LeaveState, validate_transition
from modules.elm.models import (
    LeaveAccount,
    LeaveRequest,
    LeaveResumptionRecord,
    LeaveStatus,
    LeaveTransaction,
    SubstituteAssignment,
)
from modules.elm.services.policy import validate_and_calculate_request


@transaction.atomic
def submit_leave_request(
    applicant_id: int,
    employee_kind: str,
    category: str,
    start_date: datetime.date,
    end_date: datetime.date,
    reason: str,
    substitute_id: Optional[int] = None,
    is_half_day: bool = False,
    half_day_type: Optional[str] = None,
    is_station_leave: bool = False,
    station_address: str = "",
    emergency_contact: str = "",
    is_director: bool = False,
) -> LeaveRequest:
    """Submit a new leave application and route according to workflow rules."""
    # 1. Validate policy, duration, overlap, and balance
    duration = validate_and_calculate_request(
        applicant_id=applicant_id,
        employee_kind=employee_kind,
        category=category,
        start_date=start_date,
        end_date=end_date,
        is_half_day=is_half_day,
        half_day_type=half_day_type,
    )

    # 2. Substitute validation (BR-EL-014)
    substitute_required = substitute_id is not None
    if substitute_required:
        if substitute_id == applicant_id:
            raise SubstituteError("An employee cannot nominate themselves as a substitute.")

        # Check substitute availability
        sub_has_leave = LeaveRequest.objects.filter(
            applicant_id=substitute_id,
            status__in=[LeaveStatus.APPROVED, LeaveStatus.AWAITING_UNIT_HEAD_REVIEW],
            start_date__lte=end_date,
            end_date__gte=start_date,
        ).exists()
        if sub_has_leave:
            raise SubstituteError("Nominated substitute has active leave during this period.")

    # 3. Determine initial state via state machine
    next_state = validate_transition(
        current_state=LeaveState.DRAFT,
        event=LeaveEvent.SUBMIT,
        is_director=is_director,
        category=category,
        substitute_required=substitute_required,
    )

    # 4. Create LeaveRequest
    req = LeaveRequest.objects.create(
        applicant_id=applicant_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        duration_days=duration,
        is_half_day=is_half_day,
        half_day_type=half_day_type,
        reason=reason,
        is_station_leave=is_station_leave,
        station_address=station_address,
        emergency_contact=emergency_contact,
        status=next_state,
    )

    # 5. Hold/deduct balance
    account = LeaveAccount.objects.select_for_update().get(
        employee_id=applicant_id, category=category, year=start_date.year
    )
    account.available -= duration
    if next_state == LeaveStatus.APPROVED:
        account.used += duration
    else:
        account.pending += duration
    account.save(update_fields=["available", "used", "pending"])

    LeaveTransaction.objects.create(
        account=account,
        delta=-duration,
        transaction_type="LEAVE_SUBMIT",
        reference_id=str(req.id),
        idempotency_key=f"submit_{req.id}_{start_date.isoformat()}",
    )

    # 6. Create substitute assignment record if required
    if substitute_required:
        SubstituteAssignment.objects.create(
            request=req,
            substitute_id=substitute_id,
            status="PENDING",
        )

    return req


@transaction.atomic
def respond_substitute(
    request_id: int,
    substitute_id: int,
    accept: bool,
    remarks: str = "",
    is_director: bool = False,
) -> LeaveRequest:
    """Process substitute accept or decline (BR-EL-015)."""
    req = LeaveRequest.objects.select_for_update().get(id=request_id)
    assignment = req.substitute_assignments.filter(substitute_id=substitute_id, status="PENDING").first()
    if not assignment:
        raise UnauthorizedActionError("No pending substitute assignment found for this user.")

    event = LeaveEvent.SUBSTITUTE_ACCEPT if accept else LeaveEvent.SUBSTITUTE_DECLINE
    next_state = validate_transition(
        current_state=req.status,
        event=event,
        is_director=is_director,
        category=req.category,
    )

    assignment.status = "ACCEPTED" if accept else "DECLINED"
    assignment.remarks = remarks
    assignment.responded_at = datetime.datetime.now()
    assignment.save(update_fields=["status", "remarks", "responded_at"])

    req.status = next_state
    req.save(update_fields=["status", "updated_at"])

    # If Director self-sanction immediately reaches approved
    if next_state == LeaveStatus.APPROVED:
        account = LeaveAccount.objects.select_for_update().get(
            employee_id=req.applicant_id, category=req.category, year=req.start_date.year
        )
        account.pending -= req.duration_days
        account.used += req.duration_days
        account.save(update_fields=["pending", "used"])

    return req


@transaction.atomic
def withdraw_request(request_id: int, applicant_id: int) -> LeaveRequest:
    """Immediate withdrawal of pending request before final approval (BR-EL-022)."""
    req = LeaveRequest.objects.select_for_update().get(id=request_id)
    if req.applicant_id != applicant_id:
        raise UnauthorizedActionError("Only the applicant may withdraw their pending request.")

    next_state = validate_transition(
        current_state=req.status,
        event=LeaveEvent.WITHDRAW,
    )

    # Restore pending balance back to available
    account = LeaveAccount.objects.select_for_update().get(
        employee_id=req.applicant_id, category=req.category, year=req.start_date.year
    )
    account.available += req.duration_days
    account.pending -= req.duration_days
    account.save(update_fields=["available", "pending"])

    LeaveTransaction.objects.create(
        account=account,
        delta=req.duration_days,
        transaction_type="LEAVE_WITHDRAW",
        reference_id=str(req.id),
        idempotency_key=f"withdraw_{req.id}",
    )

    req.status = next_state
    req.save(update_fields=["status", "updated_at"])
    return req


@transaction.atomic
def unit_head_review(
    request_id: int,
    action: str,  # APPROVE, REJECT, RECOMMEND, NOT_RECOMMEND
    remarks: str = "",
    establishment_configured: bool = False,
) -> LeaveRequest:
    """Review leave at Unit Head stage (BR-EL-016, BR-EL-017)."""
    req = LeaveRequest.objects.select_for_update().get(id=request_id)

    event_map = {
        "APPROVE": LeaveEvent.UNIT_HEAD_APPROVE,
        "REJECT": LeaveEvent.UNIT_HEAD_REJECT,
        "RECOMMEND": LeaveEvent.UNIT_HEAD_RECOMMEND,
        "NOT_RECOMMEND": LeaveEvent.UNIT_HEAD_RECOMMEND,  # Not recommended still proceeds (BR-EL-017)
    }
    event = event_map.get(action.upper())
    if not event:
        raise ELMValidationError(f"Invalid Unit Head action '{action}'.")

    next_state = validate_transition(
        current_state=req.status,
        event=event,
        category=req.category,
        establishment_configured=establishment_configured,
    )

    req.unit_head_recommendation = action.upper()
    req.unit_head_remarks = remarks
    req.status = next_state
    req.save(update_fields=["unit_head_recommendation", "unit_head_remarks", "status", "updated_at"])

    account = LeaveAccount.objects.select_for_update().get(
        employee_id=req.applicant_id, category=req.category, year=req.start_date.year
    )

    if next_state == LeaveStatus.APPROVED:
        account.pending -= req.duration_days
        account.used += req.duration_days
        account.save(update_fields=["pending", "used"])
    elif next_state == LeaveStatus.REJECTED:
        account.available += req.duration_days
        account.pending -= req.duration_days
        account.save(update_fields=["available", "pending"])
        LeaveTransaction.objects.create(
            account=account,
            delta=req.duration_days,
            transaction_type="LEAVE_REJECT",
            reference_id=str(req.id),
        )

    return req


@transaction.atomic
def sanction_review(
    request_id: int,
    approve: bool,
    remarks: str = "",
) -> LeaveRequest:
    """Final sanction decision by Competent Authority (BR-EL-018)."""
    req = LeaveRequest.objects.select_for_update().get(id=request_id)
    event = LeaveEvent.SANCTION_APPROVE if approve else LeaveEvent.SANCTION_REJECT

    next_state = validate_transition(
        current_state=req.status,
        event=event,
        category=req.category,
    )

    req.sanctioning_authority_remarks = remarks
    req.status = next_state
    req.save(update_fields=["sanctioning_authority_remarks", "status", "updated_at"])

    account = LeaveAccount.objects.select_for_update().get(
        employee_id=req.applicant_id, category=req.category, year=req.start_date.year
    )

    if next_state == LeaveStatus.APPROVED:
        account.pending -= req.duration_days
        account.used += req.duration_days
        account.save(update_fields=["pending", "used"])
    elif next_state == LeaveStatus.REJECTED:
        account.available += req.duration_days
        account.pending -= req.duration_days
        account.save(update_fields=["available", "pending"])
        LeaveTransaction.objects.create(
            account=account,
            delta=req.duration_days,
            transaction_type="LEAVE_REJECT",
            reference_id=str(req.id),
        )

    return req


@transaction.atomic
def request_cancellation(request_id: int, applicant_id: int, reason: str = "") -> LeaveRequest:
    """Request pre-start cancellation of approved leave (BR-EL-023)."""
    req = LeaveRequest.objects.select_for_update().get(id=request_id)
    if req.applicant_id != applicant_id:
        raise UnauthorizedActionError("Only the applicant may request cancellation.")
    if req.start_date <= datetime.date.today():
        raise ELMValidationError("Pre-start cancellation is only allowed before the leave begins.")

    next_state = validate_transition(
        current_state=req.status,
        event=LeaveEvent.REQUEST_CANCELLATION,
    )
    req.status = next_state
    req.save(update_fields=["status", "updated_at"])
    return req


@transaction.atomic
def review_cancellation(request_id: int, approve: bool, remarks: str = "") -> LeaveRequest:
    """Review cancellation request (BR-EL-023)."""
    req = LeaveRequest.objects.select_for_update().get(id=request_id)
    event = LeaveEvent.APPROVE_CANCELLATION if approve else LeaveEvent.REJECT_CANCELLATION

    next_state = validate_transition(
        current_state=req.status,
        event=event,
    )

    if next_state == LeaveStatus.CANCELLED:
        # Restore used leave balance back to available
        account = LeaveAccount.objects.select_for_update().get(
            employee_id=req.applicant_id, category=req.category, year=req.start_date.year
        )
        account.available += req.duration_days
        account.used -= req.duration_days
        account.save(update_fields=["available", "used"])

        LeaveTransaction.objects.create(
            account=account,
            delta=req.duration_days,
            transaction_type="CANCELLATION_RESTORE",
            reference_id=str(req.id),
        )

    req.status = next_state
    req.save(update_fields=["status", "updated_at"])
    return req
