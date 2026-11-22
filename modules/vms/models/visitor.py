"""Visitor and pass-related models for VMS."""

from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel


class Visitor(TimeStampedModel):
    """Core identity record for a visitor."""

    ID_DOCUMENT_TYPES = [
        ("AADHAAR", "Aadhaar Card"),
        ("PAN", "PAN Card"),
        ("PASSPORT", "Passport"),
        ("VOTER_ID", "Voter ID"),
        ("DRIVING_LICENSE", "Driving License"),
        ("INSTITUTE_ID", "Institute ID"),
        ("OTHER", "Other Government ID"),
    ]

    name = models.CharField(max_length=150)
    email = models.EmailField(db_index=True)
    phone = models.CharField(max_length=20, db_index=True)
    organization = models.CharField(max_length=150, blank=True)
    id_document_type = models.CharField(max_length=30, choices=ID_DOCUMENT_TYPES, default="AADHAAR")
    id_document_number = models.CharField(max_length=100, db_index=True)
    is_vip = models.BooleanField(default=False)
    vip_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email", "phone"]),
            models.Index(fields=["id_document_type", "id_document_number"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.phone})"


class VisitRequest(TimeStampedModel):
    """Specific visit booking."""

    STATUS_CHOICES = [
        ("PENDING_APPROVAL", "Pending Host Approval"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("EXPIRED", "Expired"),
        ("CANCELLED", "Cancelled"),
        ("CHECKED_IN", "Checked In"),
        ("CHECKED_OUT", "Checked Out"),
        ("AUTO_CHECKED_OUT", "Auto Checked Out"),
        ("TERMINATED_EARLY", "Terminated Early"),
    ]

    PASS_TYPES = [
        ("PRE_REGISTERED", "Pre-registered"),
        ("WALK_IN", "Walk-in"),
        ("VIP", "VIP"),
        ("CONTRACTOR", "Contractor"),
        ("EVENT", "Event Attendee"),
    ]

    visitor = models.ForeignKey(Visitor, on_delete=models.PROTECT, related_name="visit_requests")
    host_id = models.PositiveIntegerField(db_index=True)
    host_name = models.CharField(max_length=150, blank=True)
    purpose = models.CharField(max_length=255)
    scheduled_start = models.DateTimeField(db_index=True)
    scheduled_end = models.DateTimeField(db_index=True)
    actual_check_in = models.DateTimeField(null=True, blank=True)
    actual_check_out = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=32, choices=STATUS_CHOICES, default="PENDING_APPROVAL", db_index=True
    )
    pass_type = models.CharField(max_length=30, choices=PASS_TYPES, default="PRE_REGISTERED")
    access_zones = models.JSONField(default=list, blank=True)
    admin_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    is_urgent_exception = models.BooleanField(default=False)
    extension_hours = models.PositiveIntegerField(default=0)
    external_event_ref = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["host_id", "status"]),
            models.Index(fields=["scheduled_start", "scheduled_end"]),
        ]

    def __str__(self) -> str:
        return f"Visit #{self.pk} - {self.visitor.name} to host {self.host_id} [{self.status}]"


class Pass(TimeStampedModel):
    """Digital pass credentials for verified gate and zone access."""

    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("USED", "Used"),
        ("EXPIRED", "Expired"),
        ("REVOKED", "Revoked"),
    ]

    visit_request = models.OneToOneField(
        VisitRequest, on_delete=models.PROTECT, related_name="digital_pass"
    )
    pass_number = models.CharField(max_length=64, unique=True, db_index=True)
    qr_token = models.CharField(max_length=128, unique=True, db_index=True)
    pass_type = models.CharField(
        max_length=30, choices=VisitRequest.PASS_TYPES, default="PRE_REGISTERED"
    )
    valid_from = models.DateTimeField(db_index=True)
    valid_to = models.DateTimeField(db_index=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="ACTIVE", db_index=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Pass {self.pass_number} [{self.status}]"


class GateCheckLog(TimeStampedModel):
    """Audit log of check-in, check-out, denials and overrides at gates and zones."""

    CHECKPOINT_TYPES = [
        ("ENTRY", "Entry Gate"),
        ("EXIT", "Exit Gate"),
        ("ZONE_CHECK", "Zone Checkpoint"),
    ]

    ACTIONS = [
        ("CHECK_IN", "Check In"),
        ("CHECK_OUT", "Check Out"),
        ("DENIED", "Access Denied"),
        ("OVERRIDE", "Manual Override"),
    ]

    pass_record = models.ForeignKey(Pass, on_delete=models.PROTECT, related_name="check_logs")
    gate_name = models.CharField(max_length=100)
    checkpoint_type = models.CharField(max_length=20, choices=CHECKPOINT_TYPES, default="ENTRY")
    action = models.CharField(max_length=20, choices=ACTIONS)
    operator_id = models.PositiveIntegerField(null=True, blank=True)
    is_override = models.BooleanField(default=False)
    override_reason = models.TextField(blank=True)
    is_offline_sync = models.BooleanField(default=False)
    timestamp = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"{self.action} on Pass {self.pass_record_id} at {self.gate_name}"


class HostPreAuthorization(TimeStampedModel):
    """Host pre-authorization allowing frequent visitors to bypass individual approval."""

    host_id = models.PositiveIntegerField(db_index=True)
    visitor_email = models.EmailField(db_index=True)
    visitor_name = models.CharField(max_length=150)
    valid_from = models.DateField(db_index=True)
    valid_to = models.DateField(db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"PreAuth by host {self.host_id} for {self.visitor_email}"
