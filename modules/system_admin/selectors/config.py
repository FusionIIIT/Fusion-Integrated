"""System parameter selectors for system_admin."""
from __future__ import annotations

import json
from typing import Any, Dict

from modules.system_admin.constants import PermittedConfigKey
from modules.system_admin.models import SystemParameter


def get_system_parameter(key: str, default: Any = None) -> Any:
    """Retrieve system parameter value cast to its value_type."""
    param = SystemParameter.objects.filter(key=key).first()
    if not param:
        return default

    val = param.value
    if param.value_type == "int":
        try:
            return int(val)
        except ValueError:
            return default
    if param.value_type == "bool":
        return val.lower() in ("true", "1", "yes")
    if param.value_type == "json":
        try:
            return json.loads(val)
        except (ValueError, TypeError):
            return default
    return val


def get_all_permitted_parameters() -> Dict[str, Any]:
    """Retrieve all configured permitted parameters."""
    params = SystemParameter.objects.filter(key__in=PermittedConfigKey.ALL_KEYS)
    result = {}
    for p in params:
        result[p.key] = get_system_parameter(p.key)
    return result
