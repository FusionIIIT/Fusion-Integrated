"""Zones, gates and visit requests."""
from django.db import models

from .base import choice_check


class Zone(models.Model):
    """A campus area a pass may allow (VMS-BR-191 unauthorized zone access)."""
    name = models.CharField(max_length=80, unique=True)
    is_restricted = models.BooleanField(default=False)
    parent_zone = models.ForeignKey("self", null=True, blank=True,
                                    on_delete=models.PROTECT,
                                    related_name="children")
    is_active = models.BooleanField(default=True)


class Gate(models.Model):
    """An entry point (VMS-CFR-013, CFR-026)."""
    name = models.CharField(max_length=80, unique=True)
    zone = models.ForeignKey(Zone, on_delete=models.PROTECT, related_name="gates")
    device_id = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)


class VisitRequest(models.Model):
    """A host's request to receive a visitor; approved or rejected by staff."""

    class Status(models.TextChoices):
        PENDING = "pending"
        AWAITING_ADMIN = "awaiting_admin"   # contingency: host unavailable (BR-050)
        APPROVED = "approved"
        REJECTED = "rejected"
        EXPIRED = "expired"      # approval_timeout_hours elapsed undecided
        COMPLETED = "completed"

    class Source(models.TextChoices):
        PRE_REGISTERED = "pre_registered"
        WALK_IN = "walk_in"
        BULK = "bulk"
        VIP = "vip"
        PRE_AUTHORIZED = "pre_authorized"

    class UrgentDecision(models.TextChoices):
        NONE = "none"
        PENDING = "pending"
        APPROVED = "approved"
        REJECTED = "rejected"

    visitor = models.ForeignKey("vms.Visitor", on_delete=models.PROTECT,
                                related_name="requests")
    created_by_visitor = models.ForeignKey(
        "vms.Visitor", null=True, blank=True, on_delete=models.PROTECT,
        related_name="created_requests")
    host_user_id = models.IntegerField(db_index=True)
    purpose = models.CharField(max_length=255)
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices,
                              default=Status.PENDING, db_index=True)
    source = models.CharField(max_length=20, choices=Source.choices,
                              default=Source.PRE_REGISTERED)
    is_urgent = models.BooleanField(default=False)
    urgent_decision = models.CharField(max_length=10,
                                       choices=UrgentDecision.choices,
                                       default=UrgentDecision.NONE)
    urgent_decided_by_user_id = models.IntegerField(null=True, blank=True)
    requested_zones = models.ManyToManyField(Zone, blank=True,
                                             related_name="requests")
    decision_note = models.CharField(max_length=255, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    reminded_at = models.DateTimeField(null=True, blank=True)
    contingency_requested_at = models.DateTimeField(null=True, blank=True)
    contingency_approved_by_user_id = models.IntegerField(null=True, blank=True)
    event = models.ForeignKey("vms.EventBatch", null=True, blank=True,
                              on_delete=models.PROTECT, related_name="requests")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "host_user_id"],
                         name="vms_req_status_host_idx"),
            models.Index(fields=["status", "expires_at"],
                         name="vms_req_status_expiry_idx"),
        ]

    Meta.constraints = [
        choice_check("status", Status, "vms_req_status_valid"),
        choice_check("source", Source, "vms_req_source_valid"),
        choice_check("urgent_decision", UrgentDecision,
                     "vms_req_urgent_decision_valid"),
    ]
