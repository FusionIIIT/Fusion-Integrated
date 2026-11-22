from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.phc.domain.state_machine import ClaimStatus
from modules.phc.models._immutable import AppendOnlyModel
from modules.phc.models.records import Prescription

# PHC-BR-14: once submitted, only `status` and `updated_at` may ever change.
_FROZEN_FIELDS = ("user_id", "prescription_id", "expense_date", "amount", "description",
                  "submitted_at")


class ReimbursementPolicy(AppendOnlyModel):
    effective_from = models.DateField(unique=True)
    window_days = models.PositiveIntegerField()
    includes_last_day = models.BooleanField()
    created_by_user_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "phc_reimbursement_policy"
        constraints = [
            models.CheckConstraint(condition=models.Q(window_days__gt=0),
                                   name="phc_policy_window_positive"),
        ]

    def __str__(self) -> str:
        return f"{self.window_days} days from {self.effective_from}"


class ReimbursementClaim(TimeStampedModel, UserScopedModel):
    prescription = models.ForeignKey(Prescription, on_delete=models.PROTECT,
                                     related_name="claims")
    expense_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=40, choices=ClaimStatus.CHOICES,
                              default=ClaimStatus.PENDING_PHC_REVIEW)
    submitted_at = models.DateTimeField()

    class Meta:
        db_table = "phc_reimbursement_claim"
        indexes = [
            models.Index(fields=["user_id", "-submitted_at"], name="phc_claim_owner_idx"),
            models.Index(fields=["status", "-submitted_at"], name="phc_claim_queue_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0),
                                   name="phc_claim_amount_positive"),
        ]

    def __str__(self) -> str:
        return f"Claim {self.pk}"

    def save(self, *args, **kwargs):
        if self.pk is not None and not self._state.adding:
            original = type(self).objects.filter(pk=self.pk).values(*_FROZEN_FIELDS).first()
            if original and any(original[f] != getattr(self, f) for f in _FROZEN_FIELDS):
                raise ValueError("A submitted claim cannot be edited; submit a new claim.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("A submitted claim cannot be deleted.")


class ClaimAction(AppendOnlyModel):
    claim = models.ForeignKey(ReimbursementClaim, on_delete=models.PROTECT,
                              related_name="actions")
    actor_user_id = models.IntegerField()
    event = models.CharField(max_length=20)
    from_status = models.CharField(max_length=40, blank=True)
    to_status = models.CharField(max_length=40)
    note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "phc_claim_action"
        ordering = ("created_at", "id")
        indexes = [
            models.Index(fields=["claim", "created_at"], name="phc_claim_action_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.claim_id}: {self.event}"
