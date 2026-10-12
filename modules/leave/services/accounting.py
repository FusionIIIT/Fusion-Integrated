"""Entitlement provisioning and idempotent year-end account processing."""
from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from modules.leave.domain.eligibility import annual_entitlement
from modules.leave.models import (
    EmployeeProfile, LeaveAccountEntry, LeaveBalance, LeaveCategory,
    LeavePolicy,
)
from modules.leave.services.requests import LeaveRuleViolation, _post_entry

log = logging.getLogger("fusion.leave.accounting")


@transaction.atomic
def provision_year(year: int, *, actor_user_id: int | None = None) -> int:
    """Credit configured annual entitlements once for every active employee."""
    policy = LeavePolicy.objects.filter(policy_key="current").first()
    if not policy:
        raise LeaveRuleViolation("Leave policy has not been configured")
    count = 0
    categories = {item.code: item for item in LeaveCategory.objects.all()}
    for employee in EmployeeProfile.objects.filter(active=True).order_by("user_id").iterator():
        for code in ("CL", "RH", "SCL", "EL", "COL", "VL"):
            category = categories.get(code)
            if category is None:
                continue
            credit = annual_entitlement(code, employee.kind, policy)
            if credit <= 0:
                LeaveBalance.objects.get_or_create(employee_id=employee.user_id, category=category, year=year)
                continue
            before = LeaveAccountEntry.objects.filter(source_key=f"entitlement:{employee.user_id}:{code}:{year}").exists()
            _post_entry(employee_id=employee.user_id, category=category, year=year,
                        amount=credit, kind=LeaveAccountEntry.Kind.ENTITLEMENT,
                        source_key=f"entitlement:{employee.user_id}:{code}:{year}",
                        actor_user_id=actor_user_id, explanation="Annual leave entitlement")
            count += int(not before)
    return count


@transaction.atomic
def process_year_end(year: int, *, actor_user_id: int | None = None) -> dict[str, int]:
    """Close accounts idempotently and open next-year balances.

    CL/RH/SCL lapse. EL and COL carry at 1:1. Faculty VL is removed and
    converted to EL at 2:1. Each close and credit is persisted as ledger rows.
    """
    if year >= 9999:
        raise LeaveRuleViolation("Invalid leave year")
    totals = {"closed": 0, "carried": 0, "vl_converted": 0, "lapsed": 0, "exceptions": 0}
    balances = list(LeaveBalance.objects.select_for_update().filter(year=year).select_related("category").order_by("employee_id", "category_id"))
    profiles = {p.user_id: p for p in EmployeeProfile.objects.filter(user_id__in={b.employee_id for b in balances})}
    by_code = {item.code: item for item in LeaveCategory.objects.all()}
    for balance in balances:
        if balance.available < 0:
            totals["exceptions"] += 1
            log.error("Negative leave balance at year end", extra={
                "employee_id": balance.employee_id, "category": balance.category_id,
                "year": year, "available": str(balance.available),
            })
            continue
        amount = max(balance.available, Decimal("0"))
        if amount == 0:
            continue
        code = balance.category_id
        profile = profiles.get(balance.employee_id)
        if code == "VL" and profile is None:
            totals["exceptions"] += 1
            log.error("Missing employee projection for VL year-end", extra={
                "employee_id": balance.employee_id, "year": year,
            })
            continue
        if code == "VL" and profile.kind == "faculty":
            converted = amount / Decimal("2")
            _close_old_balance(balance, amount, year, actor_user_id, "Unused VL converted",
                               LeaveAccountEntry.Kind.VL_CONVERSION)
            if converted:
                _post_entry(employee_id=balance.employee_id, category=by_code["EL"], year=year + 1,
                            amount=converted, kind=LeaveAccountEntry.Kind.VL_CONVERSION,
                            source_key=f"yearend:{year}:{balance.employee_id}:vl-to-el",
                            actor_user_id=actor_user_id,
                            explanation="Unused VL converted to EL at 2:1")
                totals["vl_converted"] += 1
            totals["closed"] += 1
        elif code in {"EL", "COL"}:
            _close_old_balance(balance, amount, year, actor_user_id, f"{code} carried forward",
                               LeaveAccountEntry.Kind.CARRY_FORWARD)
            _post_entry(employee_id=balance.employee_id, category=balance.category,
                        year=year + 1, amount=amount,
                        kind=LeaveAccountEntry.Kind.CARRY_FORWARD,
                        source_key=f"yearend:{year}:{balance.employee_id}:{code}:carry-in",
                        actor_user_id=actor_user_id, explanation=f"Unused {code} carried forward")
            totals["carried"] += 1
            totals["closed"] += 1
        else:
            _close_old_balance(balance, amount, year, actor_user_id, f"Unused {code} lapsed",
                               LeaveAccountEntry.Kind.YEAR_END_LAPSE)
            totals["lapsed"] += 1
            totals["closed"] += 1
    totals["entitlements_issued"] = provision_year(year + 1, actor_user_id=actor_user_id)
    return totals


def _close_old_balance(balance, amount, year, actor_user_id, explanation, kind):
    _post_entry(employee_id=balance.employee_id, category=balance.category, year=year,
                amount=-amount, kind=kind,
                source_key=f"yearend:{year}:{balance.employee_id}:{balance.category_id}:close",
                actor_user_id=actor_user_id, explanation=explanation)
