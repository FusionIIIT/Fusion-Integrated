"""Offline-sanctioned leave records (EL-UC-017).

For leave that was sanctioned on paper while ELM was
unavailable. The sanction evidence is mandatory, the
entry is checked for record consistency against what
the book already holds, and a validated entry posts
straight to the ledger. It deliberately carries **no
workflow** and grants **no sanctioning power** —
recording a sanction is synchronization, not approval
(BR-EL-037).
"""
from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.elm.domain.errors import RecordInconsistent
from modules.elm.domain.policy import (
    LeaveInterval,
    count_days,
    intervals_overlap,
)
from modules.elm.models import (
    LeaveAccount,
    LeaveRecord,
    OfflineLeaveRecord,
)
from modules.elm.selectors.requests import closed_dates
from modules.elm.services import authz, workflow

log = logging.getLogger("fusion.elm.offline")

ZERO = Decimal("0")


@transaction.atomic
def record_offline(principal, *, user_id: int,
                     category: str, start_date, end_date,
                     start_half: str = "full",
                     end_half: str = "full",
                     sanction_reference: str,
                     sanction_date,
                     sanctioning_authority: str,
                     evidence_description: str,
                     reason_elm_unavailable: str,
                     ) -> OfflineLeaveRecord:
    """Record an already-sanctioned leave interval."""
    authz.require_permission(principal, "elm.records.offline")

    if not evidence_description.strip():
        raise ConflictError(
            "The sanction evidence is mandatory for an "
            "offline record.", code="evidence_required")
    if not sanction_reference.strip():
        raise ConflictError(
            "The sanction reference is mandatory for an "
            "offline record.", code="reference_required")
    if end_date < start_date:
        raise ConflictError(
            "The recorded period ends before it starts.",
            code="invalid_period")

    interval = LeaveInterval(
        category=category, start=start_date, end=end_date,
        start_half=start_half, end_half=end_half)
    days = count_days(interval, closed=closed_dates())
    if days <= ZERO:
        raise ConflictError(
            "The recorded period contains no countable "
            "leave days.", code="no_countable_days")

    # Record-consistency validation: the entry must not
    # contradict what the book already holds.
    overlaps = []
    for record in LeaveRecord.objects.filter(
            user_id=user_id, status="ongoing"):
        record_interval = LeaveInterval(
            category=record.category,
            start=record.start_date, end=record.end_date,
            start_half=record.start_half,
            end_half=record.end_half)
        if intervals_overlap(interval, record_interval):
            overlaps.append(
                {"record_id": record.id,
                 "category": record.category,
                 "start": str(record.start_date),
                 "end": str(record.end_date)})
    if overlaps:
        raise RecordInconsistent(
            "The entry overlaps leave already on record.",
        )

    entry = OfflineLeaveRecord.objects.create(
        user_id=user_id, category=category,
        start_date=start_date, end_date=end_date,
        start_half=start_half, end_half=end_half,
        days=days, sanction_reference=sanction_reference,
        sanction_date=sanction_date,
        sanctioning_authority=sanctioning_authority,
        evidence_description=evidence_description,
        reason_elm_unavailable=reason_elm_unavailable,
        recorded_by_user_id=principal.user_id,
        consistency_check={
            "checked_at": str(timezone.now()),
            "checked_by": principal.user_id,
            "overlaps": [],
            "countable_days": str(days),
        },
    )

    # Post to the ledger and the book.
    account, _ = LeaveAccount.objects.get_or_create(
        user_id=user_id,
        leave_year=workflow.policy_service.leave_year_for(
            start_date),
        category=category)
    account.used_days += days
    account.save()
    workflow._ledger(
        account, delta=-days, kind="offline_record",
        offline_record=entry, actor=principal.user_id,
        reason=(f"Offline-sanctioned leave recorded "
                f"({sanction_reference})"))
    record = LeaveRecord.objects.create(
        user_id=user_id,
        leave_year=account.leave_year,
        category=category, start_date=start_date,
        end_date=end_date, start_half=start_half,
        end_half=end_half, days=days, status="ongoing",
        offline_record=entry,
    )
    entry.leave_record = record
    entry.save(update_fields=["leave_record"])
    workflow._log(
        None, "balance_posted", actor=principal.user_id,
        actor_label=authz.user_label(principal),
        outcome="offline_record",
        payload={"entry_id": entry.id,
                 "record_id": record.id,
                 "days": str(days)})
    return entry


def _translate(exc: Exception) -> Exception:
    if isinstance(exc, RecordInconsistent):
        return ConflictError(
            str(exc), code="record_inconsistent",
            details=[])
    return exc
