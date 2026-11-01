"""Database models for System Admin (Super Admin) module.

Following Fusion platform architectural guidelines:
- Inherits TimeStampedModel for created_at / updated_at
- No foreign key crosses a module boundary; user_id is plain integer
- AuditLog is immutable and permanently retained
- CheckConstraints enforce data domain invariants
"""
from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.db.mixins import TimeStampedModel


class BasicUser(TimeStampedModel):
    """Basic User account (Student, Faculty, Staff).

    The internal user record managed by System Admin (CFR-SA-001, AFR-SA-001..013).
    Institute ID is immutable once created (BR-SA-001).
    """
    USER_TYPE_CHOICES = [
        ("student", "Student"),
        ("faculty", "Faculty"),
        ("staff", "Staff"),
    ]
    STATUS_CHOICES = [
        ("active", "Active"),
        ("deactivated", "Deactivated"),
        ("archived", "Archived"),
    ]

    user_id = models.AutoField(primary_key=True)
    institute_id = models.CharField(max_length=32, unique=True, db_index=True)
    user_type = models.CharField(max_length=16, choices=USER_TYPE_CHOICES, db_index=True)
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)
    contact_number = models.CharField(max_length=20, blank=True)

    # Department and academic attributes
    department = models.CharField(max_length=80, blank=True, db_index=True)
    programme = models.CharField(max_length=40, blank=True)
    discipline = models.CharField(max_length=40, blank=True, db_index=True)
    batch_year = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)
    employee_id = models.CharField(max_length=32, blank=True, db_index=True)
    date_of_joining = models.DateField(null=True, blank=True)
    expected_completion_date = models.DateField(null=True, blank=True)

    # Lifecycle state
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="active", db_index=True)
    dashboard_access_enabled = models.BooleanField(default=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    deactivation_reason = models.TextField(blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    archival_reason = models.TextField(blank=True)
    reversible_until = models.DateTimeField(null=True, blank=True)
    is_permanently_archived = models.BooleanField(default=False)
    has_pending_transactions = models.BooleanField(default=False)

    class Meta:
        db_table = "system_admin_basic_user"
        indexes = [
            models.Index(fields=["status", "user_type"], name="sa_user_status_type_idx"),
            models.Index(fields=["department", "status"], name="sa_user_dept_status_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=["active", "deactivated", "archived"]),
                name="sa_user_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} ({self.institute_id})"


class RoleDefinition(TimeStampedModel):
    """System-maintained, non-editable role definitions and metadata (CFR-SA-005, AFR-SA-021)."""

    code = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    module_association = models.CharField(max_length=64, db_index=True)
    department_association = models.CharField(max_length=80, blank=True)
    allowed_user_types = models.JSONField(default=list)  # ["student"], ["faculty", "staff"]
    is_singular = models.BooleanField(default=False)    # at most 1 active holder for same scope
    default_validity_days = models.PositiveIntegerField(null=True, blank=True)
    permissions = models.JSONField(default=list)
    conflict_role_codes = models.JSONField(default=list)
    is_system_role = models.BooleanField(default=False)

    class Meta:
        db_table = "system_admin_role_definition"
        ordering = ["module_association", "name"]

    def __str__(self) -> str:
        return f"{self.name} [{self.code}]"


class RoleAssignment(TimeStampedModel):
    """Additional role assigned to a basic user (CFR-SA-006..009).

    user_id is an integer, never a foreign key across module boundary.
    """
    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("active", "Active"),
        ("expired", "Expired"),
        ("revoked", "Revoked"),
        ("reassigned", "Reassigned"),
    ]
    DISPOSITION_CHOICES = [
        ("transfer", "Transfer"),
        ("close", "Close"),
    ]

    user_id = models.IntegerField(db_index=True)
    role = models.ForeignKey(RoleDefinition, on_delete=models.PROTECT, related_name="assignments")
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(null=True, blank=True, db_index=True)
    scope_type = models.CharField(max_length=32, default="institute")
    scope_id = models.CharField(max_length=64, blank=True)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="scheduled", db_index=True)

    assigned_by_user_id = models.IntegerField()
    assigned_at = models.DateTimeField(auto_now_add=True)
    effective_revoked_at = models.DateTimeField(null=True, blank=True)
    revocation_reason = models.TextField(blank=True)
    pending_task_disposition = models.CharField(max_length=16, choices=DISPOSITION_CHOICES, blank=True)
    previous_assignment = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="reassigned_to"
    )
    previous_holder_audit_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "system_admin_role_assignment"
        indexes = [
            models.Index(fields=["user_id", "status"], name="sa_role_assign_user_st_idx"),
            models.Index(fields=["role", "scope_type", "scope_id", "status"], name="sa_role_assign_scope_st_idx"),
            models.Index(fields=["status", "end_date"], name="sa_role_assign_end_date_idx"),
        ]

    def __str__(self) -> str:
        return f"User {self.user_id} -> {self.role.code} ({self.status})"


class ArchivedRecord(TimeStampedModel):
    """Archived historical system data or user package (CFR-SA-011..016)."""
    STATUS_CHOICES = [
        ("archived", "Archived"),
        ("restored", "Restored"),
        ("purge_requested", "Purge Requested"),
        ("purged", "Permanently Purged"),
    ]

    category = models.CharField(max_length=64, db_index=True)
    identifier = models.CharField(max_length=128, db_index=True)
    data_payload = models.JSONField(default=dict)
    retention_until = models.DateField(db_index=True)
    backup_reference = models.CharField(max_length=256)
    archived_at = models.DateTimeField(auto_now_add=True)
    archived_by_user_id = models.IntegerField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="archived", db_index=True)

    class Meta:
        db_table = "system_admin_archived_record"
        indexes = [
            models.Index(fields=["category", "retention_until"], name="sa_archive_cat_ret_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.category}:{self.identifier} (until {self.retention_until})"


class PurgeRequest(TimeStampedModel):
    """Permanent purge request requiring dual authorization (CFR-SA-016, BR-SA-021, BR-SA-022)."""
    STATUS_CHOICES = [
        ("pending_it_head", "Pending IT Head"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    archived_record = models.ForeignKey(ArchivedRecord, on_delete=models.CASCADE, related_name="purge_requests")
    requested_by_user_id = models.IntegerField()
    requested_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending_it_head", db_index=True)
    it_head_user_id = models.IntegerField(null=True, blank=True)
    authorized_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        db_table = "system_admin_purge_request"

    def __str__(self) -> str:
        return f"PurgeReq #{self.id} for Archive {self.archived_record_id} ({self.status})"


class AuditLog(models.Model):
    """Immutable audit trail for all Super Admin operations (BR-SA-025, BR-SA-033, CFR-SA-017).

    Logs cannot be edited or deleted.
    """
    RESULT_CHOICES = [
        ("success", "Success"),
        ("failure", "Failure"),
    ]

    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    actor_user_id = models.IntegerField(db_index=True)
    actor_username = models.CharField(max_length=64)
    action = models.CharField(max_length=80, db_index=True)
    target_type = models.CharField(max_length=64, blank=True)
    target_id = models.CharField(max_length=64, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    result = models.CharField(max_length=16, choices=RESULT_CHOICES, default="success", db_index=True)
    reason = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "system_admin_audit_log"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["action", "-timestamp"], name="sa_audit_action_ts_idx"),
            models.Index(fields=["actor_user_id", "-timestamp"], name="sa_audit_actor_ts_idx"),
        ]

    def save(self, *args, **kwargs):
        # Enforce immutability on update
        if self.pk:
            raise RuntimeError("AuditLog records are immutable and cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("AuditLog records are permanently retained and cannot be deleted.")

    def __str__(self) -> str:
        return f"{self.timestamp} | {self.actor_username} | {self.action} | {self.result}"


class SuperAdminSession(models.Model):
    """Active Super Admin sessions for single-session and timeout enforcement (BR-SA-027)."""

    user_id = models.IntegerField(db_index=True)
    session_key = models.CharField(max_length=128, unique=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=256, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "system_admin_session"

    def __str__(self) -> str:
        return f"Session {self.session_key} (User {self.user_id})"


class FailedLoginAttempt(models.Model):
    """Tracks failed Super Admin login attempts to trigger 5-attempt security alerts (BR-SA-024)."""

    username = models.CharField(max_length=64, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    attempted_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "system_admin_failed_login"
        ordering = ["-attempted_at"]

    def __str__(self) -> str:
        return f"Failed login for {self.username} at {self.attempted_at}"


class SystemConfiguration(models.Model):
    """Configurable system-wide administrative parameters (BR-SA-035, CFR-SA-023)."""

    key = models.CharField(max_length=64, primary_key=True)
    value = models.JSONField()
    description = models.CharField(max_length=256, blank=True)
    updated_by_user_id = models.IntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "system_admin_configuration"

    def __str__(self) -> str:
        return f"{self.key}: {self.value}"


class BulkOperationLog(TimeStampedModel):
    """Detailed summary and log for bulk user operations (CFR-SA-004, AFR-SA-019A/B)."""

    batch_id = models.CharField(max_length=64, unique=True, db_index=True)
    operation_type = models.CharField(max_length=32)
    total_records = models.PositiveIntegerField()
    successful_records = models.PositiveIntegerField(default=0)
    failed_records = models.PositiveIntegerField(default=0)
    initiated_by_user_id = models.IntegerField()
    summary = models.JSONField(default=dict)
    detailed_log = models.JSONField(default=list)

    class Meta:
        db_table = "system_admin_bulk_operation_log"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"BulkOp {self.batch_id} ({self.operation_type}: {self.successful_records}/{self.total_records})"
