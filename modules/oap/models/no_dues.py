from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.oap.domain import constants as c


class NoDuesRequest(TimeStampedModel, UserScopedModel):
    """No-Dues clearance request model (OA-UC-21, OA-UC-23, BW-OAP-05, BW-OAP-06)."""

    department = models.CharField(max_length=100)
    programme = models.CharField(max_length=20, default=c.PROGRAMME_UG)

    status = models.CharField(
        max_length=60,
        choices=[(s, s) for s in c.NODUES_STATES],
        default=c.NODUES_VERIFICATION_IN_PROGRESS,
        db_index=True,
    )
    finalized_by_user_id = models.IntegerField(null=True, blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    certificate_number = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-created_at"]


class NoDuesAuthorityClearance(TimeStampedModel):
    """Clearance status recorded by each of the 7 mandatory authorities (OA-BR-31, OA-BR-32)."""

    request = models.ForeignKey(
        NoDuesRequest,
        on_delete=models.CASCADE,
        related_name="clearances",
    )
    domain = models.CharField(
        max_length=50,
        choices=[(d, d) for d in c.MANDATORY_NO_DUES_DOMAINS],
    )
    status = models.CharField(
        max_length=30,
        choices=[(s, s) for s in c.CLEARANCE_STATUSES],
        default=c.CLEARANCE_PENDING,
    )
    verified_by_user_id = models.IntegerField(null=True, blank=True)
    dues_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    remarks = models.TextField(blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("request", "domain")
        ordering = ["domain"]
