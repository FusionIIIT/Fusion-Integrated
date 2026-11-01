from django.db import models
from django.utils import timezone


class UserAccount(models.Model):
    """Basic user account representation in Super Admin (BR-SA-001, BR-SA-002, ADR-0013)."""

    user_id = models.IntegerField(unique=True, db_index=True)
    institute_id = models.CharField(max_length=50, unique=True, db_index=True)
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    user_type = models.CharField(
        max_length=20,
        choices=[("STUDENT", "Student"), ("FACULTY", "Faculty"), ("STAFF", "Staff")],
        default="STUDENT",
    )
    status = models.CharField(
        max_length=30,
        choices=[
            ("ACTIVE", "Active"),
            ("DEACTIVATED", "Deactivated"),
            ("ARCHIVED_REVERSIBLE", "Archived (Reversible)"),
            ("ARCHIVED_PERMANENT", "Archived (Permanently Non-Restorable)"),
        ],
        default="ACTIVE",
        db_index=True,
    )
    deactivated_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    reversible_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "superadmin_user_account"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.institute_id} ({self.status})"


class RoleAssignment(models.Model):
    """Operational role assignments for users (BR-SA-006, BR-SA-007, BR-SA-008)."""

    user_id = models.IntegerField(db_index=True)
    role_code = models.CharField(max_length=100, db_index=True)
    role_name = models.CharField(max_length=150)
    scope = models.CharField(max_length=100, default="INSTITUTE")
    is_singular = models.BooleanField(default=False)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[("ACTIVE", "Active"), ("REVOKED", "Revoked"), ("EXPIRED", "Expired")],
        default="ACTIVE",
    )
    revocation_reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "superadmin_role_assignment"

    def __str__(self) -> str:
        return f"{self.role_code} -> {self.user_id} ({self.status})"


class AuditEntry(models.Model):
    """Immutable audit trail for administrative actions (BR-SA-025, BR-SA-033)."""

    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    actor_username = models.CharField(max_length=150, db_index=True)
    action = models.CharField(max_length=100, db_index=True)
    target_id = models.CharField(max_length=100, blank=True, default="")
    result = models.CharField(max_length=20, default="SUCCESS")
    reason = models.TextField(blank=True, default="")

    class Meta:
        db_table = "superadmin_audit_entry"
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"[{self.actor_username}] {self.action} on {self.target_id}"
