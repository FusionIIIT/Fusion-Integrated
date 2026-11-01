"""Post-grant patent tracking and maintenance fee renewal models."""

from django.db import models

from core.db.mixins import TimeStampedModel
from modules.pms.models.applications import PatentApplication


class PostGrantPatent(TimeStampedModel):
    """Post-grant patent record (BW-PMS-14, 15, CW-PMS-04)."""

    application = models.OneToOneField(
        PatentApplication, on_delete=models.CASCADE, related_name="post_grant"
    )
    patent_number = models.CharField(max_length=100, unique=True, db_index=True)
    grant_date = models.DateField(db_index=True)
    term_years = models.IntegerField(default=20)
    expiry_date = models.DateField()
    current_cycle = models.IntegerField(default=1)

    class Meta:
        db_table = "pms_post_grant_patent"
        ordering = ["-grant_date"]

    def __str__(self) -> str:
        return f"Patent No. {self.patent_number} (Granted {self.grant_date})"


class MaintenanceSchedule(TimeStampedModel):
    """Maintenance fee schedule and renewal decision cycles (BR-PMS-059, 060, 061)."""

    post_grant = models.ForeignKey(
        PostGrantPatent, on_delete=models.CASCADE, related_name="schedules"
    )
    cycle_year = models.IntegerField()  # e.g. 3rd year, 4th year... up to 20th year
    due_date = models.DateField(db_index=True)
    fee_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=50, default="scheduled", db_index=True
    )  # scheduled, decision_requested, renewal_approved, renewed, do_not_renew
    payment_record_reference = models.CharField(max_length=100, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "pms_maintenance_schedule"
        ordering = ["due_date"]
        unique_together = ("post_grant", "cycle_year")

    def __str__(self) -> str:
        return f"Cycle {self.cycle_year} for {self.post_grant.patent_number} (Due: {self.due_date})"


class RenewalDecision(TimeStampedModel):
    """Director decision to renew or abandon patent (BR-PMS-061)."""

    schedule = models.OneToOneField(
        MaintenanceSchedule, on_delete=models.CASCADE, related_name="decision"
    )
    director_user_id = models.IntegerField(db_index=True)
    decision = models.CharField(max_length=50)  # renew, do_not_renew
    justification = models.TextField(blank=True)
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pms_renewal_decision"
        ordering = ["-decided_at"]

    def __str__(self) -> str:
        return f"{self.decision} on Schedule {self.schedule_id} by Director {self.director_user_id}"
