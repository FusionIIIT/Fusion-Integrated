"""Extension service for ongoing leave.

Implements CW-EL-03, EL-UC-009, BR-EL-025.
"""

from datetime import date, timedelta

from django.db import transaction

from core.api.exceptions import BadRequestError
from fusion_auth.principal import Principal
from modules.leave.domain.constants import (
    Event,
    LedgerTransactionType,
    RequestStatus,
    SubstituteStatus,
)
from modules.leave.domain.counting import calculate_leave_days
from modules.leave.domain.exceptions import LeaveDomainError
from modules.leave.domain.validation import (
    validate_balance,
    validate_extension_eligibility,
    validate_substitute,
)
from modules.leave.models.extensions import LeaveExtension
from modules.leave.models.ledger import LeaveLedgerEntry
from modules.leave.selectors.balances import get_category_balance
from modules.leave.selectors.calendar import get_closed_holidays
from modules.leave.selectors.requests import (
    get_request_by_id,
    get_substitute_active_intervals,
)
from modules.leave.services.transitions import _translate_error, execute_transition


def request_extension(
    request_id: int,
    extend_to: date,
    reason: str,
    principal: Principal,
    substitute_user_id: int | None = None,
    current_date: date | None = None,
) -> LeaveExtension:
    """Requests extension of ongoing EL/COL/VL (EL-UC-009 / BR-EL-025)."""
    req = get_request_by_id(request_id, principal)

    if req.user_id != principal.user_id:
        raise BadRequestError("Only the applicant may request an extension of this leave.")

    today = current_date or date.today()
    extend_from = req.end_date + timedelta(days=1)

    try:
        validate_extension_eligibility(
            category=req.category,
            original_start=req.start_date,
            original_end=req.end_date,
            extension_start=extend_from,
            extension_end=extend_to,
            current_date=today,
        )

        # Calculate incremental days
        year = extend_from.year
        closed_holidays = get_closed_holidays(year)
        incremental_days = calculate_leave_days(
            category=req.category,
            start_date=extend_from,
            end_date=extend_to,
            closed_holidays=closed_holidays,
        )

        # Check balance for incremental days
        bal = get_category_balance(req.user_id, req.category)
        validate_balance(bal, incremental_days, req.category)

        # Substitute check
        if substitute_user_id:
            sub_intervals = get_substitute_active_intervals(substitute_user_id)
            validate_substitute(
                req.user_id, substitute_user_id, sub_intervals, extend_from, extend_to
            )

    except LeaveDomainError as err:
        raise _translate_error(err) from err

    with transaction.atomic():
        sub_status = (
            SubstituteStatus.PENDING.value
            if substitute_user_id
            else SubstituteStatus.NOT_REQUIRED.value
        )
        ext = LeaveExtension.objects.create(
            request=req,
            extend_from=extend_from,
            extend_to=extend_to,
            incremental_days=incremental_days,
            reason=reason,
            substitute_user_id=substitute_user_id,
            substitute_status=sub_status,
            status=(
                RequestStatus.EXT_AWAITING_SUBSTITUTE.value
                if substitute_user_id
                else RequestStatus.EXT_AWAITING_UNIT_HEAD.value
            ),
        )

        context = {"needs_substitute": bool(substitute_user_id)}
        execute_transition(
            request_id=req.id,
            event=Event.REQUEST_EXTENSION,
            actor_user_id=principal.user_id,
            actor_role="applicant",
            remarks=(
                f"Requested extension from {extend_from} to {extend_to} "
                f"(+{incremental_days} days)"
            ),
            context=context,
        )

        return ext


def sanction_extension(
    extension_id: int,
    action: str,  # "approve" or "reject"
    principal: Principal,
    remarks: str = "",
) -> LeaveExtension:
    """Sanctioning authority decides leave extension (BR-EL-025)."""
    ext = LeaveExtension.objects.select_for_update().get(id=extension_id)
    req = ext.request

    if action not in ("approve", "reject"):
        raise BadRequestError("Decision must be 'approve' or 'reject'.")

    with transaction.atomic():
        if action == "approve":
            ext.status = RequestStatus.EXTENDED.value
            # Incremental period posted (BR-EL-025)
            req.end_date = ext.extend_to
            req.days_count += ext.incremental_days
            req.status = RequestStatus.EXTENDED.value
            req.save(update_fields=["end_date", "days_count", "status", "updated_at"])

            # Debit incremental days from ledger
            LeaveLedgerEntry.objects.create(
                user_id=req.user_id,
                category=req.category,
                delta_days=-ext.incremental_days,
                transaction_type=LedgerTransactionType.DEBIT.value,
                reason=(
                    f"Approved leave extension (+{ext.incremental_days} days "
                    f"to {ext.extend_to})"
                ),
                reference_id=str(req.id),
                created_by_user_id=principal.user_id,
            )
        else:
            ext.status = RequestStatus.EXTENSION_REJECTED.value
            # Original ongoing leave unchanged (BR-EL-025)
            req.status = RequestStatus.APPROVED.value
            req.save(update_fields=["status", "updated_at"])

        ext.save(update_fields=["status", "updated_at"])

        event = Event.APPROVE if action == "approve" else Event.REJECT
        execute_transition(
            request_id=req.id,
            event=event,
            actor_user_id=principal.user_id,
            actor_role="sanctioning_authority",
            remarks=remarks or f"Extension decision: {action}",
        )

        return ext
