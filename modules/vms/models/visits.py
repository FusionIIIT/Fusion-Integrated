"""The visit lifecycle: request -> pass -> check-in -> check-out.

Status vocabulary is the frozen baseline's:
    VisitRequest: PENDING, APPROVED, REJECTED, EXPIRED, CANCELLED
    Visit:        SCHEDULED, ON_SITE, COMPLETED, TERMINATED, INVALIDATED
    Pass:         ACTIVE, DEACTIVATED, EXPIRED
"""
from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel


class VisitRequest(TimeStampedModel):
    STATUS = [("PENDING", "Pending"), ("APPROVED", "Approved"),
              ("REJECTED", "Rejected"), ("EXPIRED", "Expired"),
              ("CANCELLED", "Cancelled")]
    SOURCE = [("PRE_REGISTERED", "Pre-registered"), ("WALK_IN", "Walk-in"),
              ("EVENT", "Event"), ("SAFE_LIST", "Safe-list")]

    visitor_id = models.IntegerField(db_index=True)
    host_user_id = models.IntegerField(db_index=True)
    host_contact_email = models.EmailField(blank=True)
    host_contact_phone = models.CharField(max_length=20, blank=True)
    #: VMS-BR-022 — every channel is suppressed while this is set.
    host_contacts_disabled = models.BooleanField(default=False)
    purpose = models.CharField(max_length=255)
    requested_start = models.DateTimeField(null=True, blank=True)
    requested_end = models.DateTimeField(null=True, blank=True)
    requested_zones = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=16, choices=STATUS, default="PENDING",
                              db_index=True)
    source = models.CharField(max_length=16, choices=SOURCE,
                              default="PRE_REGISTERED")
    instructions = models.TextField(blank=True)
    decision_notes = models.CharField(max_length=255, blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True)
    decision_at = models.DateTimeField(null=True, blank=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    #: VMS-BR-007 — every notification about this request carries this id.
    original_request_id = models.CharField(max_length=64, blank=True)
    #: Approval timeout (default 24h) — after this the request auto-expires.
    approval_expires_at = models.DateTimeField(null=True, blank=True)
    #: VMS-BR-012 — a request made on a shared badge still notifies the host.
    is_shared_badge = models.BooleanField(default=False)
    created_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "vms_visit_request"
        indexes = [
            models.Index(fields=["status", "approval_expires_at"],
                         name="vms_vreq_status_exp_idx"),
            models.Index(fields=["visitor_id", "status"],
                         name="vms_vreq_visitor_idx"),
        ]

    def __str__(self) -> str:
        return f"request#{self.id}:{self.status}"


class Visit(TimeStampedModel):
    STATUS = [("SCHEDULED", "Scheduled"), ("ON_SITE", "On-site"),
              ("COMPLETED", "Completed"), ("TERMINATED", "Terminated"),
              ("INVALIDATED", "Invalidated")]

    visit_request_id = models.IntegerField(null=True, blank=True, db_index=True)
    visitor_id = models.IntegerField(db_index=True)
    host_user_id = models.IntegerField(db_index=True)
    purpose = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=16, choices=STATUS, default="SCHEDULED",
                              db_index=True)
    source = models.CharField(max_length=16,
                              choices=VisitRequest.SOURCE,
                              default="PRE_REGISTERED")
    is_walk_in = models.BooleanField(default=False)
    scheduled_start = models.DateTimeField(null=True, blank=True)
    scheduled_end = models.DateTimeField(null=True, blank=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    checked_in_by_user_id = models.IntegerField(null=True, blank=True)
    checked_out_by_user_id = models.IntegerField(null=True, blank=True)
    checked_in_machine_id = models.CharField(max_length=64, blank=True)
    gate_code = models.CharField(max_length=32, blank=True)
    #: VMS-BR-018 — a walk-in gets exactly one final pass extension.
    extension_granted = models.BooleanField(default=False)
    early_terminated = models.BooleanField(default=False)
    terminated_by_user_id = models.IntegerField(null=True, blank=True)
    termination_reason = models.CharField(max_length=255, blank=True)
    invalidated_reason = models.CharField(max_length=255, blank=True)
    created_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "vms_visit"
        indexes = [
            models.Index(fields=["status", "checked_in_at"],
                         name="vms_visit_status_idx"),
            models.Index(fields=["visitor_id", "checked_in_at"],
                         name="vms_visit_visitor_idx"),
            models.Index(fields=["host_user_id", "status"],
                         name="vms_visit_host_idx"),
        ]

    def __str__(self) -> str:
        return f"visit#{self.id}:{self.status}"


class Pass(TimeStampedModel):
    TYPES = [("PRE_REGISTERED", "Pre-registered"), ("WALK_IN", "Walk-in"),
             ("VIP", "VIP"), ("EVENT", "Event")]
    STATUS = [("ACTIVE", "Active"), ("DEACTIVATED", "Deactivated"),
              ("EXPIRED", "Expired")]

    visit_id = models.IntegerField(db_index=True)
    visitor_id = models.IntegerField(db_index=True)
    pass_type = models.CharField(max_length=16, choices=TYPES,
                                 default="PRE_REGISTERED")
    #: QR payload. Empty for anonymous visitors (VMS-BR-013).
    pass_code = models.CharField(max_length=64, unique=True)
    otp = models.CharField(max_length=6, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="ACTIVE",
                              db_index=True)
    valid_from = models.DateTimeField()
    #: Null means "real-time, until checkout" (VMS-BR-016, zero-clock).
    valid_until = models.DateTimeField(null=True, blank=True)
    permitted_zones = models.JSONField(default=list, blank=True)
    issued_by_user_id = models.IntegerField(null=True, blank=True)
    #: Event fast-lane child passes hang off a parent (VMS-BR-039).
    parent_pass_id = models.IntegerField(null=True, blank=True, db_index=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    deactivation_reason = models.CharField(max_length=255, blank=True)
    #: VMS-BR-035 — safe-listed entry is reviewed by security at issue time.
    reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    is_event_fast_lane = models.BooleanField(default=False)

    class Meta:
        db_table = "vms_pass"
        indexes = [
            models.Index(fields=["visitor_id", "valid_from"],
                         name="vms_pass_visitor_idx"),
            models.Index(fields=["status", "valid_until"],
                         name="vms_pass_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.pass_code}:{self.status}"


class VisitLog(TimeStampedModel):
    EVENTS = [
        ("CHECK_IN", "Check-in"), ("CHECK_OUT", "Check-out"),
        ("STAY_START", "Stay start"), ("STAY_END", "Stay end"),
        ("ZONE_ACCESS_ALLOWED", "Zone allowed"),
        ("ZONE_ACCESS_DENIED", "Zone denied"),
        ("AUTO_CHECKOUT", "Auto checkout"),
        ("EARLY_TERMINATION", "Early termination"),
        ("OFFLINE_ENTRY", "Offline gate entry"),
        ("VIOLATION", "Violation"), ("ALERT_OPENED", "Alert opened"),
        ("ALERT_CLOSED", "Alert closed"),
    ]

    visit_id = models.IntegerField(db_index=True)
    pass_id = models.IntegerField(null=True, blank=True)
    visitor_id = models.IntegerField(db_index=True)
    event_type = models.CharField(max_length=24, choices=EVENTS)
    zone_code = models.CharField(max_length=32, blank=True)
    gate_code = models.CharField(max_length=32, blank=True)
    machine_id = models.CharField(max_length=64, blank=True)
    occurred_at = models.DateTimeField(db_index=True)
    recorded_by_user_id = models.IntegerField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    #: VMS-CFR-025 — cached while offline, reconciled later.
    offline_cached = models.BooleanField(default=False)
    synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "vms_visit_log"
        indexes = [
            models.Index(fields=["visit_id", "event_type"],
                         name="vms_log_visit_event_idx"),
            models.Index(fields=["event_type", "occurred_at"],
                         name="vms_log_event_time_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.event_type}:{self.visit_id}"


class VmsNotification(TimeStampedModel):
    KINDS = [
        ("VISIT_REQUEST", "Visit request"), ("HOST_DECISION", "Host decision"),
        ("PASS_ISSUED", "Pass issued"), ("CHECK_IN", "Check-in"),
        ("CHECK_OUT", "Check-out"), ("APPROVAL_TIMEOUT", "Approval timeout"),
        ("MUSTER_ALERT", "Muster alert"),
        ("ZONE_VIOLATION", "Zone violation"),
        ("BLACKLIST_HIT", "Blacklist hit"), ("EVENT_LEAD", "Event lead"),
    ]
    CHANNELS = [("PUSH", "Push"), ("EMAIL", "Email"), ("SMS", "SMS"),
                ("IN_APP", "In-app"), ("CALL", "Call")]
    RECIPIENTS = [("HOST", "Host"), ("VISITOR", "Visitor"),
                  ("SECURITY", "Security"), ("ADMIN", "Admin")]
    STATUS = [("PENDING", "Pending"), ("SENT", "Sent"),
              ("SUPPRESSED", "Suppressed"), ("FAILED", "Failed")]

    kind = models.CharField(max_length=20, choices=KINDS)
    channel = models.CharField(max_length=8, choices=CHANNELS)
    recipient_type = models.CharField(max_length=8, choices=RECIPIENTS)
    recipient_contact = models.CharField(max_length=255, blank=True)
    subject = models.CharField(max_length=255, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="PENDING")
    suppressed_reason = models.CharField(max_length=64, blank=True)
    related_visit_request_id = models.IntegerField(null=True, blank=True)
    related_visit_id = models.IntegerField(null=True, blank=True)
    related_pass_id = models.IntegerField(null=True, blank=True)
    #: VMS-BR-007 — the ORIGINAL request id, preserved across resends.
    request_id = models.CharField(max_length=64, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "vms_notification"
        indexes = [
            models.Index(fields=["kind", "status"],
                         name="vms_notification_kind_idx"),
            models.Index(fields=["request_id"],
                         name="vms_notification_request_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.kind}/{self.channel}:{self.status}"


VisitPass = Pass

