"""Role Management Models for System Admin Control Plane."""
from django.db import models
from core.db.mixins import TimeStampedModel
from modules.systemadmin.models.user_mgmt import BasicUserProfile


class RoleDefinition(TimeStampedModel):
    STATUS_CHOICES = [
        ("available", "Available"),
        ("deprecated", "Deprecated"),
    ]

    code = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    module_or_dept = models.CharField(max_length=100)
    allowed_user_types = models.JSONField(default=list)  # e.g. ["faculty", "staff"]
    is_singular = models.BooleanField(default=False)
    default_validity_days = models.PositiveIntegerField(null=True, blank=True)
    is_time_bound = models.BooleanField(default=True)
    permissions = models.JSONField(default=list)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="available")

    class Meta:
        db_table = "systemadmin_role_definition"
        ordering = ["module_or_dept", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class RoleConflict(TimeStampedModel):
    role_a = models.ForeignKey(
        RoleDefinition,
        on_delete=models.CASCADE,
        related_name="conflicts_with_a"
    )
    role_b = models.ForeignKey(
        RoleDefinition,
        on_delete=models.CASCADE,
        related_name="conflicts_with_b"
    )
    reason = models.CharField(max_length=255)

    class Meta:
        db_table = "systemadmin_role_conflict"
        unique_together = ("role_a", "role_b")

    def __str__(self) -> str:
        return f"Conflict: {self.role_a.code} <-> {self.role_b.code} ({self.reason})"


class RoleAssignment(TimeStampedModel):
    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("active", "Active"),
        ("extended", "Extended"),
        ("expired", "Expired"),
        ("reassigned", "Reassigned"),
        ("revoked", "Revoked"),
    ]

    role = models.ForeignKey(
        RoleDefinition,
        on_delete=models.CASCADE,
        related_name="assignments"
    )
    user = models.ForeignKey(
        BasicUserProfile,
        on_delete=models.CASCADE,
        related_name="role_assignments"
    )
    scope = models.CharField(max_length=100, blank=True)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(null=True, blank=True, db_index=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="active", db_index=True)
    assignment_reason = models.TextField()
    assigned_by = models.CharField(max_length=64)

    extended_at = models.DateTimeField(null=True, blank=True)
    extension_reason = models.TextField(blank=True)

    revoked_at = models.DateTimeField(null=True, blank=True)
    revocation_reason = models.TextField(blank=True)
    revocation_task_disposition = models.CharField(max_length=20, blank=True)  # transfer or close

    reassigned_to_user = models.ForeignKey(
        BasicUserProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reassigned_from_roles"
    )
    reassignment_effective_date = models.DateField(null=True, blank=True)
    previous_holder_audit_until = models.DateField(null=True, blank=True)
    reminder_sent = models.BooleanField(default=False)

    class Meta:
        db_table = "systemadmin_role_assignment"
        ordering = ["-start_date", "role__name"]
        indexes = [
            models.Index(fields=["status", "start_date"], name="sa_role_status_start_idx"),
            models.Index(fields=["status", "end_date"], name="sa_role_status_end_idx"),
            models.Index(fields=["user", "status"], name="sa_role_user_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user.institute_id} as {self.role.name} ({self.status})"


class RoleAssignmentHistory(TimeStampedModel):
    assignment = models.ForeignKey(
        RoleAssignment,
        on_delete=models.CASCADE,
        related_name="history"
    )
    action = models.CharField(max_length=32, db_index=True)
    actor_username = models.CharField(max_length=64)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    details = models.JSONField(default=dict)

    class Meta:
        db_table = "systemadmin_role_assignment_history"
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"{self.assignment.id} - {self.action} at {self.timestamp}"
