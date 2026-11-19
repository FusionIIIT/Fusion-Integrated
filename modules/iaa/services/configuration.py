"""System Admin configuration operations; no operational record access."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from modules.iaa.domain import state_machine as sm
from modules.iaa.models import (
    ApprovalRouteRule, AutomaticAnomalyRule, DepartmentBudget, FinancialYear,
    IaaRoleAssignment, PolicyParameter,
)
from modules.iaa.services.authz import IaaAccessError, require_admin
from modules.iaa.services.records import IaaRuleError, _audit


@transaction.atomic
def assign_role(*, principal, role, user_id, assigned_role, department=""):
    require_admin(principal, role)
    if assigned_role not in {r for r, _ in IaaRoleAssignment._meta.get_field("role").choices}:
        raise IaaRuleError("Unknown IAA actor role.", code="invalid_iaa_role")
    if user_id <= 0:
        raise IaaRuleError("A positive IAM user id is required.", code="invalid_user_id")
    if assigned_role in sm.AUTHORITIES:
        previous = IaaRoleAssignment.objects.select_for_update().filter(
            role=assigned_role, department=department, is_active=True
        ).exclude(user_id=user_id)
        for old in previous:
            old.is_active = False
            old.save(update_fields=("is_active",))
            _audit(record_type="role_assignment", record_id=old.pk,
                   action="authority_assignment_replaced", actor=principal,
                   role=role, details={"user_id": old.user_id,
                                       "assigned_role": old.role,
                                       "department": old.department})
    assignment, created = IaaRoleAssignment.objects.update_or_create(
        user_id=user_id, role=assigned_role, department=department,
        defaults={"assigned_by_id": principal.user_id, "is_active": True})
    _audit(record_type="role_assignment", record_id=assignment.pk,
           action="role_assigned" if created else "role_assignment_activated",
           actor=principal, role=role, details={"user_id": user_id,
                                               "assigned_role": assigned_role,
                                               "department": department})
    return assignment


@transaction.atomic
def revoke_role(*, principal, role, assignment_id):
    require_admin(principal, role)
    assignment = IaaRoleAssignment.objects.select_for_update().filter(
        pk=assignment_id, is_active=True).first()
    if assignment is None:
        raise IaaRuleError("Active IAA role assignment was not found.",
                           code="role_assignment_not_found")
    assignment.is_active = False
    assignment.save(update_fields=("is_active",))
    _audit(record_type="role_assignment", record_id=assignment.pk,
           action="role_assignment_revoked", actor=principal, role=role,
           details={"user_id": assignment.user_id,
                    "assigned_role": assignment.role,
                    "department": assignment.department})
    return assignment


@transaction.atomic
def save_financial_year(*, principal, role, values, financial_year_id=None):
    require_admin(principal, role)
    if values["ends_on"] < values["starts_on"]:
        raise IaaRuleError("Financial year end must not precede its start.",
                           code="invalid_financial_year")
    year = (FinancialYear.objects.select_for_update().filter(pk=financial_year_id).first()
            if financial_year_id else FinancialYear())
    if financial_year_id and year is None:
        raise IaaRuleError("Financial year was not found.", code="financial_year_not_found")
    for name in ("code", "starts_on", "ends_on", "is_active"):
        if name in values:
            setattr(year, name, values[name])
    year.created_by_id = principal.user_id
    if year.is_active:
        FinancialYear.objects.exclude(pk=year.pk).update(is_active=False)
    year.save()
    _audit(record_type="financial_year", record_id=year.pk,
           action="financial_year_saved", actor=principal, role=role,
           details={"code": year.code, "is_active": year.is_active})
    return year


@transaction.atomic
def save_department_budget(*, principal, role, values, budget_id=None):
    require_admin(principal, role)
    if values["available_amount"] < 0:
        raise IaaRuleError("Available budget cannot be negative.", code="invalid_budget")
    year = FinancialYear.objects.filter(pk=values["financial_year_id"]).first()
    if year is None:
        raise IaaRuleError("Financial year was not found.", code="financial_year_not_found")
    budget = (DepartmentBudget.objects.select_for_update().filter(pk=budget_id).first()
              if budget_id else DepartmentBudget())
    if budget_id and budget is None:
        raise IaaRuleError("Department budget was not found.", code="budget_not_found")
    budget.financial_year = year
    budget.department = values["department"]
    budget.available_amount = values["available_amount"]
    budget.updated_by_id = principal.user_id
    budget.updated_at = timezone.now()
    budget.save()
    _audit(record_type="department_budget", record_id=budget.pk,
           action="budget_configured", actor=principal, role=role,
           details={"department": budget.department,
                    "financial_year": year.code,
                    "available_amount": str(budget.available_amount)})
    return budget


@transaction.atomic
def save_route(*, principal, role, values, route_id=None):
    require_admin(principal, role)
    levels = values["levels"]
    escalation_roles = values.get("escalation_roles", [])
    if not isinstance(levels, list) or not levels:
        raise IaaRuleError("At least one approval level must be configured.",
                           code="route_levels_required")
    if any(r not in sm.AUTHORITIES for r in levels + escalation_roles):
        raise IaaRuleError("Routes may contain only HoD, Dean, or Director roles.",
                           code="route_role_invalid")
    route = (ApprovalRouteRule.objects.select_for_update().filter(pk=route_id).first()
             if route_id else ApprovalRouteRule())
    if route_id and route is None:
        raise IaaRuleError("Approval route was not found.", code="route_not_found")
    for field in ("request_type", "department", "minimum_amount", "maximum_amount",
                  "timeout_seconds", "priority", "is_active"):
        if field in values:
            setattr(route, field, values[field])
    route.levels = levels
    route.escalation_roles = escalation_roles
    route.updated_by_id = principal.user_id
    route.updated_at = timezone.now()
    route.save()
    _audit(record_type="approval_route", record_id=route.pk,
           action="approval_route_saved", actor=principal, role=role,
           details={"levels": levels, "escalation_roles": escalation_roles})
    return route


@transaction.atomic
def save_policy_parameter(*, principal, role, values, parameter_id=None):
    require_admin(principal, role)
    parameter = (PolicyParameter.objects.select_for_update().filter(pk=parameter_id).first()
                 if parameter_id else PolicyParameter())
    if parameter_id and parameter is None:
        raise IaaRuleError("Policy parameter was not found.", code="policy_not_found")
    for field in ("code", "value", "effective_from", "effective_until", "is_active"):
        if field in values:
            setattr(parameter, field, values[field])
    parameter.updated_by_id = principal.user_id
    parameter.updated_at = timezone.now()
    parameter.save()
    _audit(record_type="policy_parameter", record_id=parameter.pk,
           action="policy_parameter_saved", actor=principal, role=role,
           details={"code": parameter.code, "value": parameter.value})
    return parameter


@transaction.atomic
def save_anomaly_rule(*, principal, role, values):
    require_admin(principal, role)
    resolver = values["resolver_role"]
    if resolver not in (sm.FINANCE, *sm.AUTHORITIES, sm.AUDITOR):
        raise IaaRuleError("Invalid configured anomaly resolver role.",
                           code="anomaly_resolver_invalid")
    rule, _ = AutomaticAnomalyRule.objects.update_or_create(
        condition=values["condition"],
        defaults={"category": values["category"],
                  "description": values.get("description", ""),
                  "resolver_role": resolver,
                  "assigned_user_id": values.get("assigned_user_id"),
                  "is_active": values.get("is_active", True),
                  "updated_by_id": principal.user_id,
                  "updated_at": timezone.now()})
    _audit(record_type="automatic_anomaly_rule", record_id=rule.pk,
           action="automatic_anomaly_rule_saved", actor=principal, role=role,
           details={"condition": rule.condition, "resolver_role": resolver})
    return rule
