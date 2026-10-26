"""Year-end processing (EL-UC-020): lapse, convert, carry; exceptions reported, never guessed."""
from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from modules.directory import contracts as directory
from modules.leave.domain import categories as cat
from modules.leave.domain import state_machine as sm
from modules.leave.domain import yearend as ye
from modules.leave.models import PENDING_STATES, LeaveRequest, LedgerEntry, YearEndRun
from modules.leave.services import accounts, configuration

log = logging.getLogger("fusion.leave.yearend")


def run(year: int) -> YearEndRun:
    """Idempotent: a completed account is skipped by its keys, an excepted one retried next run."""
    record, _ = YearEndRun.objects.get_or_create(year=year)
    if record.status == "completed":
        return record
    user_ids = sorted(set(LedgerEntry.objects.filter(leave_year=year)
                          .values_list("user_id", flat=True)))
    exceptions, written = [], 0
    for uid in user_ids:
        try:
            written += _close_account(uid, year)
        except _Exception as exc:
            exceptions.append({"user_id": uid, "reason": str(exc)})
    record.accounts_processed = len(user_ids)
    record.entries_written += written
    record.exceptions = exceptions
    record.status = "completed_with_exceptions" if exceptions else "completed"
    record.finished_at = timezone.now()
    record.save()
    log.info("leave.yearend year=%s accounts=%d entries=%d exceptions=%d", year,
             len(user_ids), written, len(exceptions))
    return record


class _Exception(Exception):
    """An account that cannot be closed consistently this run."""


@transaction.atomic
def _close_account(user_id: int, year: int) -> int:
    accounts.lock(user_id)
    in_flight = LeaveRequest.objects.filter(
        user_id=user_id, leave_year=year, status__in=PENDING_STATES).count()
    if in_flight:
        raise _Exception(f"{in_flight} request(s) charged to {year} are still undecided.")
    if LeaveRequest.objects.filter(user_id=user_id, leave_year=year, kind=sm.NEW,
                                   status=sm.APPROVED, resumption__status="review_pending"
                                   ).exists():
        raise _Exception(f"A resumption for {year} leave is still awaiting review.")
    held = accounts.balances([user_id], year)[user_id]
    try:
        moves = ye.outcome(held)
    except ValueError as exc:
        raise _Exception(str(exc)) from exc
    written = 0
    for m in moves:
        booked = year + 1 if m.next_year else year
        if accounts.post(user_id=user_id, year=booked, category=m.category, delta=m.delta,
                         entry_type=m.entry_type,
                         key=f"yearend:{year}:{user_id}:{m.entry_type}:{m.category}",
                         note=f"Year-end {year}") is not None:
            written += 1
    return written


def is_closed(user_id: int, year: int) -> bool:
    """Closed for this account: its year-end entries exist, or the whole run completed."""
    return (YearEndRun.objects.filter(year=year, status="completed").exists()
            or LedgerEntry.objects.filter(
                user_id=user_id, idempotency_key__startswith=f"yearend:{year}:{user_id}:")
            .exists())


def booking_for(user_id: int, year: int, category: str,
                delta: Decimal) -> tuple[int, str, Decimal]:
    """Where a late change to a closed year's balance belongs: carried EL/COL into the next
    year as is, VL as the EL it converted into (BR-EL-007/008); a lapsed balance stays put."""
    rule = cat.get(category).year_end
    while delta and rule != cat.LAPSE and is_closed(user_id, year):
        if rule == cat.CONVERT:
            category, rule = cat.EL, cat.get(cat.EL).year_end
            delta = (delta / cat.VL_PER_EL).quantize(Decimal("0.01"))
        year += 1
    return year, category, delta


def credit_year(year: int) -> int:
    """The new year's entitlement for every serving employee the directory knows."""
    policy = configuration.current_policy(required=False)
    if policy is None:
        return 0
    kinds = {e.user_id: e.kind for e in directory.get_employees()}
    made = 0
    for uid, kind in sorted(kinds.items()):
        with transaction.atomic():
            accounts.lock(uid, employee_kind=kind)
            made += accounts.ensure_annual_credit(user_id=uid, employee_kind=kind, year=year,
                                                  policy=policy)
    return made
