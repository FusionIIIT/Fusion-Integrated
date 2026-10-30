from decimal import Decimal
from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveApplication(TimeStampedModel, UserScopedModel):
    leave_category = models.CharField(max_length=8)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day_type = models.CharField(max_length=16, blank=True, default="")
    calculated_days = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("1.0"))
    reason = models.TextField()
    status = models.CharField(max_length=32, default="pending_unit_head", db_index=True)

    # Substitute coverage (Section 6)
    substitute_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    substitute_status = models.CharField(max_length=16, default="none")
    substitute_remarks = models.TextField(blank=True)

    # Station Leave details inside same application (Section 2)
    is_station_leave = models.BooleanField(default=False)
    station_start_date = models.DateField(null=True, blank=True)
    station_end_date = models.DateField(null=True, blank=True)
    station_destination = models.CharField(max_length=255, blank=True)
    station_contact_address = models.TextField(blank=True)
    station_emergency_phone = models.CharField(max_length=32, blank=True)

    # Unit Head Review (Section 7)
    unit_head_user_id = models.IntegerField(null=True, blank=True)
    unit_head_recommendation = models.CharField(max_length=32, blank=True)
    unit_head_remarks = models.TextField(blank=True)

    # Sanctioning Authority Decision (Section 7)
    sanctioning_authority_user_id = models.IntegerField(null=True, blank=True)
    final_decision = models.CharField(max_length=16, blank=True)
    final_decision_date = models.DateTimeField(null=True, blank=True)
    final_remarks = models.TextField(blank=True)

    # Cancellation (Section 8)
    cancellation_reason = models.TextField(blank=True)

    # Extension (Section 9)
    is_extension = models.BooleanField(default=False)
    parent_application_id = models.IntegerField(null=True, blank=True)

    # Resumption (Section 10)
    resumption_date = models.DateField(null=True, blank=True)
    resumption_status = models.CharField(max_length=16, blank=True)
    resumption_remarks = models.TextField(blank=True)

    # Offline synchronization (Section 12)
    is_offline_sanctioned = models.BooleanField(default=False)
    offline_sanction_reference = models.CharField(max_length=128, blank=True)

    class Meta:
        db_table = "elm_leave_application"
        indexes = [
            models.Index(fields=["user_id", "status"], name="elm_app_user_status_idx"),
            models.Index(fields=["substitute_user_id", "status"], name="elm_app_sub_status_idx"),
            models.Index(fields=["start_date", "end_date"], name="elm_app_dates_idx"),
        ]

    def __str__(self) -> str:
        return f"leave#{self.pk} u{self.user_id} {self.leave_category} ({self.status})"


class ApplicationTransition(models.Model):
    application = models.ForeignKey(
        LeaveApplication,
        on_delete=models.CASCADE,
        related_name="transitions",
    )
    from_status = models.CharField(max_length=32)
    to_status = models.CharField(max_length=32)
    actor_user_id = models.IntegerField()
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_application_transition"
        ordering = ["created_at"]
