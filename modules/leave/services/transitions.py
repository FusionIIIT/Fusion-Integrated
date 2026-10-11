"""Transactional choke point for all state machine movements.

All workflow movement goes through execute_transition, which takes select_for_update,
validates legal transitions, writes audit rows, and performs atomic ledger movements.
"""


from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.leave.domain.constants import (
    Event,
    LedgerTransactionType,
    RequestStatus,
)
from modules.leave.domain.exceptions import (
    InvalidStateTransitionError,
    LeaveDomainError,
    UnauthorizedActionError,
)
from modules.leave.domain.state_machine import resolve_transition
from modules.leave.models.ledger import LeaveLedgerEntry
from modules.leave.models.requests import LeaveAuditEvent, LeaveRequest


def _translate_error(err: LeaveDomainError):
    if isinstance(err, InvalidStateTransitionError):
        return ConflictError(str(err))
    if isinstance(err, UnauthorizedActionError):
        return PermissionDeniedError(str(err))
    return BadRequestError(str(err))


def execute_transition(
    request_id: int,
    event: Event,
    actor_user_id: int,
    actor_role: str,
    remarks: str = "",
    context: dict | None = None,
) -> LeaveRequest:
    """The single transactional choke point for state transitions across all leave requests.

    Enforces locking, audit trail creation, and ledger effects in one atomic transaction.
    """
    with transaction.atomic():
        req = LeaveRequest.objects.select_for_update().get(id=request_id)
        current_status = RequestStatus(req.status)

        ctx = context or {}
        # Populate context flags if not provided
        if "needs_substitute" not in ctx:
            ctx["needs_substitute"] = bool(req.substitute_user_id)
        if "is_director" not in ctx:
            ctx["is_director"] = actor_role == "Director"

        try:
            matched_transition = resolve_transition(
                current_state=current_status,
                event=event,
                actor_role=actor_role,
                context=ctx,
            )
        except LeaveDomainError as err:
            raise _translate_error(err) from err

        target_status = matched_transition.to_state

        # Apply state change
        req.status = target_status.value
        req.save(update_fields=["status", "updated_at"])

        # Write audit trail
        LeaveAuditEvent.objects.create(
            request=req,
            event=event.value,
            from_state=current_status.value,
            to_state=target_status.value,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            remarks=remarks,
        )

        # Atomic ledger movements based on final state outcomes
        # 1. On final approval: debit the balance if not already debited
        if target_status == RequestStatus.APPROVED and current_status != RequestStatus.APPROVED:
            LeaveLedgerEntry.objects.create(
                user_id=req.user_id,
                category=req.category,
                delta_days=-req.days_count,
                transaction_type=LedgerTransactionType.DEBIT.value,
                reason=f"Leave application approved ({req.category} from {req.start_date} to {req.end_date})",
                reference_id=str(req.id),
                created_by_user_id=actor_user_id,
            )

        # 2. On cancellation approval: restore the deducted balance (BR-EL-023)
        if target_status == RequestStatus.CANCELLED and current_status != RequestStatus.CANCELLED:
            LeaveLedgerEntry.objects.create(
                user_id=req.user_id,
                category=req.category,
                delta_days=req.days_count,
                transaction_type=LedgerTransactionType.RESTORATION.value,
                reason=f"Restoration upon cancellation of leave request #{req.id} (BR-EL-023)",
                reference_id=str(req.id),
                created_by_user_id=actor_user_id,
            )

        return req
