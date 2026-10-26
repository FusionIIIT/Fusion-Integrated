"""Services for Leave Management — ALL writes go here. Transaction boundaries. Emits events."""
from datetime import date
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.utils import timezone

from ..domain import entities, state_machine
from ..domain.errors import (
    InsufficientBalanceError,
    InvalidTransitionError,
    LeaveDomainError,
    MedicalCertificateRequiredError,
    OverlappingLeaveError,
    SubstituteConsentRequiredError,
    SubstituteNotEligibleError,
    SubstituteRequiredError,
)
from ..models import (
    HolidayCalendar,
    LeaveBalance,
    LeavePolicy,
    LeaveRequest,
    LeaveRequestTransition,
    OfflineLeaveEntry,
    SubstituteRequest,
)
from ..selectors.balances import get_or_create_balance
from ..selectors.leave_requests import (
    get_leave_policy,
    get_overlapping_requests,
    get_leave_balance,
    is_holiday,
)
from .. import events


def _record_transition(
    leave_request: LeaveRequest,
    from_status: str,
    to_status: str,
    actor_user_id: Optional[int],
    actor_role: str,
    reason: str = "",
    metadata: dict = None,
) -> LeaveRequestTransition:
    """Record a status transition in the audit trail."""
    return LeaveRequestTransition.objects.create(
        leave_request=leave_request,
        from_status=from_status,
        to_status=to_status,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        reason=reason,
        metadata=metadata or {},
    )


def _calculate_total_days(
    category: str,
    start_date: date,
    end_date: date,
    half_day: bool,
    half_day_session: Optional[str],
) -> Decimal:
    """Calculate total leave days based on category rules."""
    if half_day:
        return Decimal("0.5")

    days = (end_date - start_date).days + 1

    # For CL, SCL, RH - only count working days (Mon-Fri, excluding holidays)
    if category in (entities.LeaveCategory.CL, entities.LeaveCategory.SCL, entities.LeaveCategory.RH):
        working_days = 0
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:  # Mon-Fri
                if is_holiday(current, is_restricted=(category == entities.LeaveCategory.RH)):
                    current += date.resolution
                    continue
                working_days += 1
            current += date.resolution
        return Decimal(str(working_days))

    # For EL, VL, COL - count all days including weekends/holidays
    return Decimal(str(days))


@transaction.atomic
def create_leave_request(
    *,
    user_id: int,
    category: str,
    start_date: date,
    end_date: date,
    half_day: bool,
    half_day_session: Optional[str],
    purpose: str,
    station_leave: bool,
    station_leave_address: Optional[str],
    substitute_id: Optional[int],
    employee_type: str,
    principal,
) -> LeaveRequest:
    """Create a new leave request (draft)."""
    # Check eligibility
    policy = get_leave_policy(category, employee_type, start_date)
    if not policy:
        raise LeaveDomainError(f"No policy for {category} ({employee_type})")

    from .balances import ensure_user_balances

    balances = ensure_user_balances(user_id, employee_type, start_date.year)
    balance = balances.get(category)
    if not balance:
        raise InsufficientBalanceError(category, 0, 1)

    total_days = _calculate_total_days(category, start_date, end_date, half_day, half_day_session)

    # Check overlapping requests
    overlapping = get_overlapping_requests(user_id, start_date, end_date)
    if overlapping.exists():
        raise OverlappingLeaveError()

    # Check if substitute is required
    requires_substitute = category in (
        entities.LeaveCategory.SCL,
        entities.LeaveCategory.EL,
        entities.LeaveCategory.VL,
        entities.LeaveCategory.COL,
    )

    if requires_substitute and not substitute_id:
        raise SubstituteRequiredError()

    # Validate substitute if provided
    if substitute_id:
        if substitute_id == user_id:
            raise SubstituteNotEligibleError("Cannot be your own substitute")
        # Check substitute has no overlapping leave
        sub_overlapping = get_overlapping_requests(substitute_id, start_date, end_date)
        if sub_overlapping.exists():
            raise SubstituteNotEligibleError("Substitute has overlapping leave")

    # Check medical certificate for COL
    if category == entities.LeaveCategory.COL:
        # Medical certificate check would be done at submission
        pass

    # Check RH date is in calendar
    if category == entities.LeaveCategory.RH:
        if not is_holiday(start_date, is_restricted=True):
            raise LeaveDomainError("Selected date is not a Restricted Holiday")

    # Create the request
    leave_request = LeaveRequest.objects.create(
        user_id=user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        half_day=half_day,
        half_day_session=half_day_session or "",
        total_days=total_days,
        purpose=purpose,
        station_leave=station_leave,
        station_leave_address=station_leave_address or "",
        substitute_id=substitute_id,
        status=entities.LeaveStatus.DRAFT,
    )

    _record_transition(
        leave_request,
        "none",
        entities.LeaveStatus.DRAFT,
        principal.user_id,
        principal.active_role or "employee",
        "Leave request created",
    )

    events.emit_leave_request_created(leave_request, principal)

    return leave_request


@transaction.atomic
def submit_leave_request(
    leave_request_id: int,
    principal,
) -> LeaveRequest:
    """Submit a draft leave request for approval."""
    lr = LeaveRequest.objects.select_for_update().get(pk=leave_request_id)

    if lr.user_id != principal.user_id:
        raise LeaveDomainError("Not your leave request")

    if lr.status != entities.LeaveStatus.DRAFT:
        raise InvalidTransitionError(lr.status, entities.LeaveStatus.SUBMITTED, lr.category)

    # Re-check eligibility at submission time
    employee_type = "faculty" if principal.kind == "faculty" else "non_faculty"
    policy = get_leave_policy(lr.category, employee_type, lr.start_date)
    if not policy:
        raise LeaveDomainError("Policy no longer valid")

    balance = get_leave_balance(lr.user_id, lr.category, lr.start_date.year)
    if not balance or balance.closing_balance < lr.total_days:
        raise InsufficientBalanceError(lr.category, balance.closing_balance if balance else 0, lr.total_days)

    # Check substitute for required categories
    requires_substitute = lr.category in (
        entities.LeaveCategory.SCL,
        entities.LeaveCategory.EL,
        entities.LeaveCategory.VL,
        entities.LeaveCategory.COL,
    )

    if requires_substitute:
        if not lr.substitute_id:
            raise SubstituteRequiredError()

        # Create substitute request
        SubstituteRequest.objects.create(
            leave_request=lr,
            substitute_id=lr.substitute_id,
            nominated_by=lr.user_id,
            status="pending",
        )

        lr.status = entities.LeaveStatus.SUBSTITUTE_PENDING
        transition = state_machine.LeaveTransition.SUBSTITUTE_ACCEPTED
    else:
        lr.status = entities.LeaveStatus.SUBMITTED
        # Will go to Unit Head Review
        lr.status = entities.LeaveStatus.UNIT_HEAD_REVIEW
        transition = state_machine.LeaveTransition.SUBMIT

    lr.applied_at = timezone.now()
    lr.save(update_fields=["status", "applied_at", "updated_at"])

    _record_transition(
        lr,
        entities.LeaveStatus.DRAFT,
        lr.status,
        principal.user_id,
        principal.active_role or "employee",
        "Leave request submitted",
    )

    events.emit_leave_request_submitted(lr, principal)

    return lr


@transaction.atomic
def respond_to_substitute_request(
    substitute_request_id: int,
    accept: bool,
    reason: str,
    principal,
) -> SubstituteRequest:
    """Accept or decline a substitute nomination."""
    sr = SubstituteRequest.objects.select_for_update().select_related("leave_request").get(
        pk=substitute_request_id
    )

    if sr.substitute_id != principal.user_id:
        raise LeaveDomainError("Not your substitute request")

    if sr.status != "pending":
        raise LeaveDomainError("Substitute request already responded to")

    lr = sr.leave_request

    if accept:
        sr.status = "accepted"
        sr.responded_at = timezone.now()
        sr.reason = reason
        sr.save(update_fields=["status", "responded_at", "reason", "updated_at"])

        lr.status = entities.LeaveStatus.UNIT_HEAD_REVIEW
        lr.save(update_fields=["status", "updated_at"])

        _record_transition(
            lr,
            entities.LeaveStatus.SUBSTITUTE_PENDING,
            entities.LeaveStatus.UNIT_HEAD_REVIEW,
            principal.user_id,
            "substitute",
            "Substitute accepted",
        )

        events.emit_substitute_accepted(lr, principal)
    else:
        sr.status = "declined"
        sr.responded_at = timezone.now()
        sr.reason = reason
        sr.save(update_fields=["status", "responded_at", "reason", "updated_at"])

        # Back to submitted - applicant must nominate another substitute
        lr.status = entities.LeaveStatus.SUBMITTED
        lr.save(update_fields=["status", "updated_at"])

        _record_transition(
            lr,
            entities.LeaveStatus.SUBSTITUTE_PENDING,
            entities.LeaveStatus.SUBMITTED,
            principal.user_id,
            "substitute",
            f"Substitute declined: {reason}",
        )

        events.emit_substitute_declined(lr, principal, reason)

    return sr


@transaction.atomic
def unit_head_review(
    leave_request_id: int,
    recommend: bool,
    remark: str,
    principal,
) -> LeaveRequest:
    """Unit Head reviews and recommends or not."""
    lr = LeaveRequest.objects.select_for_update().get(pk=leave_request_id)

    if lr.status != entities.LeaveStatus.UNIT_HEAD_REVIEW:
        raise InvalidTransitionError(lr.status, entities.LeaveStatus.UNIT_HEAD_REVIEW, lr.category)

    lr.unit_head_id = principal.user_id
    lr.unit_head_remark = remark
    lr.unit_head_action_at = timezone.now()

    if recommend:
        # For CL/RH, Unit Head can directly approve
        if lr.category in (entities.LeaveCategory.CL, entities.LeaveCategory.RH):
            lr.status = entities.LeaveStatus.APPROVED
            lr.approved_at = timezone.now()
            to_status = entities.LeaveStatus.APPROVED
        else:
            # For SCL, EL, VL, COL - go to Establishment
            lr.status = entities.LeaveStatus.ESTABLISHMENT_REVIEW
            to_status = entities.LeaveStatus.ESTABLISHMENT_REVIEW
    else:
        # Not recommended - goes to Final Sanction
        lr.status = entities.LeaveStatus.FINAL_SANCTION
        to_status = entities.LeaveStatus.FINAL_SANCTION

    lr.save(update_fields=[
        "status", "unit_head_id", "unit_head_remark", "unit_head_action_at",
        "approved_at", "updated_at",
    ])

    _record_transition(
        lr,
        entities.LeaveStatus.UNIT_HEAD_REVIEW,
        to_status,
        principal.user_id,
        "unit_head",
        remark,
    )

    events.emit_unit_head_reviewed(lr, recommend, principal)

    return lr


@transaction.atomic
def establishment_review(
    leave_request_id: int,
    action: str,  # "forward" or "return"
    remark: str,
    principal,
) -> LeaveRequest:
    """Establishment processes the request."""
    lr = LeaveRequest.objects.select_for_update().get(pk=leave_request_id)

    if lr.status != entities.LeaveStatus.ESTABLISHMENT_REVIEW:
        raise InvalidTransitionError(lr.status, entities.LeaveStatus.ESTABLISHMENT_REVIEW, lr.category)

    lr.establishment_id = principal.user_id
    lr.establishment_remark = remark
    lr.establishment_action_at = timezone.now()

    if action == "forward":
        lr.status = entities.LeaveStatus.FINAL_SANCTION
    else:
        lr.status = entities.LeaveStatus.UNIT_HEAD_REVIEW  # Return to Unit Head

    lr.save(update_fields=[
        "status", "establishment_id", "establishment_remark",
        "establishment_action_at", "updated_at",
    ])

    _record_transition(
        lr,
        entities.LeaveStatus.ESTABLISHMENT_REVIEW,
        lr.status,
        principal.user_id,
        "establishment",
        remark,
    )

    events.emit_establishment_reviewed(lr, action, principal)

    return lr


@transaction.atomic
def final_sanction(
    leave_request_id: int,
    approve: bool,
    remark: str,
    principal,
) -> LeaveRequest:
    """Final sanctioning authority decision."""
    lr = LeaveRequest.objects.select_for_update().get(pk=leave_request_id)

    if lr.status != entities.LeaveStatus.FINAL_SANCTION:
        raise InvalidTransitionError(lr.status, entities.LeaveStatus.FINAL_SANCTION, lr.category)

    lr.final_authority_id = principal.user_id
    lr.final_authority_remark = remark
    lr.final_authority_action_at = timezone.now()

    if approve:
        lr.status = entities.LeaveStatus.APPROVED
        lr.approved_at = timezone.now()
        # Deduct from balance
        balance = get_or_create_balance(lr.user_id, lr.category, lr.start_date.year)
        balance.availed += lr.total_days
        balance.closing_balance -= lr.total_days
        balance.save(update_fields=["availed", "closing_balance", "updated_at"])
    else:
        lr.status = entities.LeaveStatus.REJECTED
        lr.rejected_at = timezone.now()

    lr.save(update_fields=[
        "status", "final_authority_id", "final_authority_remark",
        "final_authority_action_at", "approved_at", "rejected_at", "updated_at",
    ])

    _record_transition(
        lr,
        entities.LeaveStatus.FINAL_SANCTION,
        lr.status,
        principal.user_id,
        "final_authority",
        remark,
    )

    events.emit_final_sanction(lr, approve, principal)

    return lr