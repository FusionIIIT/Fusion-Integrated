from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel
from decimal import Decimal

class LeaveApplication(TimeStampedModel, UserScopedModel):
    category = models.CharField(max_length=10, choices=[
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("VL", "Vacation Leave"),
        ("COL", "Commuted Leave")
    ])
    start_date = models.DateField()
    end_date = models.DateField()
    half_day_type = models.CharField(max_length=15, default="full", choices=[
        ("full", "Full Day"),
        ("first_half", "First Half"),
        ("second_half", "Second Half")
    ])
    days_count = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("1.00"))
    purpose = models.TextField()
    address_during_leave = models.TextField(blank=True)
    
    is_station_leave = models.BooleanField(default=False)
    station_departure_date = models.DateField(null=True, blank=True)
    station_arrival_date = models.DateField(null=True, blank=True)
    station_destination = models.CharField(max_length=255, blank=True)
    
    status = models.CharField(max_length=30, default="under_review", choices=[
        ("draft", "Draft"),
        ("substitute_pending", "Pending Substitute Consent"),
        ("substitute_declined", "Substitute Declined"),
        ("under_review", "Under Unit Head Review"),
        ("establishment_review", "Under Establishment Review"),
        ("sanction_review", "Under Sanction Authority Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("cancel_requested", "Cancellation Requested"),
        ("cancelled", "Cancelled"),
        ("extension_requested", "Extension Requested"),
        ("resumption_submitted", "Resumption Submitted"),
        ("closed", "Closed")
    ])
    
    unit_head_user_id = models.IntegerField(null=True, blank=True)
    unit_head_recommended = models.BooleanField(null=True, blank=True)
    unit_head_remarks = models.TextField(blank=True)
    unit_head_reviewed_at = models.DateTimeField(null=True, blank=True)
    
    establishment_user_id = models.IntegerField(null=True, blank=True)
    establishment_remarks = models.TextField(blank=True)
    establishment_reviewed_at = models.DateTimeField(null=True, blank=True)
    
    sanctioning_authority_user_id = models.IntegerField(null=True, blank=True)
    sanctioning_remarks = models.TextField(blank=True)
    sanctioned_at = models.DateTimeField(null=True, blank=True)
    
    parent_leave = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="extensions")
    cancellation_reason = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    resumption_date = models.DateField(null=True, blank=True)
    actual_days_count = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    resumption_remarks = models.TextField(blank=True)
    resumption_reviewed_at = models.DateTimeField(null=True, blank=True)
    
    is_offline_sanctioned = models.BooleanField(default=False)
    offline_reference_no = models.CharField(max_length=120, blank=True)
    offline_sanction_date = models.DateField(null=True, blank=True)
    
    class Meta:
        db_table = "leave_application"
        indexes = [
            models.Index(fields=["user_id", "status"]),
            models.Index(fields=["start_date", "end_date"]),
            models.Index(fields=["status"])
        ]
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"leave#{self.pk} u{self.user_id} {self.category} {self.status}"