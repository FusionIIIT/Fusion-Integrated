"""Balance selectors — read-only, no authorization here.

The architecture's own line: a selector decides what a caller can
*see*; the view decides whether they may look at all. Ownership is
enforced by narrowing the queryset, so a foreign ``user_id``
returns an empty result (a visible 404 up the stack), never a
403 from inside the data layer.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from django.db.models import Sum

from modules.elm.contracts import LeaveBalanceDTO
from modules.elm.domain.leave_types import TERMINAL_STATES
from modules.elm.models import LeaveAccount, LeaveRequest

ZERO = Decimal("0")


def balances_for(user_ids: set[int],
                 leave_year: str) -> dict[int, list[LeaveBalanceDTO]]:
    """Balances for a batch of people in one leave year.

    Pending (non-terminal) requests reserve their days, so the
    available balance a caller reads can never be double-booked.
    """
    accounts = LeaveAccount.objects.filter(
        user_id__in=user_ids, leave_year=leave_year)

    pending = defaultdict(Decimal)
    open_requests = LeaveRequest.objects.filter(
        user_id__in=user_ids, leave_year=leave_year,
    ).exclude(status__in=TERMINAL_STATES).values(
        "user_id", "category").annotate(
        reserved=Sum("days"))
    for row in open_requests:
        pending[(row["user_id"], row["category"])] = row["reserved"] or ZERO

    out: dict[int, list[LeaveBalanceDTO]] = defaultdict(list)
    for account in accounts:
        out[account.user_id].append(
            LeaveBalanceDTO(
                user_id=account.user_id,
                leave_year=account.leave_year,
                category=account.category,
                opening_days=account.opening_days,
                entitled_days=account.entitled_days,
                used_days=account.used_days,
                pending_days=pending.get(
                    (account.user_id, account.category), ZERO),
            )
        )
    return dict(out)


def balance_for(user_id: int, leave_year: str,
                category: str) -> LeaveBalanceDTO | None:
    """One account, with its pending reservation."""
    try:
        account = LeaveAccount.objects.get(
            user_id=user_id, leave_year=leave_year, category=category)
    except LeaveAccount.DoesNotExist:
        return None
    reserved = LeaveRequest.objects.filter(
        user_id=user_id, leave_year=leave_year, category=category,
    ).exclude(status__in=TERMINAL_STATES).aggregate(
        reserved=Sum("days"))["reserved"] or ZERO
    return LeaveBalanceDTO(
        user_id=account.user_id,
        leave_year=account.leave_year,
        category=account.category,
        opening_days=account.opening_days,
        entitled_days=account.entitled_days,
        used_days=account.used_days,
        pending_days=reserved,
    )
