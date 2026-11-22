from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class VisitorProfile(TimeStampedModel):
    display_name = models.CharField(max_length=160)
    email = models.EmailField(max_length=254, db_index=True)
    phone = models.CharField(max_length=32, blank=True)
    id_type = models.CharField(max_length=32)
    id_fingerprint = models.CharField(max_length=64, db_index=True)
    id_last_four = models.CharField(max_length=4, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "vms_visitor_profile"
        constraints = [
            models.UniqueConstraint(
                fields=["email", "id_fingerprint"], name="vms_visitor_identity_uq"
            ),
        ]
        indexes = [models.Index(fields=["email", "is_active"], name="vms_visit_email_idx")]


class VisitorDocument(models.Model):
    """Private identity evidence; the file itself lives in VMS-owned storage."""

    SCAN_STATUS = [
        ("pending", "Pending"),
        ("clean", "Clean"),
        ("infected", "Infected"),
        ("failed", "Failed"),
    ]
    request = models.ForeignKey(
        "vms.VisitRequest", on_delete=models.PROTECT, related_name="identity_documents"
    )
    visitor = models.ForeignKey(
        VisitorProfile, on_delete=models.PROTECT, related_name="identity_documents"
    )
    document_type = models.CharField(max_length=32)
    storage_key = models.CharField(max_length=80, unique=True)
    filename = models.CharField(max_length=160)
    content_type = models.CharField(max_length=80)
    size_bytes = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)
    scan_status = models.CharField(
        max_length=12, choices=SCAN_STATUS, default="pending", db_index=True
    )
    scan_detail = models.CharField(max_length=160, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    scanned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "vms_visitor_document"
        indexes = [models.Index(fields=["request", "scan_status"], name="vms_doc_request_idx")]

    def __str__(self):
        return f"Visitor document {self.pk} ({self.scan_status})"


class VisitorAccessCredential(TimeStampedModel):
    visitor = models.ForeignKey(
        VisitorProfile, on_delete=models.CASCADE, related_name="access_credentials"
    )
    nonce = models.UUIDField(unique=True)
    expires_at = models.DateTimeField(db_index=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    purpose = models.CharField(max_length=24, default="visitor_portal")

    class Meta:
        db_table = "vms_visitor_access_credential"
        indexes = [models.Index(fields=["visitor", "expires_at"], name="vms_cred_exp_idx")]


class VisitRequest(TimeStampedModel):
    STATUS = [
        ("pending", "Pending host approval"),
        ("pending_admin_contingency", "Pending Admin contingency"),
        ("pending_urgent_review", "Pending urgent review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("expired", "Expired"),
        ("cancelled", "Cancelled"),
        ("on_site", "On site"),
        ("completed", "Completed"),
        ("terminated", "Terminated"),
    ]
    KIND = [("pre_registered", "Pre-registered"), ("walk_in", "Walk-in"), ("event", "Event")]

    visitor = models.ForeignKey(
        VisitorProfile, on_delete=models.PROTECT, related_name="visit_requests"
    )
    host_user_id = models.IntegerField(db_index=True)
    kind = models.CharField(max_length=20, choices=KIND, default="pre_registered")
    status = models.CharField(max_length=32, choices=STATUS, default="pending", db_index=True)
    purpose = models.CharField(max_length=500)
    starts_at = models.DateTimeField(db_index=True)
    ends_at = models.DateTimeField(db_index=True)
    requested_zones = models.JSONField(default=list, blank=True)
    approved_zones = models.JSONField(default=list, blank=True)
    special_instructions = models.CharField(max_length=500, blank=True)
    decision_reason = models.CharField(max_length=500, blank=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    approval_due_at = models.DateTimeField(null=True, blank=True, db_index=True)
    policy_version = models.ForeignKey(
        "vms.AccessPolicyVersion",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="visit_requests",
    )
    event = models.ForeignKey(
        "vms.EventRecord",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="visit_requests",
    )

    class Meta:
        db_table = "vms_visit_request"
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__gt=models.F("starts_at")), name="vms_visit_window_valid"
            ),
        ]
        indexes = [
            models.Index(
                fields=["host_user_id", "status", "-created_at"], name="vms_host_pending_idx"
            ),
            models.Index(fields=["status", "approval_due_at"], name="vms_expiry_due_idx"),
            models.Index(fields=["visitor", "-created_at"], name="vms_vis_hist_idx"),
        ]


class VisitTransition(models.Model):
    request = models.ForeignKey(VisitRequest, on_delete=models.PROTECT, related_name="transitions")
    from_status = models.CharField(max_length=32)
    to_status = models.CharField(max_length=32)
    event = models.CharField(max_length=32)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_kind = models.CharField(max_length=24)
    reason = models.CharField(max_length=500, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vms_visit_transition"
        indexes = [models.Index(fields=["request", "at"], name="vms_trans_req_idx")]

    def __str__(self):
        return f"Visit {self.request_id}: {self.from_status} to {self.to_status}"


class VisitPass(TimeStampedModel):
    TYPE = [("pre_registered", "Pre-registered"), ("walk_in", "Walk-in"), ("vip", "VIP")]
    STATUS = [
        ("active", "Active"),
        ("revoked", "Revoked"),
        ("expired", "Expired"),
        ("used", "Used"),
    ]

    request = models.OneToOneField(
        VisitRequest, on_delete=models.PROTECT, related_name="visit_pass"
    )
    pass_type = models.CharField(max_length=20, choices=TYPE)
    status = models.CharField(max_length=12, choices=STATUS, default="active", db_index=True)
    credential_nonce = models.UUIDField(unique=True)
    valid_from = models.DateTimeField(db_index=True)
    valid_until = models.DateTimeField(db_index=True)
    permitted_zones = models.JSONField(default=list, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by_user_id = models.IntegerField(null=True, blank=True)
    revocation_reason = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "vms_visit_pass"
        constraints = [
            models.CheckConstraint(
                condition=Q(valid_until__gt=models.F("valid_from")), name="vms_pass_window_valid"
            ),
        ]
        indexes = [
            models.Index(fields=["status", "valid_until"], name="vms_pass_expiry_idx"),
            models.Index(fields=["pass_type", "status"], name="vms_pass_type_idx"),
        ]


class VisitLog(models.Model):
    EVENT = [
        ("entry", "Entry"),
        ("exit", "Exit"),
        ("zone_granted", "Zone granted"),
        ("zone_denied", "Zone denied"),
        ("gate_denied", "Gate denied"),
        ("offline_entry", "Offline entry"),
        ("override", "Manual override"),
    ]
    request = models.ForeignKey(VisitRequest, on_delete=models.PROTECT, related_name="visit_logs")
    event_type = models.CharField(max_length=20, choices=EVENT)
    occurred_at = models.DateTimeField(db_index=True)
    location = models.CharField(max_length=160, blank=True)
    zone = models.CharField(max_length=80, blank=True)
    recorded_by_user_id = models.IntegerField(null=True, blank=True)
    source = models.CharField(max_length=20, default="online")
    reason = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "vms_visit_log"
        indexes = [
            models.Index(fields=["request", "occurred_at"], name="vms_visit_log_idx"),
            models.Index(fields=["event_type", "occurred_at"], name="vms_log_event_idx"),
        ]

    def __str__(self):
        return f"Visit {self.request_id}: {self.event_type}"


class AuditEvent(models.Model):
    actor_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    actor_kind = models.CharField(max_length=24)
    action = models.CharField(max_length=80, db_index=True)
    object_type = models.CharField(max_length=64)
    object_id = models.CharField(max_length=64)
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)
    request_id = models.CharField(max_length=64, blank=True)
    reason = models.CharField(max_length=500, blank=True)
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "vms_audit_event"
        indexes = [
            models.Index(
                fields=["object_type", "object_id", "-occurred_at"], name="vms_audit_object_idx"
            ),
            models.Index(fields=["action", "-occurred_at"], name="vms_audit_action_idx"),
        ]

    def __str__(self):
        return f"{self.action}: {self.object_type} {self.object_id}"


class NotificationOutbox(models.Model):
    STATUS = [
        ("pending", "Pending"),
        ("sending", "Sending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
        ("suppressed", "Suppressed"),
    ]
    topic = models.CharField(max_length=60, db_index=True)
    dedupe_key = models.CharField(max_length=200, unique=True)
    recipient_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    recipient_email = models.EmailField(blank=True)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="pending", db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_error = models.CharField(max_length=300, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vms_notification_outbox"
        indexes = [models.Index(fields=["status", "created_at"], name="vms_outbox_pending_idx")]

    def __str__(self):
        return f"{self.topic} notification ({self.status})"
