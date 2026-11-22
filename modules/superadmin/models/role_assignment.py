"""Role assignment and handover models."""

from django.db import models

from core.db.mixins import TimeStampedModel


class RoleAssignmentStatus(models.TextChoices):
    SCHEDULED = "SCHEDULED", "Scheduled"
    ACTIVE = "ACTIVE", "Active"
    EXTENDED = "EXTENDED", "Extended"
    EXPIRED = "EXPIRED", "Expired"
    REVOKED = "REVOKED", "Revoked"
    REASSIGNED = "REASSIGNED", "Reassigned"


class RoleAssignmentRecord(TimeStampedModel):
    user_id = models.IntegerField(db_index=True)
    role_name = models.CharField(max_length=128, db_index=True)
    scope_type = models.CharField(max_length=64, blank=True, default="")
    scope_id = models.CharField(max_length=64, blank=True, default="")
    valid_from = models.DateTimeField(db_index=True)
    valid_to = models.DateTimeField(null=True, blank=True, db_index=True)
    status = models.CharField(
        max_length=32,
        choices=RoleAssignmentStatus.choices,
        default=RoleAssignmentStatus.SCHEDULED,
        db_index=True,
    )
    is_singular = models.BooleanField(default=False)
    assigned_by_user_id = models.IntegerField()
    assignment_reason = models.TextField(blank=True, default="")

    class Meta:
        db_table = "superadmin_role_assignment"
        indexes = [
            models.Index(fields=["user_id", "status"], name="sa_role_usr_status_idx"),
            models.Index(fields=["role_name", "status"], name="sa_role_name_status_idx"),
            models.Index(fields=["status", "valid_to"], name="sa_role_status_vto_idx"),
            models.Index(fields=["status", "valid_from"], name="sa_role_status_vfrom_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["role_name"],
                condition=models.Q(is_singular=True, status__in=["ACTIVE", "EXTENDED"]),
                name="sa_singular_role_unique_active_holder",
            ),
        ]


class RoleHandoverRecord(TimeStampedModel):
    role_assignment = models.ForeignKey(
        RoleAssignmentRecord,
        on_delete=models.CASCADE,
        related_name="handovers",
    )
    from_user_id = models.IntegerField(db_index=True)
    to_user_id = models.IntegerField(db_index=True)
    effective_date = models.DateTimeField(db_index=True)
    pending_work_summary = models.TextField(blank=True, default="")
    audit_access_granted = models.BooleanField(default=True)

    class Meta:
        db_table = "superadmin_role_handover"
