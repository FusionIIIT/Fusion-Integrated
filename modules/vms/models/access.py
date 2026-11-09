"""Passes, the gate trail, elevations, overrides and escalations."""
from django.db import models

from .base import AppendOnlyModel, choice_check
from .core import VisitRequest


class VisitPass(models.Model):
    """Gate credential: QR token plus OTP, valid for a window."""

    class PassType(models.TextChoices):
        PRE_REGISTERED = "PRE_REGISTERED"
        WALK_IN = "WALK_IN"      # short validity, walk_in_pass_hours
        VIP = "VIP"

    visit_request = models.ForeignKey(VisitRequest, on_delete=models.PROTECT,
                                      related_name="passes")
    pass_type = models.CharField(max_length=16, choices=PassType.choices)
    qr_token = models.CharField(max_length=64, unique=True)
    otp = models.CharField(max_length=8)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    allowed_zones = models.ManyToManyField("vms.Zone", blank=True,
                                           related_name="passes")
    issued_by_user_id = models.IntegerField()
    issued_for_source = models.CharField(
        max_length=20, choices=VisitRequest.Source.choices, blank=True)
    terminated_at = models.DateTimeField(null=True, blank=True)
    terminated_by_user_id = models.IntegerField(null=True, blank=True)
    termination_reason = models.CharField(max_length=255, blank=True)
    event = models.ForeignKey("vms.EventBatch", null=True, blank=True,
                              on_delete=models.PROTECT, related_name="passes")
    fast_lane = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["otp", "is_active"],
                                name="vms_pass_otp_active_idx")]

    Meta.constraints = [
        models.CheckConstraint(
            condition=models.Q(issued_for_source="")
            | models.Q(issued_for_source__in=[
                c.value for c in VisitRequest.Source]),
            name="vms_pass_source_valid"),
        choice_check("pass_type", PassType, "vms_pass_type_valid"),
    ]

    def __str__(self) -> str:
        return f"Pass {self.pk} ({self.pass_type}, request {self.visit_request_id})"


class VisitLog(AppendOnlyModel):
    """Append-only gate event trail (never updated or deleted)."""

    class Event(models.TextChoices):
        CHECK_IN = "check_in"
        CHECK_OUT = "check_out"
        DENIED = "denied"
        ZONE_ALLOWED = "zone_allowed"
        ZONE_DENIED = "zone_denied"
        OVERRIDE = "override"
        TERMINATED = "terminated"
        AUTO_CHECK_OUT = "auto_check_out"

    visit_pass = models.ForeignKey(VisitPass, on_delete=models.PROTECT,
                                   related_name="logs")
    event = models.CharField(max_length=20, choices=Event.choices)
    zone = models.ForeignKey("vms.Zone", null=True, blank=True,
                             on_delete=models.PROTECT)
    gate = models.ForeignKey("vms.Gate", null=True, blank=True,
                             on_delete=models.PROTECT, related_name="logs")
    entry_point = models.CharField(max_length=80, blank=True)
    device_id = models.CharField(max_length=80, blank=True)
    reason = models.CharField(max_length=255, blank=True)
    # Structured facts: failures (list of codes), vip_override, override, manual.
    detail = models.JSONField(default=dict, blank=True)
    # Null for system-generated events (auto check-out, scheduled work).
    logged_by_user_id = models.IntegerField(null=True, blank=True)
    offline = models.BooleanField(default=False)
    client_event_id = models.UUIDField(null=True, blank=True, unique=True)
    occurred_at = models.DateTimeField(null=True, blank=True)   # device time (D-10)
    synced_at = models.DateTimeField(null=True, blank=True)
    conflict = models.BooleanField(default=False)               # D-10
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["visit_pass", "created_at"],
                                name="vms_log_pass_created_idx")]

    Meta.constraints = [choice_check("event", Event, "vms_log_event_valid")]

    def __str__(self) -> str:
        return f"VisitLog {self.pk} ({self.event}, pass {self.visit_pass_id})"


class ZoneElevation(models.Model):
    """Time-boxed extra zone access for one pass (VMS-CFR-026, D-15)."""
    visit_pass = models.ForeignKey(VisitPass, on_delete=models.PROTECT,
                                   related_name="elevations")
    zone = models.ForeignKey("vms.Zone", on_delete=models.PROTECT,
                             related_name="elevations")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    granted_by_user_id = models.IntegerField()
    reason = models.CharField(max_length=255)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        pass

    Meta.constraints = [models.CheckConstraint(
        condition=models.Q(ends_at__gt=models.F("starts_at")),
        name="vms_elevation_window_valid")]

    def __str__(self) -> str:
        return f"ZoneElevation {self.pk} (pass {self.visit_pass_id}, zone {self.zone_id})"


class GateOverride(models.Model):
    """Admin override of a gate denial (VMS-CFR-014)."""
    visit_log = models.ForeignKey(VisitLog, on_delete=models.PROTECT,
                                  related_name="overrides")
    admin_user_id = models.IntegerField()
    justification = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"GateOverride {self.pk} (log {self.visit_log_id})"


class Escalation(models.Model):
    """Security escalates a denial to an Admin (VMS-CFR-014)."""

    class Status(models.TextChoices):
        OPEN = "open"
        RESOLVED = "resolved"

    visit_log = models.ForeignKey(VisitLog, on_delete=models.PROTECT,
                                  related_name="escalations")
    raised_by_user_id = models.IntegerField()
    note = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices,
                              default=Status.OPEN)
    resolved_by_user_id = models.IntegerField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        pass

    Meta.constraints = [choice_check("status", Status, "vms_escalation_status_valid")]

    def __str__(self) -> str:
        return f"Escalation {self.pk} ({self.status})"
