"""Workflow Configuration service (BR-HR-009, BR-HR-012, BR-HR-017)."""
from __future__ import annotations

from typing import Any

from modules.hreis.domain.leave import DEFAULT_LEAVE_QUOTAS
from modules.hreis.domain.workflow import DEFAULT_APPROVAL_HIERARCHY
from modules.hreis.models import WorkflowConfiguration

DEFAULT_CONFIGS: dict[str, dict[str, Any]] = {
    "appraisal_window": {
        "active": True,
        "academic_year": "2025-2026",
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
    },
    "approval_hierarchy": DEFAULT_APPROVAL_HIERARCHY,
    "leave_quotas": DEFAULT_LEAVE_QUOTAS,
}


def get_workflow_config(key: str) -> dict[str, Any]:
    try:
        conf = WorkflowConfiguration.objects.get(setting_key=key)
        return conf.setting_value
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


def update_workflow_config(key: str, value: dict[str, Any], description: str = "") -> dict[str, Any]:
    conf, _ = WorkflowConfiguration.objects.update_or_create(
        setting_key=key,
        defaults={"setting_value": value, "description": description},
    )
    return conf.setting_value
