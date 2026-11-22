"""System Admin configuration (UC-703/704); never operational data (BR-004)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from django.db import transaction

from core.api.exceptions import ConflictError, DomainError
from modules.iaa.domain import policy as policy_rules
from modules.iaa.domain import roles
from modules.iaa.models import BudgetEntry, FinancialYear, PolicyVersion
from modules.iaa.services import trail
from modules.iaa.services.authz import require, role_of
from modules.iaa.services.common import now

P_CONFIGURE = "iaa.configuration.update"


class PolicyRejected(DomainError):
    code = "policy_invalid"
    message = "The policy has errors. Fix the listed fields and publish again."


def _admin(actor) -> None:
    require(actor, P_CONFIGURE)
    if role_of(actor) != roles.SYSTEM_ADMIN:
        raise ConflictError("Switch to the IAA System Admin role to change configuration.",
                            code="actor_not_allowed")


@transaction.atomic
def publish_policy(actor, payload: dict, effective_from: datetime | None = None
                   ) -> PolicyVersion:
    _admin(actor)
    try:
        policy = policy_rules.parse(payload)
    except policy_rules.PolicyInvalid as exc:
        raise PolicyRejected(details=exc.errors) from exc
    current = now()
    if effective_from is not None and effective_from < current:
        raise DomainError("A policy cannot take effect in the past.", code="backdated_policy")
    start = effective_from or current
    version = PolicyVersion.objects.create(
        effective_from=start, approval_timeout_hours=policy.approval_timeout_hours,
        ta_high_value_threshold=policy.ta_high_value_threshold,
        budget_check_required=policy.budget_check_required,
        request_types=list(policy.request_types), required_documents=policy.required_documents,
        routes=payload.get("routes") or [], anomaly_resolvers=payload.get("anomaly_resolvers"),
        created_by=actor.user_id, created_role=role_of(actor))
    trail.log("configuration", version.pk, "publish_policy", actor=actor,
              remarks=f"Effective from {start.isoformat()}")
    return version


@transaction.atomic
def add_financial_year(actor, *, code: str, starts_on: date, ends_on: date) -> FinancialYear:
    _admin(actor)
    if ends_on <= starts_on:
        raise DomainError("The financial year must end after it starts.", code="invalid_dates")
    if FinancialYear.objects.filter(starts_on__lte=ends_on, ends_on__gte=starts_on).exists():
        raise ConflictError("These dates overlap an existing financial year.",
                            code="financial_year_overlap")
    if FinancialYear.objects.filter(code=code).exists():
        raise ConflictError(f"Financial year {code} already exists.", code="duplicate_code")
    year = FinancialYear.objects.create(code=code, starts_on=starts_on, ends_on=ends_on)
    trail.log("configuration", year.pk, "add_financial_year", actor=actor,
              remarks=f"{code}: {starts_on}..{ends_on}")
    return year


@transaction.atomic
def add_budget_entry(actor, *, financial_year_id: int, department: str, kind: str,
                     amount: Decimal, note: str = "") -> BudgetEntry:
    _admin(actor)
    if kind not in (BudgetEntry.ALLOCATION, BudgetEntry.ADJUSTMENT):
        raise DomainError("Use 'allocation' or 'adjustment'; commitments are written by Finance.",
                          code="invalid_kind")
    if kind == BudgetEntry.ALLOCATION and amount <= 0:
        raise DomainError("An allocation must be above zero; use an adjustment to reduce.",
                          code="invalid_amount")
    if amount == 0:
        raise DomainError("An entry of zero changes nothing.", code="invalid_amount")
    if not department.strip():
        raise DomainError("Name the department.", code="department_required")
    year = FinancialYear.objects.filter(pk=financial_year_id).first()
    if year is None:
        raise DomainError("Choose an existing financial year.", code="financial_year_missing")
    entry = BudgetEntry.objects.create(financial_year=year, department=department.strip(),
                                       kind=kind, amount=amount, note=note,
                                       created_by=actor.user_id, created_role=role_of(actor))
    trail.log("configuration", entry.pk, f"budget_{kind}", actor=actor,
              remarks=f"{department} {amount} in {year.code}")
    return entry
