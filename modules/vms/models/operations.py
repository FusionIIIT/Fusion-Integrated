import uuid

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class GateAttempt(TimeStampedModel):
    RESULT = [
        ("allowed", "Allowed"),
        ("denied", "Denied"),
        ("override_pending", "Override pending"),
        ("overridden", "Overridden"),
    ]
    request = models.ForeignKey(
        "vms.VisitRequest",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="gate_attempts",
    )
    presented_fingerprint = models.CharField(max_length=64, blank=True, db_index=True)
    checkpoint = models.CharField(max_length=100, blank=True)
    result = models.CharField(max_length=20, choices=RESULT, db_index=True)
    failure_code = models.CharField(max_length=40, blank=True, db_index=True)
    actor_user_id = models.IntegerField(null=True, blank=True)
    attempted_at = models.DateTimeField(db_index=True)
    idempotency_key = models.CharField(max_length=100, blank=True)
    override_reason = models.CharField(max_length=500, blank=True)
    overridden_by_user_id = models.IntegerField(null=True, blank=True)
    overridden_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "vms_gate_attempt"
        constraints = [
            models.UniqueConstraint(
                fields=["idempotency_key"],
                condition=~Q(idempotency_key=""),
                name="vms_gate_attempt_idem_uq",
            )
        ]
        indexes = [
            models.Index(fields=["request", "-attempted_at"], name="vms_gate_attempt_req_idx")
        ]


class ZoneAccessEvent(models.Model):
    DECISION = [("granted", "Granted"), ("denied", "Denied"), ("exception", "Exception")]
    request = models.ForeignKey(
        "vms.VisitRequest", on_delete=models.PROTECT, related_name="zone_access_events"
    )
    zone = models.CharField(max_length=80, db_index=True)
    decision = models.CharField(max_length=12, choices=DECISION, db_index=True)
    reason_code = models.CharField(max_length=40, blank=True)
    occurred_at = models.DateTimeField(db_index=True)
    recorded_by_user_id = models.IntegerField(null=True, blank=True)
    source = models.CharField(max_length=20, default="online")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "vms_zone_access_event"
        indexes = [models.Index(fields=["zone", "-occurred_at"], name="vms_zone_event_idx")]

    def __str__(self):
        return f"Zone access {self.pk}: {self.zone} ({self.decision})"


class ZoneElevation(TimeStampedModel):
    request = models.ForeignKey(
        "vms.VisitRequest", on_delete=models.PROTECT, related_name="zone_elevations"
    )
    zone = models.CharField(max_length=80)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField(db_index=True)
    reason = models.CharField(max_length=500)
    granted_by_user_id = models.IntegerField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "vms_zone_elevation"
        constraints = [
            models.CheckConstraint(
                condition=Q(valid_until__gt=models.F("valid_from")),
                name="vms_zone_elevation_window",
            )
        ]
        indexes = [
            models.Index(
                fields=["request", "zone", "valid_until"], name="vms_zone_elev_runtime_idx"
            )
        ]


class ZoneAlert(TimeStampedModel):
    STATUS = [("open", "Open"), ("handled", "Handled"), ("false_positive", "False positive")]
    access_event = models.OneToOneField(
        ZoneAccessEvent, on_delete=models.PROTECT, related_name="alert"
    )
    status = models.CharField(max_length=16, choices=STATUS, default="open", db_index=True)
    handling_note = models.CharField(max_length=500, blank=True)
    handled_by_user_id = models.IntegerField(null=True, blank=True)
    handled_at = models.DateTimeField(null=True, blank=True)
    escalated_to_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "vms_zone_alert"
        indexes = [models.Index(fields=["status", "-created_at"], name="vms_zone_alert_idx")]


class EmergencyMuster(TimeStampedModel):
    STATUS = [("active", "Active"), ("completed", "Completed")]
    status = models.CharField(max_length=12, choices=STATUS, default="active", db_index=True)
    triggered_by_user_id = models.IntegerField()
    triggered_at = models.DateTimeField(db_index=True)
    location = models.CharField(max_length=160, blank=True)
    instructions = models.CharField(max_length=500, blank=True)
    roster_created_at = models.DateTimeField()
    roster_count = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by_user_id = models.IntegerField(null=True, blank=True)
    report = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "vms_emergency_muster"
        constraints = [
            models.UniqueConstraint(
                fields=["status"], condition=Q(status="active"), name="vms_one_active_muster_uq"
            )
        ]
        indexes = [models.Index(fields=["status", "-triggered_at"], name="vms_muster_live_idx")]


class MusterRollCall(models.Model):
    STATUS = [
        ("unaccounted", "Unaccounted"),
        ("accounted", "Accounted"),
        ("last_seen", "Last seen"),
    ]
    muster = models.ForeignKey(EmergencyMuster, on_delete=models.PROTECT, related_name="roll_calls")
    request = models.ForeignKey(
        "vms.VisitRequest", on_delete=models.PROTECT, related_name="muster_roll_calls"
    )
    status = models.CharField(max_length=16, choices=STATUS, default="unaccounted")
    note = models.CharField(max_length=300, blank=True)
    updated_by_user_id = models.IntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vms_muster_roll_call"
        constraints = [
            models.UniqueConstraint(fields=["muster", "request"], name="vms_muster_request_uq")
        ]

    def __str__(self):
        return f"Muster {self.muster_id}: visit {self.request_id} ({self.status})"


class OfflineGateEvent(TimeStampedModel):
    STATUS = [("pending", "Pending"), ("reconciled", "Reconciled"), ("conflict", "Conflict")]
    event_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    idempotency_key = models.CharField(max_length=100, unique=True)
    credential_nonce = models.UUIDField(db_index=True)
    checkpoint = models.CharField(max_length=100, blank=True)
    event_at = models.DateTimeField()
    recorded_by_user_id = models.IntegerField()
    status = models.CharField(max_length=12, choices=STATUS, default="pending", db_index=True)
    reconciliation_note = models.CharField(max_length=500, blank=True)
    reconciled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "vms_offline_gate_event"
        indexes = [models.Index(fields=["status", "created_at"], name="vms_offline_pending_idx")]


class EventRecord(TimeStampedModel):
    STATUS = [("draft", "Draft"), ("active", "Active"), ("completed", "Completed")]
    name = models.CharField(max_length=180)
    external_event_id = models.CharField(max_length=100, blank=True, db_index=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    zones = models.JSONField(default=list, blank=True)
    fast_lane_enabled = models.BooleanField(default=False)
    overflow_limit = models.PositiveIntegerField(null=True, blank=True)
    rate_limit_per_minute = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="draft", db_index=True)
    created_by_user_id = models.IntegerField()

    class Meta:
        db_table = "vms_event_record"
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__gt=models.F("starts_at")), name="vms_event_window_valid"
            )
        ]
        indexes = [models.Index(fields=["status", "starts_at"], name="vms_event_live_idx")]


class EventGuestBatch(models.Model):
    event = models.ForeignKey(EventRecord, on_delete=models.PROTECT, related_name="guest_batches")
    idempotency_key = models.CharField(max_length=100, unique=True)
    created_by_user_id = models.IntegerField()
    row_count = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vms_event_guest_batch"
        indexes = [models.Index(fields=["event", "-created_at"], name="vms_event_batch_idx")]

    def __str__(self):
        return f"Guest batch {self.pk} for event {self.event_id}"


class EventGuestBatchRow(models.Model):
    STATUS = [("accepted", "Accepted"), ("rejected", "Rejected")]
    batch = models.ForeignKey(EventGuestBatch, on_delete=models.PROTECT, related_name="rows")
    request = models.ForeignKey(
        "vms.VisitRequest",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="event_batch_rows",
    )
    submitted_visit_id = models.PositiveBigIntegerField()
    status = models.CharField(max_length=12, choices=STATUS)
    reason = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vms_event_guest_batch_row"
        constraints = [
            models.UniqueConstraint(
                fields=["batch", "submitted_visit_id"], name="vms_event_batch_visit_uq"
            )
        ]

    def __str__(self):
        return f"Guest import visit {self.submitted_visit_id} ({self.status})"
