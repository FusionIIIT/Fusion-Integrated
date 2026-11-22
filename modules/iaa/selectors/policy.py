"""The policy, financial year and budget in force at a moment."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from modules.iaa.domain import policy as policy_rules
from modules.iaa.models import BudgetEntry, FinancialYear, PolicyVersion


def current_version(at: datetime | None = None) -> PolicyVersion | None:
    at = at or timezone.now()
    return PolicyVersion.objects.filter(effective_from__lte=at).order_by("-effective_from",
                                                                         "-id").first()


def to_policy(version: PolicyVersion) -> policy_rules.Policy:
    return policy_rules.parse({
        "approval_timeout_hours": version.approval_timeout_hours,
        "ta_high_value_threshold": str(version.ta_high_value_threshold),
        "budget_check_required": version.budget_check_required,
        "request_types": version.request_types,
        "required_documents": version.required_documents,
        "routes": version.routes,
        "anomaly_resolvers": version.anomaly_resolvers,
    })


def financial_year_on(day: date) -> FinancialYear | None:
    return FinancialYear.objects.filter(starts_on__lte=day, ends_on__gte=day).first()


def available_budget(financial_year: FinancialYear, department: str) -> Decimal:
    total = (BudgetEntry.objects.filter(financial_year=financial_year, department=department)
             .aggregate(t=Sum("amount"))["t"])
    return total or Decimal("0")
