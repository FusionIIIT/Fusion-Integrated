from decimal import Decimal

from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveCategory(models.TextChoices):
    CL = "CL", "Casual Leave"
    RH = "RH", "Restricted Holiday"
    SCL = "SCL", "Special Casual Leave"
    EL = "EL", "Earned Leave"
    COL = "COL", "Compensatory / Balance Controlled Leave"
    VL = "VL", "Vacation Leave"


class HalfDay(models.TextChoices):
    NONE = "none", "None"
    FIRST = "first", "First half-day"
    SECOND = "second", "Second half-day"


class Stage(models.TextChoices):
    SUBSTITUTE = "substitute", "Substitute"
    UNIT_HEAD = "unit_head", "Unit Head"
    ESTABLISHMENT = "establishment", "Establishment"
    SANCTION = "sanction", "Sanctioning Authority"
    DONE = "done", "Done"


class Status(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    WITHDRAWN = "withdrawn", "Withdrawn"
    CANCELLED = "cancelled", "Cancelled"


class SubstituteStatus(models.TextChoices):
    NOT_REQUIRED = "not_required", "Not Required"
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    DECLINED = "declined", "Declined"


class RequestKind(models.TextChoices):
    LEAVE = "leave", "Leave"
    CANCELLATION = "cancellation", "Cancellation"


class ReportingLine(TimeStampedModel):
    """The reporting line for a leave application."""

    user_id = models.IntegerField(unique=True)
    unit_head_id = models.IntegerField()
    establishment_id = models.IntegerField(null=True, blank=True)
    sanctioning_authority_id = models.IntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "Reporting Line"
        verbose_name_plural = "Reporting Lines"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Reporting line for user {self.user_id}"


class LeaveApplication(UserScopedModel, TimeStampedModel):
    """A leave application submitted by an employee."""

    kind = models.CharField(
        max_length=12,
        choices=RequestKind.choices,
        default=RequestKind.LEAVE,
        verbose_name="Request Kind",
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="cancellations",
    )
    category = models.CharField(
        max_length=3,
        choices=LeaveCategory.choices,
        verbose_name="Leave Category",
    )
    start_date = models.DateField("Start Date")
    end_date = models.DateField("End Date")
    half_day = models.CharField(
        max_length=7,
        choices=HalfDay.choices,
        default=HalfDay.NONE,
        verbose_name="Half Day",
    )
    days = models.DecimalField(max_digits=5, decimal_places=1)
    purpose = models.TextField("Purpose / Reason")
    station_leave = models.BooleanField(default=False, verbose_name="Station Leave")
    station_address = models.TextField(blank=True, verbose_name="Station Address")
    substitute_id = models.IntegerField(
        null=True, blank=True, verbose_name="Nominated Substitute ID"
    )
    substitute_status = models.CharField(
        max_length=15,
        choices=SubstituteStatus.choices,
        default=SubstituteStatus.NOT_REQUIRED,
        verbose_name="Substitute Status",
    )
    unit_head_id = models.IntegerField()
    establishment_id = models.IntegerField(null=True, blank=True)
    sanctioning_authority_id = models.IntegerField(null=True, blank=True)
    unit_head_recommendation = models.CharField(
        max_length=20, blank=True, verbose_name="Unit Head Recommendation"
    )
    stage = models.CharField(
        max_length=15,
        choices=Stage.choices,
        default=Stage.SUBSTITUTE,
        verbose_name="Stage",
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Status",
    )
    assignee_id = models.IntegerField(null=True, blank=True, db_index=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Leave Application"
        verbose_name_plural = "Leave Applications"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return (
            f"{self.user_id}'s {self.category} application ({self.start_date} to {self.end_date})"
        )


class LeaveBalance(UserScopedModel, TimeStampedModel):
    """Per-user, per-year, per-category leave balance."""

    category = models.CharField(
        max_length=3,
        choices=LeaveCategory.choices,
        verbose_name="Leave Category",
    )
    year = models.IntegerField("Year")
    entitled = models.DecimalField(max_digits=5, decimal_places=1)
    used = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)

    class Meta:
        verbose_name = "Leave Balance"
        verbose_name_plural = "Leave Balances"
        ordering = ["-year", "-category"]
        unique_together = ["user_id", "year", "category"]

    @property
    def available(self) -> Decimal:
        """Calculate the available leave days."""
        return self.entitled - self.used

    def __str__(self) -> str:
        return f"{self.user_id}'s {self.category} balance for {self.year}"


class LeaveAction(models.Model):
    """Append-only history of actions taken on leave applications and balances."""

    application = models.ForeignKey(
        LeaveApplication,
        on_delete=models.CASCADE,
        related_name="actions",
    )
    actor_id = models.IntegerField("Actor ID")
    action = models.CharField(max_length=40)
    remark = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Leave Action"
        verbose_name_plural = "Leave Actions"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.action} on {self.application.id} by {self.actor_id}"
