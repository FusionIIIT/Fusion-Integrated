"""Append-only leave ledger; balances are derived from entries."""
from decimal import Decimal
from django.db.models import Sum
from modules.directory import contracts as directory
from modules.elm.models import LeavePolicy, LedgerEntry
from modules.elm.domain.policy import merged_params, annual_credit_for


def current_policy():
    policy, _ = LeavePolicy.objects.get_or_create(key="current", defaults={"params": merged_params(None), "hierarchy": {}})
    if not policy.params:
        policy.params = merged_params(None)
        policy.save(update_fields=["params", "updated_at"])
    return policy


def ensure_annual_credits(user_id: int, year: int, kind: str | None = None) -> int:
    if kind is None:
        user = directory.get_users([user_id]).get(user_id)
        if not user or not user.is_active:
            return 0
        kind = user.kind
    if kind not in {"faculty", "staff"}:
        return 0
    policy = current_policy()
    created = 0
    for category in ("CL", "RH", "SCL", "EL", "COL", "VL"):
        try:
            amount = annual_credit_for(category, kind, policy.params)
        except ValueError:
            continue
        _, was_created = LedgerEntry.objects.get_or_create(
            user_id=user_id, category=category, year=year, entry_type="annual_credit",
            defaults={"delta": amount, "note": "Annual entitlement credit"})
        created += int(was_created)
    return created


def balance(user_id: int, category: str, year: int | None = None) -> Decimal:
    qs = LedgerEntry.objects.filter(user_id=user_id, category=category)
    if year is not None:
        qs = qs.filter(year=year)
    return qs.aggregate(total=Sum("delta"))["total"] or Decimal("0")


def post_request_debit(request) -> None:
    LedgerEntry.objects.get_or_create(
        request=request, entry_type="debit",
        defaults={"user_id": request.user_id, "category": request.category,
                  "year": request.start_date.year, "delta": -request.days,
                  "note": "Approved leave"})


def reverse_request_debit(request, entry_type: str = "reversal") -> None:
    debit = LedgerEntry.objects.filter(request=request, entry_type="debit").first()
    if not debit:
        return
    LedgerEntry.objects.get_or_create(
        request=request, entry_type=entry_type,
        defaults={"user_id": request.user_id, "category": request.category,
                  "year": request.start_date.year, "delta": abs(debit.delta),
                  "note": "Leave debit reversed"})
