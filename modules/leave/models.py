from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveCategory(models.TextChoices):
    CL = "CL", "Casual Leave"
    RH = "RH", "Restricted Holiday"
    SCL = "SCL", "Special Casual Leave"
    EL = "EL", "Earned Leave"
    COL = "COL", "Compensatory / Balance Controlled Leave"
    VL = "VL", "Vacation Leave"


class LeaveApplication(UserScopedModel):
    """A leave application submitted by an employee."""

    category = models.CharField(
        max_length=2,
        choices=LeaveCategory.choices,
        verbose_name="Leave Category",
    )
    requested_from = models.DateField("Requested From")
    requested_to = models.DateField("Requested To")
    purpose = models.TextField("Purpose / Reason")
    station_leave_details = models.JSONField(
        null=True, blank=True, verbose_name="Station Leave Details"
    )
    nominated_substitute_id = models.IntegerField(
        null=True, blank=True, verbose_name="Nominated Substitute ID",
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("under_review", "Under Review"),
            ("recommended", "Recommended"),
            ("not_recommended", "Not Recommended"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
            ("withdrawn", "Withdrawn"),
        ],
        default="draft",
    )

    class Meta:
        verbose_name = "Leave Application"
        verbose_name_plural = "Leave Applications"
        ordering = ["-requested_from"]

    def __str__(self) -> str:
        return f"{self.user_id}'s {self.category} application ({self.requested_from} to {self.requested_to})"


class LeaveBalance(UserScopedModel):
    """Per-user, per-year, per-category leave balance."""

    category = models.CharField(
        max_length=2,
        choices=LeaveCategory.choices,
        verbose_name="Leave Category",
    )
    year = models.IntegerField("Year")
    available_days = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    used_days = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)

    class Meta:
        verbose_name = "Leave Balance"
        verbose_name_plural = "Leave Balances"
        ordering = ["-year", "-category"]
        unique_together = ["user_id", "year", "category"]

    def __str__(self) -> str:
        return f"{self.user_id}'s {self.category} balance for {self.year}"


class LeaveActionHistory(models.Model):
    """Append-only history of actions taken on leave applications and balances."""

    application = models.ForeignKey(
        LeaveApplication,
        on_delete=models.CASCADE,
        related_name="action_history",
    )
    actor_id = models.IntegerField("Actor ID")
    action_type = models.CharField(max_length=50)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Leave Action History"
        verbose_name_plural = "Leave Action Histories"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action_type} on {self.application.id} by {self.actor_id}"
