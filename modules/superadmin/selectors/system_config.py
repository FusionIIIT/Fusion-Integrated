"""System parameter policy selectors."""

from __future__ import annotations

from django.db.models import QuerySet

from modules.superadmin.models import SystemParameterPolicy
from modules.superadmin.selectors.scoping import visible_parameters


def list_system_parameters(principal) -> QuerySet[SystemParameterPolicy]:
    return visible_parameters(principal).order_by("parameter_key")


def get_parameter_value(key: str, default: any | None = None) -> any:
    # Read active parameter value directly from policy table.
    param = (
        SystemParameterPolicy.objects.filter(parameter_key=key, is_active=True)
        .order_by("-version")
        .first()
    )
    if param and "value" in param.parameter_value:
        return param.parameter_value["value"]
    return default
