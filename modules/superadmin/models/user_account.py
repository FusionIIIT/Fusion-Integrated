"""User account administrative record model."""

from django.db import models

from core.db.mixins import TimeStampedModel


class UserActivationStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    DEACTIVATED = "DEACTIVATED", "Deactivated"
    ARCHIVED_REVERSIBLE = "ARCHIVED_REVERSIBLE", "Archived (Reversible)"
    ARCHIVED_PERMANENT = "ARCHIVED_PERMANENT", "Archived (Permanently Non-Restorable)"


class UserType(models.TextChoices):
    STUDENT = "STUDENT", "Student"
    FACULTY = "FACULTY", "Faculty"
    STAFF = "STAFF", "Staff"


class UserAccountRecord(TimeStampedModel):
    user_id = models.IntegerField(unique=True, db_index=True)
    institute_id = models.CharField(max_length=64, unique=True, db_index=True)
    email = models.EmailField(unique=True, db_index=True)
    user_type = models.CharField(max_length=16, choices=UserType.choices)
    activation_status = models.CharField(
        max_length=32,
        choices=UserActivationStatus.choices,
        default=UserActivationStatus.ACTIVE,
        db_index=True,
    )
    deactivation_date = models.DateTimeField(null=True, blank=True)
    archival_date = models.DateTimeField(null=True, blank=True)
    reversibility_expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    department = models.CharField(max_length=128, blank=True, default="")
    program = models.CharField(max_length=64, blank=True, default="")
    batch = models.CharField(max_length=32, blank=True, default="")
    deactivation_reason = models.TextField(blank=True, default="")
    archival_reason = models.TextField(blank=True, default="")

    class Meta:
        db_table = "superadmin_user_account"
        indexes = [
            models.Index(
                fields=["activation_status", "reversibility_expires_at"],
                name="sa_usr_status_exp_idx",
            ),
            models.Index(fields=["user_type", "activation_status"], name="sa_usr_type_status_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(activation_status__in=UserActivationStatus.values),
                name="sa_usr_valid_status_check",
            ),
        ]
