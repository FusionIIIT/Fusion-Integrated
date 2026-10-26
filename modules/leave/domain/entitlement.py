"""The annual credit each kind of employee receives (BR-EL-002 to 006, BR-EL-009)."""
from __future__ import annotations

from decimal import Decimal

from modules.leave.domain import categories as cat
from modules.leave.domain.policy import Policy


def annual_credits(policy: Policy, employee_kind: str) -> dict[str, Decimal]:
    """EL goes to non-faculty only; faculty receive VL instead and EL only by conversion."""
    if employee_kind not in cat.EMPLOYEE_KINDS:
        return {}
    return {code: policy.rule(code).annual_entitlement
            for code in cat.ALL
            if employee_kind in cat.get(code).credited_to
            and policy.rule(code).annual_entitlement > 0}
