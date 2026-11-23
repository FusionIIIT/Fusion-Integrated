from __future__ import annotations

from typing import Any

from modules.superadmin.domain.constants import DEFAULT_POLICY_VALUES
from modules.superadmin.models.config import SystemPolicyParameter


def get_active_policy_param(key: str) -> SystemPolicyParameter | None:
    # Returns current active policy parameter record where effective_to is NULL
    return (
        SystemPolicyParameter.objects.filter(key=key, effective_to__isnull=True)
        .order_by("-version")
        .first()
    )


def get_active_policy_value(key: str) -> Any:
    # Safe fallback to platform defaults when unseeded
    param = get_active_policy_param(key)
    if param is None:
        return DEFAULT_POLICY_VALUES.get(key)
    if param.value_type == "int":
        return int(param.value)
    if param.value_type == "bool":
        return param.value.lower() in {"true", "1", "yes"}
    return param.value


def list_active_policy_params() -> list[SystemPolicyParameter]:
    return list(SystemPolicyParameter.objects.filter(effective_to__isnull=True).order_by("key"))
