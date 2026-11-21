"""Configuration selectors for ELM."""
from __future__ import annotations

from modules.elm.models import (
    ApprovalHierarchy,
    LeavePolicyConfig,
    SlaThresholdConfig,
)


def get_active_policy_config() -> LeavePolicyConfig:
    """Return the active leave policy configuration, or create a default one if none exists."""
    cfg = LeavePolicyConfig.objects.filter(is_active=True).first()
    if not cfg:
        cfg = LeavePolicyConfig.objects.create(is_active=True)
    return cfg


def resolve_hierarchy_for_employee(
    applicant_user_id: int,
    department: str = "",
    designation: str = "",
    category: str = "",
) -> ApprovalHierarchy | None:
    """Resolve approval hierarchy for an employee per BR-EL-019.

    Resolution precedence:
    1. Direct applicant match
    2. Department + Designation + Category match
    3. Department + Designation match
    4. Department match
    5. Fallback first active hierarchy
    """
    qs = ApprovalHierarchy.objects.filter(is_active=True)

    # 1. Direct applicant match
    by_user = qs.filter(applicant_user_id=applicant_user_id).first()
    if by_user:
        return by_user

    # 2. Dept + Desig + Category
    if department and designation and category:
        match = qs.filter(
            department=department, designation=designation, leave_category=category
        ).first()
        if match:
            return match

    # 3. Dept + Desig
    if department and designation:
        match = qs.filter(department=department, designation=designation).first()
        if match:
            return match

    # 4. Dept
    if department:
        match = qs.filter(department=department).first()
        if match:
            return match

    # 5. Fallback active hierarchy
    return qs.first()


def get_sla_config_for_task(task_type: str) -> SlaThresholdConfig | None:
    """Return configured SLA thresholds for a task type."""
    return SlaThresholdConfig.objects.filter(task_type=task_type, is_active=True).first()
