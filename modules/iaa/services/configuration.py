"""Configuration service for IAA (IAA-UC-703, IAA-UC-704)."""

from decimal import Decimal

from django.db import transaction

from modules.iaa.models import ApprovalHierarchyRule, DepartmentBudget, IAAConfiguration
from modules.iaa.services.audit_trail import record_audit_log


def update_iaa_configuration(
    user_id: int,
    acting_role: str,
    financial_year: str,
    high_value_ta_threshold: Decimal,
    approval_timeout_days: int,
) -> IAAConfiguration:
    with transaction.atomic():
        config, _ = IAAConfiguration.objects.get_or_create(is_active=True)
        config.financial_year = financial_year
        config.high_value_ta_threshold = high_value_ta_threshold
        config.approval_timeout_days = approval_timeout_days
        config.save()

        record_audit_log(
            user_id=user_id,
            acting_role=acting_role,
            action="update_configuration",
            target_type="iaa_configuration",
            target_id=config.id,
            details={
                "financial_year": financial_year,
                "high_value_ta_threshold": str(high_value_ta_threshold),
                "approval_timeout_days": approval_timeout_days,
            },
        )
        return config


def set_department_budget(
    user_id: int,
    acting_role: str,
    department: str,
    financial_year: str,
    allocated_amount: Decimal,
) -> DepartmentBudget:
    with transaction.atomic():
        budget, _ = DepartmentBudget.objects.get_or_create(
            department=department,
            financial_year=financial_year,
        )
        budget.allocated_amount = allocated_amount
        budget.save()

        record_audit_log(
            user_id=user_id,
            acting_role=acting_role,
            action="set_department_budget",
            target_type="department_budget",
            target_id=budget.id,
            details={"department": department, "allocated_amount": str(allocated_amount)},
        )
        return budget


def add_approval_hierarchy_rule(
    user_id: int,
    acting_role: str,
    request_type: str,
    min_amount: Decimal,
    max_amount: Decimal | None,
    required_levels: int,
    approver_roles: list[str],
) -> ApprovalHierarchyRule:
    with transaction.atomic():
        rule = ApprovalHierarchyRule.objects.create(
            request_type=request_type,
            min_amount=min_amount,
            max_amount=max_amount,
            required_levels=required_levels,
            approver_roles=approver_roles,
        )
        record_audit_log(
            user_id=user_id,
            acting_role=acting_role,
            action="add_hierarchy_rule",
            target_type="approval_hierarchy_rule",
            target_id=rule.id,
            details={"request_type": request_type, "approver_roles": approver_roles},
        )
        return rule
