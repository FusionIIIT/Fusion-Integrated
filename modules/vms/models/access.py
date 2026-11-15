"""Zones, gates, the versioned access policy, elevations, violations and
the time-bound VMS role assignments Super Admin hands out."""
from __future__ import annotations

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class Zone(TimeStampedModel):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=120)
    is_restricted = models.BooleanField(default=False)
    #: VMS-BR-031 — VIP passes only ever reach a designated VIP zone.
    is_vip_designated = models.BooleanField(default=False)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "vms_zone"

    def __str__(self) -> str:
        return self.code


class Gate(TimeStampedModel):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=120, blank=True)
    machine_id = models.CharField(max_length=64, unique=True)
    zone_code = models.CharField(max_length=32, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "vms_gate"

    def __str__(self) -> str:
        return f"{self.code}({self.machine_id})"


class AccessPolicy(TimeStampedModel):
    """Versioned runtime rules. Only PUBLISHED rows are consumed; edits
    create a new version and never disturb a visit already on-site."""

    STATUS = [("DRAFT", "Draft"), ("PUBLISHED", "Published"),
              ("RETIRED", "Retired")]

    name = models.CharField(max_length=120)
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=12, choices=STATUS, default="DRAFT",
                              db_index=True)
    visiting_hours_start = models.TimeField(default="09:00")
    visiting_hours_end = models.TimeField(default="18:00")
    #: Baseline defaults from the consolidated statement.
    max_visit_duration_hours = models.PositiveIntegerField(default=8)
    #: VMS-BR-032 — walk-in passes last 4 hours by default.
    walk_in_pass_duration_hours = models.PositiveIntegerField(default=4)
    #: VMS-BR-033 — registered guest passes default to 4 hours.
    registered_pass_duration_hours = models.PositiveIntegerField(default=4)
    #: VMS-BR-034 — a generic guest pass uses the configured duration.
    default_pass_duration_hours = models.PositiveIntegerField(default=8)
    approval_timeout_hours = models.PositiveIntegerField(default=24)
    #: VMS-BR-014 — when the approval-timeout warning is sent.
    approval_reminder_hours = models.PositiveIntegerField(default=6)
    advance_registration_hours = models.PositiveIntegerField(default=2)
    restricted_zones = models.JSONField(default=list, blank=True)
    #: VMS-BR-029 — guest operations must read this machine id.
    nominal_machine_id = models.CharField(max_length=64, default="GATE-NOMINAL")
    #: VMS-BR-045 — minutes on the muster roster before eviction.
    muster_eviction_grace_minutes = models.PositiveSmallIntegerField(default=15)
    is_default = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)
    created_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "vms_access_policy"
        constraints = [
            models.UniqueConstraint(
                fields=["is_default"],
                condition=Q(status="PUBLISHED", is_default=True),
                name="vms_policy_single_published_default",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "is_default"],
                         name="vms_policy_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} v{self.version} ({self.status})"


class ZoneElevation(TimeStampedModel):
    """Time-boxed access beyond the pass's designated zones (VMS-BR-042)."""

    visit_id = models.IntegerField(db_index=True)
    zone_code = models.CharField(max_length=32, db_index=True)
    granted_by_user_id = models.IntegerField()
    reason = models.CharField(max_length=255, blank=True)
    starts_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "vms_zone_elevation"
        indexes = [
            models.Index(fields=["visit_id", "zone_code", "is_active"],
                         name="vms_elevation_idx"),
        ]


class Violation(TimeStampedModel):
    """Only these two kinds may ever exist (VMS-BR-003). A double close is
    a ConflictError, not a third kind of row — see services.violations."""

    KINDS = [("EXPIRED_PASS", "Expired pass"),
             ("UNAUTHORIZED_ZONE", "Unauthorized zone access")]
    STATUS = [("OPEN", "Open"), ("RESOLVED", "Resolved")]

    visit_id = models.IntegerField(db_index=True)
    visitor_id = models.IntegerField(db_index=True)
    pass_id = models.IntegerField(null=True, blank=True)
    kind = models.CharField(max_length=24, choices=KINDS)
    status = models.CharField(max_length=12, choices=STATUS, default="OPEN",
                              db_index=True)
    zone_code = models.CharField(max_length=32, blank=True)
    details = models.JSONField(default=dict, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "vms_violation"
        indexes = [
            models.Index(fields=["visit_id", "kind", "status"],
                         name="vms_violation_idx"),
        ]


class VmsRoleAssignment(TimeStampedModel):
    """Time-bound operational roles. Reassignment is immediate: a row that is
    inactive or expired is read as not holding the role at all."""

    ROLES = [("ADMIN", "Admin"), ("SECURITY", "Security"),
             ("HOST", "Host")]

    user_id = models.IntegerField(db_index=True)
    role = models.CharField(max_length=16, choices=ROLES)
    #: Empty list means campus-wide; otherwise the assignment's scope.
    zone_codes = models.JSONField(default=list, blank=True)
    gate_code = models.CharField(max_length=32, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    assigned_by_user_id = models.IntegerField(null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "vms_role_assignment"
        indexes = [
            models.Index(fields=["user_id", "role", "is_active"],
                         name="vms_role_user_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.role}:{self.user_id}"


CampusZone = Zone
ZoneAccessLog = Violation



def _get_alert():
    from modules.vms.models.visitors import Alert
    return Alert


class _GateAlertProxy:
    def __getattr__(self, name):
        return getattr(_get_alert(), name)

    def __call__(self, *args, **kwargs):
        return _get_alert()(*args, **kwargs)


GateAlert = _GateAlertProxy()

