from datetime import date
from decimal import Decimal

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField
from django.contrib.postgres.fields.ranges import RangeOperators
from django.db import models
from django.db.models import Q
from psycopg.types.range import Range

from core.db.mixins import TimeStampedModel
from modules.phc.domain.reimbursements import CLAIM_PENDING_PHC


class ReimbursementPolicy(TimeStampedModel):
    submission_window_days = models.PositiveSmallIntegerField()
    effective_period = DateRangeField()
    created_by = models.CharField(max_length=24, default="seed")

    class Meta:
        db_table = "phc_reimbursement_policy"
        constraints = [
            models.CheckConstraint(condition=Q(submission_window_days__gt=0),
                                   name="phc_policy_window_positive"),
            ExclusionConstraint(name="phc_policy_period_no_overlap",
                                expressions=[("effective_period", RangeOperators.OVERLAPS)]),
        ]
        indexes = [models.Index(fields=["-created_at"], name="phc_policy_created_idx")]

    @classmethod
    def initial(cls):
        return cls(submission_window_days=30,
                   effective_period=Range(date(2026, 1, 1), None, bounds="[)"))


class ReimbursementClaim(TimeStampedModel):
    class State(models.TextChoices):
        PENDING_PHC = CLAIM_PENDING_PHC, "Pending PHC Review"
        PENDING_ACCOUNTS = "pending_accounts_verification", "Pending Accounts Verification"
        PENDING_SANCTION = "pending_sanction", "Pending Sanction"
        APPROVED_PAYMENT = "approved_for_payment", "Approved for Payment"
        REJECTED = "rejected", "Rejected"
        REIMBURSED = "reimbursed", "Reimbursed"

    claimant_user_id = models.PositiveBigIntegerField()
    prescription = models.ForeignKey("phc.Prescription", on_delete=models.PROTECT,
                                     related_name="reimbursement_claims")
    claim_amount = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField()
    bill_reference = models.CharField(max_length=200, blank=True)
    remarks = models.TextField(blank=True)
    state = models.CharField(max_length=40, choices=State.choices,
                             default=CLAIM_PENDING_PHC)
    submitted_at = models.DateTimeField()

    class Meta:
        db_table = "phc_reimbursement_claim"
        ordering = ["-created_at", "-id"]
        constraints = [models.CheckConstraint(
            condition=Q(claim_amount__gt=Decimal("0.00")),
            name="phc_claim_amount_positive")]
        indexes = [
            models.Index(fields=["claimant_user_id", "-created_at"],
                         name="phc_claim_owner_created_idx"),
            models.Index(fields=["state", "created_at"], name="phc_claim_state_created_idx"),
        ]


class ReimbursementAction(TimeStampedModel):
    claim = models.ForeignKey(ReimbursementClaim, on_delete=models.PROTECT,
                              related_name="actions")
    from_state = models.CharField(max_length=40)
    to_state = models.CharField(max_length=40)
    event = models.CharField(max_length=16)
    actor_user_id = models.PositiveBigIntegerField()

    class Meta:
        db_table = "phc_reimbursement_action"
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["claim", "created_at"],
                                name="phc_claim_action_created_idx")]
