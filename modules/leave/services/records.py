"""Record maintenance and offline synchronization (EL-UC-016, EL-UC-017).

Neither of these creates a sanctioning decision, which is exactly why they are
separate from every review path: BR-EL-037 says a correction must never read as
an approval when somebody reads the history later.
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from django.db import transaction

from core.api.exceptions import ConflictError
from modules.leave.domain import categories as cat
from modules.leave.domain import counting
from modules.leave.domain import ledger as led
from modules.leave.domain.errors import RuleViolation
from modules.leave.models import LeaveAccount, LeaveRecordAdjustment, OfflineLeaveRecord
from modules.leave.services import accounts as account_service
from modules.leave.services import authz

log = logging.getLogger("fusion.leave.records")


@transaction.atomic
def record_offline(*, actor, user_id: int, category: str, start_date: date,
                   end_date: date, days, sanction_reference: str,
                   evidence_note: str = "", is_faculty: bool = False
                   ) -> OfflineLeaveRecord:
    """BR-EL-029: synchronize a paper sanction, do not sanction it again."""
    authz.require(actor, "leave.record.update")
    if not cat.is_known(category):
        raise ConflictError(f"'{category}' is not a leave category.",
                            code="unknown_category")
    if not (sanction_reference or "").strip():
        raise ConflictError(
            "Record the sanction reference from the paper file: this entry "
            "synchronizes a decision, it does not make one.",
            code="sanction_reference_required")
    try:
        expected = counting.count_days(category=category, start=start_date,
                                       end=end_date)
    except RuleViolation as exc:
        raise ConflictError(exc.message, code=exc.code) from exc

    recorded = Decimal(str(days)) if days is not None else expected
    if recorded != expected:
        raise ConflictError(
            f"The recorded days ({recorded}) do not match the period "
            f"({expected} day(s)) for this category.",
            code="record_inconsistent")

    account_service.open_year(user_id=user_id, year=start_date.year,
                              is_faculty=is_faculty,
                              actor_user_id=getattr(actor, "user_id", None))
    account = account_service.ensure_account(user_id=user_id,
                                             year=start_date.year,
                                             category=category)
    account_service.post(account=account, entry_type=led.DEBIT, days=recorded,
                         reference=f"offline:{sanction_reference}"[:64],
                         reason="Already sanctioned offline",
                         actor_user_id=getattr(actor, "user_id", None))

    row = OfflineLeaveRecord.objects.create(
        user_id=user_id, category=category, start_date=start_date,
        end_date=end_date, days=recorded, sanction_reference=sanction_reference,
        evidence_note=evidence_note,
        recorded_by_user_id=getattr(actor, "user_id", None), balance_synced=True,
    )
    log.info("leave.records.offline u=%s category=%s days=%s ref=%s", user_id,
             category, recorded, sanction_reference)
    return row


@transaction.atomic
def adjust_balance(*, actor, user_id: int, category: str, year: int, days,
                   reason: str, reversal: bool = False) -> LeaveRecordAdjustment:
    """EL-UC-017: a correction, recorded as a correction (BR-EL-037)."""
    authz.require(actor, "leave.record.update")
    if not (reason or "").strip():
        raise ConflictError("A correction needs a reason.", code="reason_required")
    if not cat.is_known(category):
        raise ConflictError(f"'{category}' is not a leave category.",
                            code="unknown_category")

    account = account_service.ensure_account(user_id=user_id, year=year,
                                             category=category)
    entry_type = led.REVERSAL if reversal else led.ADJUSTMENT
    entry = account_service.post(
        account=account, entry_type=entry_type, days=days,
        reference=f"adjustment:{getattr(actor, 'user_id', None)}",
        reason=reason, actor_user_id=getattr(actor, "user_id", None))

    return LeaveRecordAdjustment.objects.create(
        user_id=user_id, account=account, entry_type="reversal" if reversal
        else "adjustment", days=entry.days, reason=reason,
        actor_user_id=getattr(actor, "user_id", None))


def offline_records(*, user_id: int | None = None):
    qs = OfflineLeaveRecord.objects.order_by("-id")
    if user_id is not None:
        qs = qs.filter(user_id=user_id)
    return qs


def accounts_for_admin(*, user_id: int, year: int) -> list[LeaveAccount]:
    return list(LeaveAccount.objects.filter(user_id=user_id, year=year)
                .order_by("category"))
