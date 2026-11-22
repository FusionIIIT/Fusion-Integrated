"""Workflow configuration service (BR-HR-009, BR-HR-012, BR-HR-034)."""

from __future__ import annotations

from typing import Any

from modules.hreis.models import WorkflowConfiguration

DEFAULT_CONFIGS: dict[str, dict[str, Any]] = {
    "appraisal_window": {
        "active": False,
        "academic_year": "2025-2026",
        "start_date": "2026-04-01",
        "end_date": "2026-05-31",
    },
    "leave_policy": {
        "auto_forward_days": 3,
        "escalation_role": "director",
    },
    "claim_policy": {
        "max_advance_percent": 80,
        "ltc_settlement_days": 30,
        "cpda_settlement_days": 30,
    },
}


def get_workflow_config(key: str) -> dict[str, Any]:
    try:
        conf = WorkflowConfiguration.objects.get(setting_key=key)
    except WorkflowConfiguration.DoesNotExist:
        default_val = DEFAULT_CONFIGS.get(key, {})
        if default_val:
            conf = WorkflowConfiguration.objects.create(
                setting_key=key,
                setting_value=default_val,
                description=f"Default setting for {key}",
            )
            return conf.setting_value
        return {}
    else:
        return conf.setting_value


def update_workflow_config(
    key: str, value: dict[str, Any], description: str = ""
) -> WorkflowConfiguration:
    conf, _ = WorkflowConfiguration.objects.update_or_create(
        setting_key=key,
        defaults={"setting_value": value, "description": description},
    )
    return conf
