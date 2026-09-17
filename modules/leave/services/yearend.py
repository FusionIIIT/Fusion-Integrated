"""Closing a leave year for one employee."""
from __future__ import annotations

from decimal import Decimal

from django.db import IntegrityError, transaction

from core.api.exceptions import ConflictError
from modules.leave.domain.categories import Category
from modules.leave.domain.entitlement import Balance, close_year
from modules.leave.models import EntryReason, LedgerEntry, YearEndClosure
from modules.leave.selectors import balances
from modules.leave.selectors import policy as policy_selector

ZERO = Decimal("0")
_CLOSING = (
    EntryReason.LAPSED,
    EntryReason.CONVERTED_OUT,
    EntryReason.CONVERTED_IN,
)


def already_closed(user_id: int, year: int) -> bool:
    """Read the closure record, not the entries it happened to write."""
    return YearEndClosure.objects.filter(user_id=user_id, year=year).exists()


@transaction.atomic
def close(*, user_id: int, year: int, faculty: bool) -> dict[str, Decimal]:
    """Settle the year and open the next one. Returns what moved."""
    try:
        closure = YearEndClosure.objects.create(user_id=user_id, year=year)
    except IntegrityError as exc:
        # The unique constraint, not a prior read, stops a double close.
        raise ConflictError(
            f"{year} is already closed for this employee.", code="year_already_closed"
        ) from exc

    from datetime import date

    policy = policy_selector.effective_policy(date(year, 12, 31))
    rounding, _ = policy_selector.conversion_settings(policy)
    category_policies = policy_selector.category_policies(policy, faculty=faculty)
    held = balances.balances_for(user_id, year)
    # Settle untouched categories, and give conversion an EL balance.
    for category in category_policies:
        held.setdefault(category, Balance(category=category))
    held.setdefault(Category.EL, Balance(category=Category.EL))

    outcome = close_year(
        held,
        category_policies,
        vl_to_el_ratio=policy.vl_to_el_ratio if faculty else None,
        rounding=rounding,
    )

    rows: list[LedgerEntry] = []
    for category, days in outcome.lapsed.items():
        if days > ZERO:
            rows.append(
                LedgerEntry(
                    user_id=user_id, year=year, category=category.value, days=-days,
                    reason=EntryReason.LAPSED, policy_id=policy.pk,
                    note=f"lapsed at the end of {year}",
                )
            )
    if outcome.converted_vl > ZERO:
        rows.append(
            LedgerEntry(
                user_id=user_id, year=year, category=Category.VL.value,
                days=-outcome.converted_vl, reason=EntryReason.CONVERTED_OUT,
                policy_id=policy.pk,
                note=f"converted at {policy.vl_to_el_ratio.normalize()} VL to 1 EL",
            )
        )
        rows.append(
            LedgerEntry(
                user_id=user_id, year=year, category=Category.EL.value,
                days=outcome.el_from_conversion, reason=EntryReason.CONVERTED_IN,
                policy_id=policy.pk,
                note=f"from {outcome.converted_vl} unused VL",
            )
        )
    for category, days in outcome.carried.items():
        if days > ZERO:
            rows.append(
                LedgerEntry(
                    user_id=user_id, year=year + 1, category=category.value, days=days,
                    reason=EntryReason.OPENING_BALANCE, policy_id=policy.pk,
                    note=f"carried from {year}",
                )
            )
    LedgerEntry.objects.bulk_create(rows)

    moved = {
        "lapsed": sum(outcome.lapsed.values()),
        "carried": sum(outcome.carried.values()),
        "converted_vl": outcome.converted_vl,
        "el_from_conversion": outcome.el_from_conversion,
    }
    closure.policy_id = policy.pk
    for field, value in moved.items():
        setattr(closure, field, value)
    closure.save(update_fields=[*moved, "policy_id", "updated_at"])
    return moved


@transaction.atomic
def credit_year(*, user_id: int, year: int, faculty: bool) -> int:
    """Give the annual entitlement for a new year. Returns rows written."""
    from datetime import date

    policy = policy_selector.effective_policy(date(year, 1, 1))
    settings = policy_selector.category_policies(policy, faculty=faculty)
    existing = set(
        LedgerEntry.objects.filter(
            user_id=user_id, year=year, reason=EntryReason.ANNUAL_CREDIT
        ).values_list("category", flat=True)
    )
    rows = [
        LedgerEntry(
            user_id=user_id, year=year, category=category.value,
            days=setting.annual_credit, reason=EntryReason.ANNUAL_CREDIT,
            policy_id=policy.pk, note=f"annual credit for {year}",
        )
        for category, setting in settings.items()
        if setting.annual_credit > ZERO and category.value not in existing
    ]
    if not rows:
        return 0
    before = LedgerEntry.objects.filter(
        user_id=user_id, year=year, reason=EntryReason.ANNUAL_CREDIT
    ).count()
    # The read keeps the common case cheap; the constraint makes races safe.
    LedgerEntry.objects.bulk_create(rows, ignore_conflicts=True)
    after = LedgerEntry.objects.filter(
        user_id=user_id, year=year, reason=EntryReason.ANNUAL_CREDIT
    ).count()
    return after - before


@transaction.atomic
def revoke_credit(*, user_id: int, year: int, actor_user_id: int, note: str) -> int:
    """Undo a year's credit for somebody who should never have had it."""
    if already_closed(user_id, year):
        # Closing has already lapsed, converted and carried this credit into the next year.
        raise ConflictError(
            f"{year} is closed for this employee. The credit has already been "
            "lapsed, converted or carried forward, so it cannot be reversed on "
            "its own.",
            code="year_already_closed",
        )
    credited = list(
        LedgerEntry.objects.filter(
            user_id=user_id, year=year, reason=EntryReason.ANNUAL_CREDIT
        ).exclude(pk__in=_already_reversed(user_id, year))
    )
    if not credited:
        return 0

    spent = LedgerEntry.objects.filter(
        user_id=user_id, year=year, reason=EntryReason.CONSUMED
    ).exists()
    if spent:
        raise ConflictError(
            f"{user_id} has already used leave in {year}. Revoking the credit "
            "would leave a negative balance; settle the leave first.",
            code="credit_already_spent",
        )

    LedgerEntry.objects.bulk_create([
        LedgerEntry(
            user_id=user_id, year=year, category=entry.category, days=-entry.days,
            reason=EntryReason.CORRECTION, policy_id=entry.policy_id,
            reverses_id=entry.pk, recorded_by_user_id=actor_user_id, note=note,
        )
        for entry in credited
    ])
    return len(credited)


def _already_reversed(user_id: int, year: int) -> set[int]:
    return set(
        LedgerEntry.objects.filter(
            user_id=user_id, year=year, reason=EntryReason.CORRECTION
        ).exclude(reverses_id=None).values_list("reverses_id", flat=True)
    )
