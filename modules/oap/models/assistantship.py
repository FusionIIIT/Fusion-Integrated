from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.oap.domain import constants as c


class AssistantshipClaim(TimeStampedModel, UserScopedModel):
    """PG assistantship claim model (OA-UC-31, OA-UC-35, OA-UC-36, BW-OAP-07, BW-OAP-08)."""

    month = models.PositiveSmallIntegerField()
    year = models.PositiveSmallIntegerField()
    department = models.CharField(max_length=100)
    stipend_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    work_summary = models.TextField()
    hours_worked = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)

    status = models.CharField(
        max_length=60,
        choices=[(s, s) for s in c.ASSISTANTSHIP_STATES],
        default=c.ASSISTANTSHIP_AWAITING_DUAL_SUPERVISOR,
        db_index=True,
    )

    thesis_supervisor_user_id = models.IntegerField(db_index=True)
    ta_supervisor_user_id = models.IntegerField(db_index=True)

    thesis_verified = models.BooleanField(default=False)
    ta_verified = models.BooleanField(default=False)
    thesis_verified_at = models.DateTimeField(null=True, blank=True)
    ta_verified_at = models.DateTimeField(null=True, blank=True)

    dept_reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    dept_reviewed_at = models.DateTimeField(null=True, blank=True)

    hod_decided_by_user_id = models.IntegerField(null=True, blank=True)
    hod_decision_remarks = models.TextField(blank=True)
    hod_decided_at = models.DateTimeField(null=True, blank=True)

    disbursed_by_user_id = models.IntegerField(null=True, blank=True)
    disbursed_at = models.DateTimeField(null=True, blank=True)
    disbursement_reference = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-created_at"]


class ClaimSupervisorVerification(TimeStampedModel):
    """Detailed record of supervisor verification for an assistantship claim (OA-UC-33)."""

    claim = models.ForeignKey(
        AssistantshipClaim,
        on_delete=models.CASCADE,
        related_name="supervisor_verifications",
    )
    role = models.CharField(
        max_length=30,
        choices=[(r, r) for r in c.SUPERVISOR_ROLES],
    )
    supervisor_user_id = models.IntegerField()
    remarks = models.TextField(blank=True)
    verified_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("claim", "role")
        ordering = ["verified_at"]
