"""Reading and updating the current ELM configuration (BR-EL-030/038)."""
from __future__ import annotations

from decimal import Decimal

from modules.elm.domain import enums as e
from modules.elm.models import (
    ElmSettings,
    HierarchyConfig,
    LeaveTypeConfig,
    SlaConfig,
    UnitHeadAssignment,
)

#: Default policy per category. A data migration writes these; `type_config`
#: also creates a row on demand so a fresh test needs no fixtures.
DEFAULT_TYPES: dict[str, dict] = {
    e.CL: {"label": "Casual Leave", "annual_entitlement": Decimal("8"),
           "half_day": True, "unit_head_final": True},
    e.RH: {"label": "Restricted Holiday", "annual_entitlement": Decimal("2"),
           "unit_head_final": True},
    e.SCL: {"label": "Special Casual Leave",
            "annual_entitlement": Decimal("15"), "requires_substitute": False},
    e.EL: {"label": "Earned Leave", "annual_entitlement": Decimal("30"),
           "carry_forward": True, "continuous": True,
           "requires_substitute": True, "requires_resumption": True,
           "allows_extension": True},
    e.COL: {"label": "Commuted Leave", "annual_entitlement": Decimal("20"),
            "carry_forward": True, "continuous": True,
            "requires_substitute": True, "requires_resumption": True,
            "allows_extension": True, "requires_medical_evidence": True},
    e.VL: {"label": "Vacation Leave", "employee_kind": "faculty",
           "annual_entitlement": Decimal("60"), "continuous": True,
           "requires_substitute": True, "requires_resumption": True,
           "allows_extension": True},
}


def settings_row() -> ElmSettings:
    return ElmSettings.load()


def type_config(category: str) -> LeaveTypeConfig:
    row = LeaveTypeConfig.objects.filter(category=category).first()
    if row is not None:
        return row
    defaults = DEFAULT_TYPES.get(category, {"label": category})
    return LeaveTypeConfig.objects.create(category=category, **defaults)


def all_type_configs() -> dict[str, LeaveTypeConfig]:
    return {c.category: c for c in LeaveTypeConfig.objects.all()}


def hierarchy_for(category: str) -> HierarchyConfig:
    row = HierarchyConfig.objects.filter(category=category).first()
    if row is None:
        row = HierarchyConfig.objects.filter(category="").first()
    if row is None:
        row = HierarchyConfig.objects.create(category="")
    return row


def unit_head_for(department: str) -> int | None:
    if not department:
        return None
    row = UnitHeadAssignment.objects.filter(department=department).first()
    return row.unit_head_user_id if row else None


def sla_for(task_type: str) -> SlaConfig:
    row = SlaConfig.objects.filter(task_type=task_type).first()
    return row or SlaConfig(task_type=task_type)


def update_policy(*, category: str, **fields) -> LeaveTypeConfig:
    row = type_config(category)
    for key, value in fields.items():
        setattr(row, key, value)
    row.save()
    return row


def update_hierarchy(*, category: str, **fields) -> HierarchyConfig:
    row, _ = HierarchyConfig.objects.update_or_create(
        category=category, defaults=fields)
    return row


def update_sla(*, task_type: str, **fields) -> SlaConfig:
    row, _ = SlaConfig.objects.update_or_create(
        task_type=task_type, defaults=fields)
    return row


def set_unit_head(*, department: str, unit_head_user_id: int) -> UnitHeadAssignment:
    row, _ = UnitHeadAssignment.objects.update_or_create(
        department=department, defaults={"unit_head_user_id": unit_head_user_id})
    return row
