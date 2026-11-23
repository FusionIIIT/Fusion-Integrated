"""Helpers for exercising operator-configured policy in tests.

Nothing here is a product default: each helper writes a value an operator
would write, so a test proves the *mechanism*, not an invented number.
"""

from __future__ import annotations

from typing import Any

from modules.pms.services.configuration import set_policy_value

#: A schedule shaped like an operator's own, deliberately unlike the values the
#: codebase used to hard-code.
TEST_MAINTENANCE_SCHEDULE: dict[str, list[dict[str, Any]]] = {
    "IN": [
        {"cycle": 1, "due_after_days": 1095, "fee_amount": "5000.00"},
        {"cycle": 2, "due_after_days": 1460, "fee_amount": "6000.00"},
    ]
}


def configure(**values: Any) -> None:
    """Write one or more policy values."""
    for key, value in values.items():
        set_policy_value(key, value)


def configure_maintenance_schedule(schedule: dict | None = None) -> None:
    """Write the jurisdiction schedule a renewing patent needs (BR-PMS-060)."""
    set_policy_value("maintenance_schedule", schedule or TEST_MAINTENANCE_SCHEDULE)
