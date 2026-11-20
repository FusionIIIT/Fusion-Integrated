"""PMS policy values (DEC-7).

Every operator-configurable number lives here. Values the six specifications
state explicitly carry a default; everything the PS says PMS must **not**
define — "the cost-escalation threshold, office-action response deadlines,
jurisdiction maintenance schedules, exact appeal deadline, exact
authorization hierarchy" (PS §2.4) — has **no default** and stays `None`
until an operator configures it. An absent value is never guessed.

Pure Python: no Django or DRF imports.
"""

from __future__ import annotations

import datetime
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

from .errors import PolicyConfigurationError

#: Every key an operator may configure. Anything else is a typo, not a policy.
CONFIG_KEYS: dict[str, str] = {
    "review_business_days": "Business days allowed for a Director review (BR-PMS-031).",
    "revision_days": "Calendar days allowed for resubmission (BR-PMS-035).",
    "alert_offsets": "Days-before-deadline at which an alert is raised (PMS-AFR-176..178).",
    "holiday_calendar": "Optional ISO dates excluded from business-day counting.",
    "budget_threshold": (
        "Cost above which a budget escalates (BR-PMS-051). Unset by default (PS 2.4)."
    ),
    "appeal_period_days": (
        "Days allowed to file an appeal (BR-PMS-093). Unset by default (PS 2.4)."
    ),
    "escalation_chain": (
        "Ordered recipients for a missed deadline (BR-PMS-104). Unset by default."
    ),
    "maintenance_schedule": (
        "Per-jurisdiction renewal cycles (BR-PMS-060). Unset by default (PS 2.4)."
    ),
}

#: Values the specifications state outright, so they are safe to default.
#: Only these three are seeded by migration.
SPECIFIED_DEFAULTS: dict[str, Any] = {
    "review_business_days": 15,  # BR-PMS-031
    "revision_days": 60,  # BR-PMS-035
    "alert_offsets": [30, 15, 5],  # PMS-AFR-176, 177, 178
}


@dataclass(frozen=True)
class MaintenanceCycle:
    """One renewal cycle of a jurisdiction's schedule (BR-PMS-060)."""

    cycle: int
    due_after_days: int
    fee_amount: Decimal


def _as_positive_int(key: str, value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise PolicyConfigurationError(f"'{key}' must be a whole number.") from exc
    if parsed <= 0:
        raise PolicyConfigurationError(f"'{key}' must be greater than zero.")
    return parsed


def _as_decimal(key: str, value: Any) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise PolicyConfigurationError(f"'{key}' must be a decimal number.") from exc
    if parsed < 0:
        raise PolicyConfigurationError(f"'{key}' cannot be negative.")
    return parsed


def _parse_schedule(value: Any) -> dict[str, tuple[MaintenanceCycle, ...]]:
    if not isinstance(value, Mapping):
        raise PolicyConfigurationError("'maintenance_schedule' must map a jurisdiction to cycles.")
    schedule: dict[str, tuple[MaintenanceCycle, ...]] = {}
    for jurisdiction, cycles in value.items():
        if not isinstance(cycles, list) or not cycles:
            raise PolicyConfigurationError(
                f"'maintenance_schedule.{jurisdiction}' must be a non-empty list of cycles."
            )
        parsed: list[MaintenanceCycle] = []
        for entry in cycles:
            if not isinstance(entry, Mapping):
                raise PolicyConfigurationError(
                    f"'maintenance_schedule.{jurisdiction}' entries must be objects."
                )
            try:
                parsed.append(
                    MaintenanceCycle(
                        cycle=int(entry["cycle"]),
                        due_after_days=int(entry["due_after_days"]),
                        fee_amount=Decimal(str(entry["fee_amount"])),
                    )
                )
            except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
                raise PolicyConfigurationError(
                    f"'maintenance_schedule.{jurisdiction}' needs cycle, "
                    "due_after_days and fee_amount."
                ) from exc
        schedule[str(jurisdiction)] = tuple(sorted(parsed, key=lambda c: c.cycle))
    return schedule


@dataclass(frozen=True)
class PmsPolicy:
    """Resolved configuration. `None` means "the operator has not set this"."""

    review_business_days: int = 15
    revision_days: int = 60
    alert_offsets: tuple[int, ...] = (30, 15, 5)
    holidays: frozenset[datetime.date] = field(default_factory=frozenset)
    budget_threshold: Decimal | None = None
    appeal_period_days: int | None = None
    escalation_chain: tuple[str, ...] | None = None
    maintenance_schedule: Mapping[str, tuple[MaintenanceCycle, ...]] | None = None

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> PmsPolicy:
        """Build a policy from stored `PmsConfiguration` values.

        Unknown keys are rejected: silently ignoring one hides a typo behind a
        policy that looks configured but is not.
        """
        unknown = sorted(set(values) - set(CONFIG_KEYS))
        if unknown:
            raise PolicyConfigurationError(f"Unknown PMS configuration key(s): {unknown}.")

        kwargs: dict[str, Any] = {}
        if "review_business_days" in values:
            kwargs["review_business_days"] = _as_positive_int(
                "review_business_days", values["review_business_days"]
            )
        if "revision_days" in values:
            kwargs["revision_days"] = _as_positive_int("revision_days", values["revision_days"])
        if "alert_offsets" in values:
            raw = values["alert_offsets"]
            if not isinstance(raw, list) or not raw:
                raise PolicyConfigurationError("'alert_offsets' must be a non-empty list.")
            kwargs["alert_offsets"] = tuple(_as_positive_int("alert_offsets", n) for n in raw)
        if "holiday_calendar" in values:
            raw = values["holiday_calendar"]
            if not isinstance(raw, list):
                raise PolicyConfigurationError("'holiday_calendar' must be a list of ISO dates.")
            try:
                kwargs["holidays"] = frozenset(datetime.date.fromisoformat(str(d)) for d in raw)
            except ValueError as exc:
                raise PolicyConfigurationError(
                    "'holiday_calendar' entries must be ISO dates (YYYY-MM-DD)."
                ) from exc
        if "budget_threshold" in values:
            kwargs["budget_threshold"] = _as_decimal(
                "budget_threshold", values["budget_threshold"]
            )
        if "appeal_period_days" in values:
            kwargs["appeal_period_days"] = _as_positive_int(
                "appeal_period_days", values["appeal_period_days"]
            )
        if "escalation_chain" in values:
            raw = values["escalation_chain"]
            if not isinstance(raw, list) or not raw:
                raise PolicyConfigurationError("'escalation_chain' must be a non-empty list.")
            kwargs["escalation_chain"] = tuple(str(step) for step in raw)
        if "maintenance_schedule" in values:
            kwargs["maintenance_schedule"] = _parse_schedule(values["maintenance_schedule"])
        return cls(**kwargs)

    def maintenance_cycle(self, jurisdiction: str, cycle_number: int) -> MaintenanceCycle | None:
        """The configured cycle for this jurisdiction, or None when unconfigured."""
        if not self.maintenance_schedule:
            return None
        for entry in self.maintenance_schedule.get(jurisdiction, ()):
            if entry.cycle == cycle_number:
                return entry
        return None
