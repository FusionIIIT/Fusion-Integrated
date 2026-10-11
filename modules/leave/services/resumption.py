"""Resumption service for duty return review.

Implements CW-EL-04, EL-UC-010, EL-UC-011, BR-EL-027, BR-EL-028.
"""

from datetime import date
from decimal import Decimal

from django.db import transaction

from core.api.exceptions import BadRequestError
from fusion_auth.principal import Principal
from modules.leave.domain.constants import (
    Event,
    LedgerTransactionType,
    RequestStatus,
    ResumptionType,
)
from modules.leave.models.ledger import LeaveLedgerEntry
from modules.leave.models.resumptions import LeaveResumption
from modules.leave.selectors.requests import get_request_by_id
from modules.leave.services.transitions import execute_transition


def submit_resumption_of_duty(
    request_id: int,
    actual_resumption_date: date,
    principal: Principal,
    remarks: str = "",
) -> LeaveResumption:
    """Employee declares actual duty return after EL/COL/VL (EL-UC-010 / BR-EL-027)."""
    req = get_request_by_id(request_id, principal)

    if req.user_id != principal.user_id:
        raise BadRequestError("Only the applicant may submit resumption for this leave.")

    if actual_resumption_date < req.start_date:
        raise BadRequestError("Actual resumption date cannot be earlier than leave start date.")

    # Determine resumption type
    if actual_resumption_date == req.end_date:
        res_type = ResumptionType.NORMAL
    elif actual_resumption_date < req.end_date:
        res_type = ResumptionType.EARLY
    else:
        res_type = ResumptionType.LATE

    with transaction.atomic():
        res = LeaveResumption.objects.create(
            request=req,
            actual_resumption_date=actual_resumption_date,
            resumption_type=res_type.value,
            status=RequestStatus.RESUMPTION_REVIEW_PENDING.value,
            remarks=remarks,
        )

        execute_transition(
            request_id=req.id,
            event=Event.SUBMIT_RESUMPTION,
            actor_user_id=principal.user_id,
            actor_role="applicant",
            remarks=f"Submitted resumption of duty on {actual_resumption_date} ({res_type.value})",
        )

        return res


def review_resumption(
    resumption_id: int,
    principal: Principal,
    remarks: str = "",
) -> LeaveResumption:
    """Sanctioning authority reviews resumption and applies ledger synchronization (BR-EL-028)."""
    res = LeaveResumption.objects.select_for_update().get(id=resumption_id)
    req = res.request

    with transaction.atomic():
        if res.resumption_type == ResumptionType.NORMAL.value:
            event = Event.REVIEW_NORMAL
            res.status = RequestStatus.RESUMPTION_REVIEWED_NORMAL.value
            # Normal: no adjustment (BR-EL-028)
            res.days_adjustment = Decimal("0.0")

        elif res.resumption_type == ResumptionType.EARLY.value:
            event = Event.REVIEW_EARLY
            res.status = RequestStatus.RESUMPTION_REVIEWED_EARLY.value
            # Early return: calculate unavailed days and restore to ledger (BR-EL-028)
            unavailed_days = Decimal((req.end_date - res.actual_resumption_date).days)
            res.days_adjustment = unavailed_days
            # Update request end_date and days_count
            req.end_date = res.actual_resumption_date
            req.days_count -= unavailed_days
            req.save(update_fields=["end_date", "days_count", "updated_at"])

            LeaveLedgerEntry.objects.create(
                user_id=req.user_id,
                category=req.category,
                delta_days=unavailed_days,
                transaction_type=LedgerTransactionType.RESTORATION.value,
                reason=f"Restoration for early resumption from leave #{req.id} (BR-EL-028)",
                reference_id=str(req.id),
                created_by_user_id=principal.user_id,
            )

        else:  # LATE
            event = Event.REVIEW_LATE
            res.status = RequestStatus.RESUMPTION_REVIEWED_LATE.value
            # Late return: calculate extra days and debit from ledger (BR-EL-028)
            extra_days = Decimal((res.actual_resumption_date - req.end_date).days)
            res.days_adjustment = -extra_days
            req.end_date = res.actual_resumption_date
            req.days_count += extra_days
            req.save(update_fields=["end_date", "days_count", "updated_at"])

            LeaveLedgerEntry.objects.create(
                user_id=req.user_id,
                category=req.category,
                delta_days=-extra_days,
                transaction_type=LedgerTransactionType.DEBIT.value,
                reason=f"Debit for late resumption beyond leave #{req.id} (BR-EL-028)",
                reference_id=str(req.id),
                created_by_user_id=principal.user_id,
            )

        res.reviewed_by_user_id = principal.user_id
        res.save(update_fields=["status", "days_adjustment", "reviewed_by_user_id", "updated_at"])

        execute_transition(
            request_id=req.id,
            event=event,
            actor_user_id=principal.user_id,
            actor_role="sanctioning_authority",
            remarks=remarks or f"Resumption reviewed: {res.resumption_type}",
        )

        return res
