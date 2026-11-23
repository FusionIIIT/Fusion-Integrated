"""Budgets and the append-only financial log (UC-PMS-009, PMS-AFR-098)."""
from __future__ import annotations

from django.db import models
from django.db.models import F, Q

from core.db.mixins import TimeStampedModel
from modules.pms.domain import state_machine as sm
from modules.pms.models.applications import Application
from modules.pms.models.base import AppendOnly, choices

BUDGET_STATUSES = (sm.PROPOSED, sm.BUDGET_APPROVED, sm.BUDGET_REJECTED, sm.ESCALATED,
                   sm.ESCALATION_TRACKED, sm.EXTERNAL_APPROVED, sm.EXTERNAL_REJECTED,
                   sm.BUDGET_CLOSED)


class Budget(TimeStampedModel):
    application = models.ForeignKey(Application, on_delete=models.CASCADE,
                                    related_name="budgets")
    proposed_by_user_id = models.IntegerField()
    filing_fee = models.DecimalField(max_digits=12, decimal_places=2)
    attorney_fee = models.DecimalField(max_digits=12, decimal_places=2)
    admin_cost = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=choices(BUDGET_STATUSES),
                              default=sm.PROPOSED)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decision_note = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    threshold_at_decision = models.DecimalField(max_digits=12, decimal_places=2, null=True,
                                                blank=True)
    availability = models.CharField(max_length=20, blank=True)
    routed_to = models.CharField(max_length=200, blank=True)
    external_reference = models.CharField(max_length=200, blank=True)
    external_decided_on = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(filing_fee__gte=0) & Q(attorney_fee__gte=0) & Q(admin_cost__gte=0),
                name="pms_budget_components_nonnegative"),
            models.CheckConstraint(
                condition=Q(total=F("filing_fee") + F("attorney_fee") + F("admin_cost")),
                name="pms_budget_total_is_sum"),
            models.UniqueConstraint(fields=["application"],
                                    condition=Q(status__in=sorted(sm.OPEN_BUDGET)),
                                    name="pms_budget_one_open"),
            models.UniqueConstraint(fields=["application"],
                                    condition=Q(status__in=sorted(sm.APPROVED_BUDGET)),
                                    name="pms_budget_one_approved"),
            models.CheckConstraint(condition=Q(status__in=BUDGET_STATUSES),
                                   name="pms_budget_status_valid"),
        ]
        indexes = [models.Index(fields=["status", "-updated_at"], name="pms_budget_status_idx")]


FINANCIAL_KINDS = ("budget_approved", "budget_rejected", "budget_escalated",
                   "external_approved", "external_rejected", "maintenance_payment")
AUTHORIZATION_LEVELS = ("director", "external_authority", "attorney_recorded")


class FinancialRecord(AppendOnly):
    application = models.ForeignKey(Application, on_delete=models.PROTECT,
                                    related_name="financial_records")
    budget = models.ForeignKey(Budget, on_delete=models.PROTECT, null=True, blank=True,
                               related_name="financial_records")
    maintenance_cycle_id = models.IntegerField(null=True, blank=True)
    kind = models.CharField(max_length=24, choices=choices(FINANCIAL_KINDS))
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    authorization_level = models.CharField(max_length=20, choices=choices(AUTHORIZATION_LEVELS))
    availability = models.CharField(max_length=20, blank=True)
    recorded_by_user_id = models.IntegerField()
    reference = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["application", "-created_at"],
                                name="pms_financial_app_idx")]
