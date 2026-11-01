"""Database models for Visitor Management System (VMS).

Implements EBC Entity classes from Basis Workflow BW-VMS-01:
  - Visitor (VMS-E-05)
  - Host (VMS-E-06)
  - BlacklistRegistry (VMS-E-07)
  - CampusGate (VMS-E-08)
  - VisitRequest (VMS-E-01)
  - HostDecision (VMS-E-04)
  - VisitorPass (VMS-E-02)
  - VisitLog (VMS-E-03)
"""
import uuid
from django.db import models
from django.utils import timezone
from core.db.mixins import TimeStampedModel


def generate_uuid():
    return uuid.uuid4().hex[:12].upper()


class Visitor(TimeStampedModel):
    """VMS-E-05: Actor-representing entity persisting visitor profile."""
    visitor_id = models.CharField(max_length=32, primary_key=True, default=generate_uuid)
    full_name = models.CharField(max_length=120)
    email = models.EmailField(db_index=True)
    phone = models.CharField(max_length=20, db_index=True)
    id_document_type = models.CharField(max_length=40, default="AADHAAR")  # AADHAAR, PASSPORT, PAN, VOTER_ID, DRIVING_LICENSE
    id_document_number = models.CharField(max_length=64, db_index=True)
    organization = models.CharField(max_length=150, blank=True, default="")

    class Meta:
        db_table = "vms_visitor"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} ({self.phone})"


class Host(TimeStampedModel):
    """VMS-E-06: Campus member who hosts the visit."""
    host_id = models.CharField(max_length=32, primary_key=True, default=generate_uuid)
    user_id = models.IntegerField(unique=True, help_text="Reference to Fusion user_id")
    employee_id = models.CharField(max_length=32, blank=True, default="")
    full_name = models.CharField(max_length=120)
    department = models.CharField(max_length=80, blank=True, default="")
    designation = models.CharField(max_length=80, blank=True, default="")
    email = models.EmailField()
    office_location = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        db_table = "vms_host"

    def __str__(self):
        return f"{self.full_name} ({self.department})"


class BlacklistRegistry(TimeStampedModel):
    """VMS-E-07: Security blacklist registry matching visitor records."""
    entry_id = models.CharField(max_length=32, primary_key=True, default=generate_uuid)
    phone = models.CharField(max_length=20, blank=True, default="", db_index=True)
    id_document_number = models.CharField(max_length=64, blank=True, default="", db_index=True)
    full_name = models.CharField(max_length=120, blank=True, default="")
    reason = models.TextField()
    is_active = models.BooleanField(default=True)
    flagged_by = models.IntegerField(help_text="User ID who added the entry")

    class Meta:
        db_table = "vms_blacklist_registry"
        indexes = [
            models.Index(fields=["phone", "is_active"]),
            models.Index(fields=["id_document_number", "is_active"]),
        ]

    def __str__(self):
        return f"Blacklist: {self.full_name or self.phone} ({self.reason})"


class CampusGate(TimeStampedModel):
    """VMS-E-08: Campus physical checkpoint where entry/exit occurs."""
    gate_id = models.CharField(max_length=32, primary_key=True)
    gate_name = models.CharField(max_length=80)
    gate_type = models.CharField(max_length=30, default="MAIN_GATE")  # MAIN_GATE, HOSTEL_GATE, ACADEMIC_GATE
    location_zone = models.CharField(max_length=50, default="MAIN_CAMPUS")
    is_operational = models.BooleanField(default=True)

    class Meta:
        db_table = "vms_campus_gate"

    def __str__(self):
        return f"{self.gate_name} ({self.gate_id})"


class RequestStatus(models.TextChoices):
    NOT_SUBMITTED = "NOT_SUBMITTED", "Not Submitted"
    PENDING_HOST_APPROVAL = "PENDING_HOST_APPROVAL", "Pending Host Approval"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"
    EXPIRED = "EXPIRED", "Expired"
    COMPLETED = "COMPLETED", "Completed"


class PassStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    EXPIRED = "EXPIRED", "Expired"
    DEACTIVATED = "DEACTIVATED", "Deactivated"
    COMPLETED = "COMPLETED", "Completed"


class PassType(models.TextChoices):
    PRE_REGISTERED = "PRE_REGISTERED", "Pre-Registered"
    WALK_IN = "WALK_IN", "Walk-In"
    VIP = "VIP", "VIP"


class VisitStatus(models.TextChoices):
    ON_SITE = "ON_SITE", "On-site"
    COMPLETED = "COMPLETED", "Completed"
    FLAGGED = "FLAGGED", "Flagged"


class VisitRequest(TimeStampedModel):
    """VMS-E-01: Represents a pre-registration visit request."""
    request_id = models.CharField(max_length=32, primary_key=True, default=generate_uuid)
    visitor = models.ForeignKey(Visitor, on_delete=models.CASCADE, related_name="requests")
    host = models.ForeignKey(Host, on_delete=models.PROTECT, related_name="hosted_requests")
    purpose = models.CharField(max_length=255)
    scheduled_start_time = models.DateTimeField()
    scheduled_end_time = models.DateTimeField()
    status = models.CharField(
        max_length=30,
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING_HOST_APPROVAL,
        db_index=True,
    )
    submission_timestamp = models.DateTimeField(default=timezone.now)
    remarks = models.TextField(blank=True, default="")

    class Meta:
        db_table = "vms_visit_request"
        ordering = ["-submission_timestamp"]

    def __str__(self):
        return f"Req-{self.request_id}: {self.visitor.full_name} -> {self.host.full_name} [{self.status}]"


class HostDecision(TimeStampedModel):
    """VMS-E-04: Explicit review and decision by the Host."""
    decision_id = models.CharField(max_length=32, primary_key=True, default=generate_uuid)
    request = models.OneToOneField(VisitRequest, on_delete=models.CASCADE, related_name="decision")
    host = models.ForeignKey(Host, on_delete=models.PROTECT)
    outcome = models.CharField(max_length=20)  # APPROVE, REJECT
    decided_at = models.DateTimeField(default=timezone.now)
    allowed_start_time = models.DateTimeField(null=True, blank=True)
    allowed_end_time = models.DateTimeField(null=True, blank=True)
    permitted_zones = models.JSONField(default=list, blank=True)
    special_instructions = models.TextField(blank=True, default="")

    class Meta:
        db_table = "vms_host_decision"


class VisitorPass(TimeStampedModel):
    """VMS-E-02: Issued physical or digital credential authorizing campus access."""
    pass_id = models.CharField(max_length=32, primary_key=True, default=generate_uuid)
    request = models.ForeignKey(VisitRequest, on_delete=models.CASCADE, related_name="passes")
    pass_type = models.CharField(max_length=25, choices=PassType.choices, default=PassType.PRE_REGISTERED)
    credential_data = models.CharField(max_length=128, unique=True, db_index=True)  # Secret token / QR code data
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    status = models.CharField(max_length=25, choices=PassStatus.choices, default=PassStatus.ACTIVE, db_index=True)
    permitted_zones = models.JSONField(default=list)

    class Meta:
        db_table = "vms_visitor_pass"
        ordering = ["-valid_from"]

    def __str__(self):
        return f"Pass-{self.pass_id} [{self.status}] ({self.pass_type})"


class VisitLog(TimeStampedModel):
    """VMS-E-03: Physical visit session tracking entry and exit."""
    log_id = models.CharField(max_length=32, primary_key=True, default=generate_uuid)
    visitor_pass = models.ForeignKey(VisitorPass, on_delete=models.CASCADE, related_name="logs")
    entry_gate = models.ForeignKey(CampusGate, on_delete=models.PROTECT, related_name="entry_logs")
    exit_gate = models.ForeignKey(CampusGate, on_delete=models.PROTECT, null=True, blank=True, related_name="exit_logs")
    check_in_time = models.DateTimeField(default=timezone.now)
    check_out_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=VisitStatus.choices, default=VisitStatus.ON_SITE)
    verifier_notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "vms_visit_log"
        ordering = ["-check_in_time"]

    def __str__(self):
        return f"Log-{self.log_id}: Pass {self.visitor_pass.pass_id} [{self.status}]"
