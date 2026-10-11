"""Policy configuration service (BR-EL-030).

The single ``PolicyConfig`` row is the current configuration —
there is no draft/publish lifecycle, and a change applies to
requests submitted from the next moment. The baseline
entitlements from the problem statement (PS §3) seed a fresh
installation; what validation reads is whatever the
Leave Administrator has configured.
"""
from __future__ import annotations

from decimal import Decimal

from modules.elm.domain import routing as routing_domain
from modules.elm.domain.leave_types import (
    BASELINE_ENTITLEMENTS,
    CATEGORIES,
    KIND_FACULTY,
    VL,
)
from modules.elm.models import PolicyConfig


def current_policy() -> PolicyConfig:
    """The current policy row, seeded from the baseline on
    first read."""
    policy, _ = PolicyConfig.objects.get_or_create(
        id=1,
        defaults={
            "entitlements": _serialize(BASELINE_ENTITLEMENTS),
            "director_designations": [
                routing_domain.DIRECTOR_DESIGNATION],
            "establishment_designations": [
                "Deputy Registrar (Estt.)"],
        },
    )
    return policy


def _serialize(base: dict) -> dict:
    """Decimals cannot live in a JSONField."""
    out: dict = {}
    for category, params in base.items():
        out[category] = {
            key: (str(value) if isinstance(value, Decimal)
                  else value)
            for key, value in params.items()
            if value is not None
        }
    return out


def _raw(category: str) -> dict:
    policy = current_policy()
    return policy.entitlements.get(category) or \
        _serialize(BASELINE_ENTITLEMENTS).get(category, {})


def entitlement_for(category: str,
                    employee_kind: str | None = None) -> Decimal:
    """Annual entitlement in days.

    VL is faculty-only: a staff member's VL entitlement is
    zero, which is what makes the submission guard (BR-EL-006)
    and the balance check agree.
    """
    if category not in CATEGORIES:
        return Decimal("0")
    if category == VL and employee_kind not in (None, KIND_FACULTY):
        return Decimal("0")
    raw = _raw(category).get("annual_days")
    return Decimal(str(raw)) if raw is not None else Decimal("0")


def carry_forward_enabled(category: str) -> bool:
    return bool(_raw(category).get("carry_forward"))


def half_day_enabled(category: str) -> bool:
    return bool(_raw(category).get("half_day"))


def vl_conversion_ratio() -> Decimal:
    raw = _raw(VL).get("conversion_ratio")
    return Decimal(str(raw)) if raw is not None else Decimal("2")


def director_designations() -> list[str]:
    return list(current_policy().director_designations or
                [routing_domain.DIRECTOR_DESIGNATION])


def establishment_designations() -> list[str]:
    return list(
        current_policy().establishment_designations or
        ["Deputy Registrar (Estt.)"])


def year_end_boundary() -> str:
    return current_policy().year_end_month_day or "03-31"


def leave_year_for(day, boundary_md: str | None = None) -> str:
    """Which leave-year a date belongs to (PS §3).

    The leave year runs from the day after the boundary to
    the boundary: with the default 03-31 boundary, 2026-04-01
    opens leave-year 2026-27 and 2026-03-01 still belongs to
    2025-26.
    """
    boundary_md = boundary_md or year_end_boundary()
    month, day_of_month = (int(part)
                           for part in boundary_md.split("-"))
    boundary = day.__class__(day.year, month, day_of_month)
    if day >= boundary:
        return f"{day.year}-{str(day.year + 1)[2:]}"
    return f"{day.year - 1}-{str(day.year)[2:]}"


def next_leave_year(leave_year: str) -> str:
    start = int(leave_year.split("-", maxsplit=1)[0]) + 1
    return f"{start}-{str(start + 1)[2:]}"
