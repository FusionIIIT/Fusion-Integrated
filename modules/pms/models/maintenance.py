from django.db import models
from django.db.models import CheckConstraint, Q

from core.db.mixins import TimeStampedModel


class RenewalDecision(models.TextChoices):
    PENDING = "pending", "Pending Decision"
    RENEW = "renew", "Approved for Annuity Payment"
    ABANDON = "abandon", "Lapse / Do Not Renew"


class MaintenanceRenewal(TimeStampedModel):
    """Annual patent annuity / maintenance renewal tracking for granted patents."""

    application = models.ForeignKey(
        "pms.PatentApplication",
        on_delete=models.CASCADE,
        related_name="renewals",
    )
    renewal_year = models.IntegerField(db_index=True)
    due_date = models.DateField(db_index=True)
    grace_period_deadline = models.DateField()
    annuity_fee = models.DecimalField(max_digits=12, decimal_places=2)
    decision = models.CharField(
        max_length=32,
        choices=RenewalDecision.choices,
        default=RenewalDecision.PENDING,
    )
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    payment_reference = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        db_table = "pms_maintenance_renewal"
        ordering = ["due_date"]
        constraints = [
            CheckConstraint(
                check=Q(renewal_year__gte=3) & Q(renewal_year__lte=20),
                name="pms_valid_renewal_year",
            ),
        ]

    def __str__(self) -> str:
        return f"Year {self.renewal_year} Renewal for App #{self.application_id}: {self.decision}"
