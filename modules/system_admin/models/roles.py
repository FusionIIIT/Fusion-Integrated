"""Role definitions, role assignments, lifecycle history, and reassignment handovers."""
from typing import Set
from django.db import models

from core.db.mixins import TimeStampedModel
from modules.system_admin.constants import (
    PendingTaskDisposition,
    RoleCategory,
    RoleAssignmentState,
    RoleRevocationType,
)
from modules.system_admin.models.users import BasicUser


class RoleDefinition(TimeStampedModel):
    """The catalog of assignable roles. Read-only to Super Admin (BR-SA-035)."""

    code = models.CharField(max_length=64, unique=True, primary_key=True)
    label = models.CharField(max_length=120)
    category = models.CharField(max_length=16, choices=RoleCategory.choices)
    allowed_kinds = models.CharField(
        max_length=64,
        help_text="Comma-separated UserKinds: student,faculty,staff",
    )
    is_singular = models.BooleanField(default=False)
    is_time_bound = models.BooleanField(default=False)
    default_lead_time_days = models.PositiveSmallIntegerField(default=7)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    compatibility_rules = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "system_admin_role_definition"

    def get_allowed_kinds_set(self) -> Set[str]:
        if not self.allowed_kinds:
            return set()
        return {k.strip() for k in self.allowed_kinds.split(",") if k.strip()}

    def is_eligible_kind(self, kind: str) -> bool:
        return kind in self.get_allowed_kinds_set()

    def __str__(self):
        return f"{self.label} ({self.code})"


class RoleAssignment(TimeStampedModel):
    """Active and historical role grants to basic users."""

    user = models.ForeignKey(
        BasicUser,
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )
    role = models.ForeignKey(
        RoleDefinition,
        on_delete=models.PROTECT,
        related_name="assignments",
    )
    scope = models.CharField(max_length=64, default="institute", db_index=True)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(null=True, blank=True, db_index=True)
    state = models.CharField(
        max_length=16,
        choices=RoleAssignmentState.choices,
        default=RoleAssignmentState.SCHEDULED,
        db_index=True,
    )
    assigned_by = models.IntegerField(help_text="Super Admin user_id")
    reason = models.TextField(blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    expired_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revocation_reason = models.TextField(blank=True)
    revocation_type = models.CharField(
        max_length=16,
        choices=RoleRevocationType.choices,
        blank=True,
    )
    notice_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "system_admin_role_assignment"
        indexes = [
            models.Index(fields=["role", "scope", "state"]),
            models.Index(fields=["user", "state"]),
            models.Index(fields=["state", "start_date"]),
            models.Index(fields=["state", "end_date"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__isnull=True) | models.Q(end_date__gt=models.F("start_date")),
                name="check_role_dates_valid",
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.role_id} ({self.state})"


class RoleAssignmentHistory(TimeStampedModel):
    """Permanent historical record of role modifications (AFR-SA-031, AFR-SA-081D)."""

    assignment = models.ForeignKey(
        RoleAssignment,
        on_delete=models.CASCADE,
        related_name="history",
    )
    action = models.CharField(max_length=32)
    from_state = models.CharField(max_length=16)
    to_state = models.CharField(max_length=16)
    performed_by = models.IntegerField()
    effective_date = models.DateField()
    reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "system_admin_role_history"

    def __str__(self):
        return f"{self.assignment_id} - {self.action} ({self.from_state} -> {self.to_state})"


class RoleHandoverLog(TimeStampedModel):
    """Tracks work transfer and audit access during role reassignment (BR-SA-012, BR-SA-013)."""

    role = models.ForeignKey(RoleDefinition, on_delete=models.PROTECT)
    previous_holder_id = models.IntegerField(db_index=True)
    new_holder_id = models.IntegerField(db_index=True)
    scope = models.CharField(max_length=64)
    effective_date = models.DateField()
    pending_tasks_count = models.PositiveIntegerField(default=0)
    tasks_disposition = models.CharField(
        max_length=16,
        choices=PendingTaskDisposition.choices,
    )
    audit_access_expires_at = models.DateField(help_text="BR-SA-013: Read-only access cutoff")
    reassigned_by = models.IntegerField()

    class Meta:
        db_table = "system_admin_role_handover_log"

    def __str__(self):
        return f"Handover: {self.role_id} from {self.previous_holder_id} to {self.new_holder_id}"
