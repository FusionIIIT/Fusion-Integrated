import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class VisitRequest(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending Host Approval"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        EXPIRED = "EXPIRED", "Expired"
        ON_SITE = "ON_SITE", "On-site"
        COMPLETED = "COMPLETED", "Completed"
        TERMINATED = "TERMINATED", "Terminated"

    class VisitType(models.TextChoices):
        PRE_REGISTERED = "PRE_REGISTERED", "Pre-registered"
        WALK_IN = "WALK_IN", "Walk-in"

    visitor_name = models.CharField(max_length=150)
    visitor_email = models.EmailField()
    visitor_phone = models.CharField(max_length=20)
    identity_document_type = models.CharField(max_length=50)
    identity_document_reference = models.CharField(max_length=100)

    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="vms_hosted_visits",
    )

    purpose = models.TextField()
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()

    visit_type = models.CharField(
        max_length=20,
        choices=VisitType.choices,
        default=VisitType.PRE_REGISTERED,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    submitted_at = models.DateTimeField(default=timezone.now)
    decision_at = models.DateTimeField(null=True, blank=True)
    decision_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="vms_visit_decisions",
    )
    decision_note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.visitor_name} - {self.status}"


class VisitorPass(models.Model):

    class PassType(models.TextChoices):
        PRE_REGISTERED = "PRE_REGISTERED", "Pre-registered"
        WALK_IN = "WALK_IN", "Walk-in"
        VIP = "VIP", "VIP"

    visit_request = models.OneToOneField(
        VisitRequest,
        on_delete=models.PROTECT,
        related_name="visitor_pass",
    )

    credential = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    pass_type = models.CharField(
        max_length=20,
        choices=PassType.choices,
    )

    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()

    is_active = models.BooleanField(default=True)

    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pass for visit {self.visit_request_id}"


class VisitLog(models.Model):

    class EventType(models.TextChoices):
        CHECK_IN = "CHECK_IN", "Check-in"
        CHECK_OUT = "CHECK_OUT", "Check-out"
        DENIED = "DENIED", "Gate validation denied"
        TERMINATED = "TERMINATED", "Visit terminated"

    visit_request = models.ForeignKey(
        VisitRequest,
        on_delete=models.PROTECT,
        related_name="logs",
    )

    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices,
    )

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
    )

    checkpoint = models.CharField(max_length=100, blank=True)
    remarks = models.TextField(blank=True)

    event_time = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.event_type} - {self.visit_request_id}"