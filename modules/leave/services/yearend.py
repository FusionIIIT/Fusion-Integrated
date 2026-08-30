"""Closing a leave year for one employee.

SF-EL-001, BR-EL-007. Lapse what does not carry, carry what does, and convert
unused vacation leave. Every movement is a ledger row, so a year that was
closed wrongly can be corrected by reversing entries rather than by editing
figures nobody can later explain.

The run is idempotent per employee and year: it refuses to close a year that
already carries closing entries.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from core.api.exceptions import ConflictError
from modules.leave.domain.categories import Category
from modules.leave.domain.entitlement import Balance, close_year
from modules.leave.models import EntryReason, LedgerEntry
from modules.leave.selectors import balances
from modules.leave.selectors import policy as policy_selector

ZERO = Decimal("0")
_CLOSING = (
    EntryReason.LAPSED,
    EntryReason.CONVERTED_OUT,
    EntryReason.CONVERTED_IN,
)


def already_closed(user_id: int, year: int) -> bool:
    return LedgerEntry.objects.filter(
        user_id=user_id, year=year, reason__in=_CLOSING
    ).exists()


@transaction.atomic
def close(*, user_id: int, year: int, faculty: bool) -> dict[str, Decimal]:
    """Settle the year and open the next one. Returns what moved."""
    if already_closed(user_id, year):
        raise ConflictError(
            f"{year} is already closed for this employee.", code="year_already_closed"
        )

    from datetime import date

    policy = policy_selector.effective_policy(date(year, 12, 31))
    rounding, _ = policy_selector.conversion_settings(policy)
    category_policies = policy_selector.category_policies(policy, faculty=faculty)
    held = balances.balances_for(user_id, year)
    # A category the policy grants but the employee never touched still has to
    # be settled, and vacation converts into an EL balance that may not exist.
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

    return {
        "lapsed": sum(outcome.lapsed.values()),
        "carried": sum(outcome.carried.values()),
        "converted_vl": outcome.converted_vl,
        "el_from_conversion": outcome.el_from_conversion,
    }


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
    LedgerEntry.objects.bulk_create(rows)
    return len(rows)
