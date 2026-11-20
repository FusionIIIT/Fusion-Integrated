"""Reading and writing PMS policy values (DEC-7).

The values themselves are parsed by `domain/policies.py`; this module is the
only place that touches `PmsConfiguration`, so callers never scatter key
strings through services.
"""

from __future__ import annotations

from typing import Any

from modules.pms.domain.errors import PolicyConfigurationError
from modules.pms.domain.policies import CONFIG_KEYS, PmsPolicy
from modules.pms.models import PmsConfiguration


def load_policy() -> PmsPolicy:
    """Resolve the stored configuration into a policy object.

    Missing keys keep their specification-provided default or stay `None`;
    nothing is inferred.
    """
    values = dict(PmsConfiguration.objects.values_list("key", "value"))
    return PmsPolicy.from_mapping(values)


def set_policy_value(key: str, value: Any, *, description: str = "") -> PmsConfiguration:
    """Create or replace one configuration value."""
    if key not in CONFIG_KEYS:
        raise PolicyConfigurationError(f"Unknown PMS configuration key '{key}'.")
    # Validate by parsing the single value against the policy, so a bad value
    # can never be stored and discovered later at deadline-calculation time.
    PmsPolicy.from_mapping({key: value})
    row, _ = PmsConfiguration.objects.update_or_create(
        key=key,
        defaults={"value": value, "description": description or CONFIG_KEYS[key]},
    )
    return row


def unset_policy_value(key: str) -> int:
    """Remove one value; returns how many rows were deleted."""
    return PmsConfiguration.objects.filter(key=key).delete()[0]


def configured_keys() -> list[str]:
    """Keys an operator has actually set — the audit view of the policy."""
    return sorted(PmsConfiguration.objects.values_list("key", flat=True))
