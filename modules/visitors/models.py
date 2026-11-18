"""VMS tables.

Visitors, hosts, and security personnel are plain `user_id` integers — this
database has no user table, so a cross-boundary reference stays unconstrained.

Ref: 01_VMS_Problem_Statement_v1.2, 03_VMS_Use_Case_Specifications_v1.3
"""
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel

# --- value-domain choices (BR-VMS-187, BR-VMS-211) --------------------------

ID_DOCUMENT_TYPES = [
    ("AADHAAR", "Aadhaar Card"),
    ("PAN", "PAN Card"),
    ("PASSPORT", "Passport"),
    ("DRIVING", "Driving License"),
    ("VOTER", "Voter ID"),
    ("INSTITUTE", "Institute ID"),
]

PASS_TYPES = [
    ("PRE_REGISTERED", "Pre-registered"),
    ("WALK_IN", "Walk-in"),
    ("PRE_AUTHORIZED", "Pre-authorized"),
    ("VIP", "VIP"),
    ("EVENT", "Event / Bulk"),
]

VISIT_STATUSES = [
    ("draft", "Draft"),
    ("pending_host", "Pending Host Approval"),
    ("pending_admin", "Pending Admin Approval"),
    ("approved", "Approved"),
    ("pass_active", "Pass Active"),
    ("on_site", "On Site"),
    ("checked_out", "Checked Out"),
    ("completed", "Completed"),
    ("rejected", "Rejected"),
    ("cancelled", "Cancelled"),
    ("expired", "Expired"),
    ("terminated", "Terminated"),
]

VISIT_REQUEST_KINDS = [
    ("standard", "Standard Pre-registration"),
    ("walkin", "Walk-in Registration"),
    ("pre_authorized", "Pre-authorized Visit"),
    ("vip", "VIP Visit"),
    ("event", "Event / Bulk"),
    ("extension", "Visit Extension"),
    ("urgent", "Same-day Urgent"),
]

APPROVAL_ACTIONS = [
    ("approve", "Approve"),
    ("reject", "Reject"),
    ("contingency_approve", "Contingency Approve"),
]

ZONE_ACCESS_LEVELS = [
    ("general", "General / Public"),
    ("restricted", "Restricted"),
    ("high_security", "High Security"),
]

GATE_EVENT_TYPES = [
    ("check_in", "Check-in"),
    ("check_out", "Check-out"),
    ("zone_entry", "Zone Entry"),
    ("zone_exit", "Zone Exit"),
    ("denied", "Denied"),
    ("override", "Manual Override"),
]

MUSTER_STATUSES = [
    ("active", "Active"),
    ("roll_call", "Roll-call in Progress"),
    ("resolved", "Resolved"),
]

BLACKLIST_ENTRY_TYPES = [
    ("blacklist", "Blacklist"),
    ("watchlist", "Watchlist"),
]


# --- Access policy (BR-VMS-125 … BR-VMS-129) --------------------------------

class AccessPolicy(TimeStampedModel):
    """Versioned campus-wide visiting rules — only the published row is used
    at runtime (BR-VMS-126, BR-VMS-127)."""

    version = models.PositiveIntegerField()
    visiting_hours_start = models.TimeField()
    visiting_hours_end = models.TimeField()
    max_visit_duration_hours = models.PositiveIntegerField(default=8)
    default_walkin_duration_minutes = models.PositiveIntegerField(default=120)
    advance_registration_days = models.PositiveIntegerField(default=30)
    approval_timeout_hours = models.PositiveIntegerField(default=48)
    is_published = models.BooleanField(default=False)
    published_by = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "vms_access_policy"
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(fields=["version"],
                                    name="vms_policy_unique_version"),
        ]

    def __str__(self) -> str:
        return f"Policy v{self.version} ({'published' if self.is_published else 'draft'})"


# --- Blacklist / Watchlist / Safe-list (BR-VMS-051, BR-VMS-112 … 120) --------

class BlacklistEntry(TimeStampedModel):
    """A person barred or flagged for campus entry."""

    entry_type = models.CharField(max_length=12, choices=BLACKLIST_ENTRY_TYPES,
                                  default="blacklist")
    full_name = models.CharField(max_length=200)
    id_document_type = models.CharField(max_length=12, choices=ID_DOCUMENT_TYPES,
                                        blank=True)
    id_document_number = models.CharField(max_length=50, blank=True)
    reason = models.TextField(blank=True)
    added_by = models.IntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "vms_blacklist_entry"
        indexes = [
            models.Index(fields=["id_document_number"],
                         name="vms_blacklist_doc_idx"),
            models.Index(fields=["full_name"], name="vms_blacklist_name_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.entry_type}: {self.full_name}"


class SafeListEntry(TimeStampedModel):
    """Temporary safe-list override for a blacklisted person (BR-VMS-118, 119)."""

    blacklist_entry = models.ForeignKey(BlacklistEntry, on_delete=models.CASCADE,
                                        related_name="safe_list_overrides")
    reason = models.TextField()
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    granted_by = models.IntegerField()

    class Meta:
        db_table = "vms_safe_list_entry"

    def __str__(self) -> str:
        return f"Safe-list for {self.blacklist_entry} until {self.valid_until}"


# --- VIP permissions (VMS-UC-003, BR-VMS-196, BR-VMS-197) --------------------

class VIPPermission(TimeStampedModel):
    """A VIP override scope granted by Super Admin."""

    visitor_name = models.CharField(max_length=200)
    visitor_id_number = models.CharField(max_length=50, blank=True)
    scope_description = models.TextField()
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    bypass_host_approval = models.BooleanField(default=True)
    bypass_zone_restriction = models.BooleanField(default=False)
    granted_by = models.IntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "vms_vip_permission"

    def __str__(self) -> str:
        return f"VIP: {self.visitor_name} until {self.valid_until}"


# --- Pre-authorization (VMS-UC-014, BR-VMS-195) -----------------------------

class PreAuthorization(TimeStampedModel, UserScopedModel):
    """A host pre-authorizes a recurring visitor so approval is automatic."""

    visitor_name = models.CharField(max_length=200)
    visitor_phone = models.CharField(max_length=20, blank=True)
    visitor_email = models.EmailField(blank=True)
    visitor_id_type = models.CharField(max_length=12, choices=ID_DOCUMENT_TYPES,
                                       blank=True)
    visitor_id_number = models.CharField(max_length=50, blank=True)
    purpose = models.CharField(max_length=200)
    valid_from = models.DateField()
    valid_until = models.DateField()
    allowed_zones = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "vms_pre_authorization"

    def __str__(self) -> str:
        return f"Pre-auth: {self.visitor_name} by u{self.user_id}"


# --- Core visit record (CW-VMS-01, CW-VMS-02) -------------------------------

class VisitRequest(TimeStampedModel):
    """One visit lifecycle from registration through checkout/completion.

    Covers pre-registered (BW-VMS-01), walk-in (BW-VMS-06/07), pre-authorized
    (BW-VMS-04), VIP (BW-VMS-05), event/bulk (BW-VMS-21), same-day urgent
    (BW-VMS-22), and extension (BW-VMS-23) flows.
    """

    kind = models.CharField(max_length=16, choices=VISIT_REQUEST_KINDS,
                            default="standard")
    parent = models.ForeignKey("self", on_delete=models.PROTECT, null=True,
                               blank=True, related_name="extensions")
    status = models.CharField(max_length=16, choices=VISIT_STATUSES,
                              default="draft")

    # Visitor information (BR-VMS-037, BR-VMS-186)
    visitor_name = models.CharField(max_length=200)
    visitor_email = models.EmailField(blank=True)
    visitor_phone = models.CharField(max_length=20)
    visitor_organization = models.CharField(max_length=200, blank=True)
    visitor_id_type = models.CharField(max_length=12, choices=ID_DOCUMENT_TYPES)
    visitor_id_number = models.CharField(max_length=50)
    visitor_photo = models.TextField(blank=True)

    # Visit details
    host_user_id = models.IntegerField(db_index=True)
    purpose = models.CharField(max_length=500)
    expected_date = models.DateField()
    expected_time_from = models.TimeField(null=True, blank=True)
    expected_time_until = models.TimeField(null=True, blank=True)
    number_of_visitors = models.PositiveIntegerField(default=1)
    allowed_zones = models.JSONField(default=list, blank=True)

    # Pass information (BR-VMS-211, BR-VMS-077, BR-VMS-190)
    pass_type = models.CharField(max_length=16, choices=PASS_TYPES, blank=True)
    pass_code = models.CharField(max_length=40, unique=True, null=True, blank=True)
    pass_valid_from = models.DateTimeField(null=True, blank=True)
    pass_valid_until = models.DateTimeField(null=True, blank=True)

    # Check-in / check-out timestamps (BR-VMS-105)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_in_by = models.IntegerField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    checked_out_by = models.IntegerField(null=True, blank=True)

    # Approval tracking
    decided_by = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True)

    # Pre-authorization / VIP links
    pre_authorization = models.ForeignKey(PreAuthorization, on_delete=models.SET_NULL,
                                          null=True, blank=True)
    vip_permission = models.ForeignKey(VIPPermission, on_delete=models.SET_NULL,
                                       null=True, blank=True)

    # Registered by (visitor self-service vs security walk-in)
    registered_by = models.IntegerField(null=True, blank=True)

    # Event/bulk reference
    event_name = models.CharField(max_length=200, blank=True)
    bulk_upload_batch = models.CharField(max_length=40, blank=True)

    class Meta:
        db_table = "vms_visit_request"
        indexes = [
            models.Index(fields=["status", "expected_date"],
                         name="vms_visit_status_date_idx"),
            models.Index(fields=["host_user_id"], name="vms_visit_host_idx"),
            models.Index(fields=["visitor_id_number"],
                         name="vms_visit_visitor_doc_idx"),
            models.Index(fields=["pass_code"], name="vms_visit_pass_idx"),
        ]

    def __str__(self) -> str:
        return f"Visit #{self.pk} {self.visitor_name} → u{self.host_user_id}"


class VisitApproval(TimeStampedModel):
    """Audit row for every approval/rejection action on a visit request."""

    visit = models.ForeignKey(VisitRequest, on_delete=models.CASCADE,
                              related_name="approvals")
    action = models.CharField(max_length=24, choices=APPROVAL_ACTIONS)
    actor_user_id = models.IntegerField()
    actor_role = models.CharField(max_length=30)
    note = models.TextField(blank=True)

    class Meta:
        db_table = "vms_visit_approval"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action} by u{self.actor_user_id} on Visit #{self.visit_id}"


# --- Gate events (CW-VMS-03, BR-VMS-082) ------------------------------------

class GateLog(TimeStampedModel):
    """Every gate interaction: check-in, check-out, denial, override."""

    visit = models.ForeignKey(VisitRequest, on_delete=models.CASCADE,
                              related_name="gate_logs")
    event_type = models.CharField(max_length=12, choices=GATE_EVENT_TYPES)
    gate_name = models.CharField(max_length=60)
    recorded_by = models.IntegerField()
    is_offline = models.BooleanField(default=False)
    synced_at = models.DateTimeField(null=True, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        db_table = "vms_gate_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["visit", "event_type"],
                         name="vms_gate_visit_event_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} at {self.gate_name} for Visit #{self.visit_id}"


# --- Zone access (CW-VMS-04, BR-VMS-191 … 192) ------------------------------

class ZoneDefinition(TimeStampedModel):
    """A named campus zone with an access level."""

    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=120)
    access_level = models.CharField(max_length=16, choices=ZONE_ACCESS_LEVELS,
                                    default="general")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "vms_zone_definition"

    def __str__(self) -> str:
        return f"{self.code}: {self.name}"


class ZoneAccessLog(TimeStampedModel):
    """Zone entry/exit/denial record (BR-VMS-192)."""

    visit = models.ForeignKey(VisitRequest, on_delete=models.CASCADE,
                              related_name="zone_logs")
    zone = models.ForeignKey(ZoneDefinition, on_delete=models.PROTECT)
    action = models.CharField(max_length=10,
                              choices=[("entry", "Entry"), ("exit", "Exit"),
                                       ("denied", "Denied")])
    recorded_by = models.IntegerField()
    note = models.TextField(blank=True)

    class Meta:
        db_table = "vms_zone_access_log"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action} zone {self.zone.code} Visit #{self.visit_id}"


class TemporaryZoneElevation(TimeStampedModel):
    """One-time elevated zone access granted by Admin (BR-VMS-096)."""

    visit = models.ForeignKey(VisitRequest, on_delete=models.CASCADE,
                              related_name="zone_elevations")
    zone = models.ForeignKey(ZoneDefinition, on_delete=models.PROTECT)
    granted_by = models.IntegerField()
    valid_until = models.DateTimeField()
    used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "vms_temp_zone_elevation"

    def __str__(self) -> str:
        return f"Elevation: Visit #{self.visit_id} → {self.zone.code}"


# --- Emergency muster (CW-VMS-06, BR-VMS-130) --------------------------------

class EmergencyMuster(TimeStampedModel):
    """An emergency muster event triggered by Admin or Security."""

    triggered_by = models.IntegerField()
    trigger_role = models.CharField(max_length=30)
    reason = models.TextField()
    status = models.CharField(max_length=12, choices=MUSTER_STATUSES,
                              default="active")
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.IntegerField(null=True, blank=True)
    total_on_site = models.PositiveIntegerField(default=0)
    total_accounted = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "vms_emergency_muster"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Muster #{self.pk} ({self.status})"


class MusterRollCall(TimeStampedModel):
    """Per-visitor accounting during an emergency muster (VMS-UC-027)."""

    muster = models.ForeignKey(EmergencyMuster, on_delete=models.CASCADE,
                               related_name="roll_calls")
    visit = models.ForeignKey(VisitRequest, on_delete=models.CASCADE)
    accounted = models.BooleanField(default=False)
    accounted_by = models.IntegerField(null=True, blank=True)
    accounted_at = models.DateTimeField(null=True, blank=True)
    location_note = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = "vms_muster_roll_call"
        constraints = [
            models.UniqueConstraint(fields=["muster", "visit"],
                                    name="vms_muster_visit_unique"),
        ]

    def __str__(self) -> str:
        return f"Roll-call Muster #{self.muster_id} Visit #{self.visit_id}"


# --- VMS role assignment (VMS-UC-001, BR-VMS-181 … 184) ----------------------

class VMSRoleAssignment(TimeStampedModel):
    """Time-bound VMS-specific role assignment for a user."""

    user_id = models.IntegerField(db_index=True)
    role = models.CharField(max_length=30)
    scope_zone = models.ForeignKey(ZoneDefinition, on_delete=models.SET_NULL,
                                   null=True, blank=True)
    scope_gate = models.CharField(max_length=60, blank=True)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField(null=True, blank=True)
    assigned_by = models.IntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "vms_role_assignment"
        indexes = [
            models.Index(fields=["user_id", "role"],
                         name="vms_role_user_role_idx"),
        ]

    def __str__(self) -> str:
        return f"u{self.user_id} = {self.role}"


# --- Notification log (BR-VMS-174) -------------------------------------------

class NotificationLog(TimeStampedModel):
    """Record of every VMS notification event sent."""

    visit = models.ForeignKey(VisitRequest, on_delete=models.CASCADE,
                              related_name="notifications", null=True, blank=True)
    recipient_user_id = models.IntegerField(null=True, blank=True)
    recipient_contact = models.CharField(max_length=200, blank=True)
    channel = models.CharField(max_length=16,
                               choices=[("email", "Email"), ("sms", "SMS"),
                                        ("push", "Push"), ("in_app", "In-App")])
    event_type = models.CharField(max_length=60)
    message_summary = models.TextField(blank=True)
    sent = models.BooleanField(default=False)

    class Meta:
        db_table = "vms_notification_log"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.event_type} → {self.recipient_contact or self.recipient_user_id}"
