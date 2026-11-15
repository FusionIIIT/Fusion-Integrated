"""User lifecycle, identity immutability, profiles, and status history models."""
from django.db import models

from core.db.mixins import TimeStampedModel
from modules.system_admin.constants import UserKind, UserLifecycleStatus
from modules.system_admin.exceptions import ImmutableFieldModificationError


class BasicUser(TimeStampedModel):
    """Represents an identity account in Fusion ERP (Student, Faculty, or Staff)."""

    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=64, unique=True, db_index=True)
    institute_id = models.CharField(max_length=32, unique=True, db_index=True)  # BR-SA-001: Immutable!
    email = models.EmailField(unique=True, db_index=True)                        # BR-SA-002: iiitdmj.ac.in
    kind = models.CharField(max_length=16, choices=UserKind.choices, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    status = models.CharField(
        max_length=16,
        choices=UserLifecycleStatus.choices,
        default=UserLifecycleStatus.ACTIVE,
        db_index=True,
    )
    deactivated_at = models.DateTimeField(null=True, blank=True)
    date_of_joining = models.DateField(null=True, blank=True)
    expected_completion_date = models.DateField(null=True, blank=True)
    password_hash = models.CharField(max_length=255)
    password_changed_at = models.DateTimeField(auto_now_add=True)
    first_login_completed = models.BooleanField(default=False)

    class Meta:
        db_table = "system_admin_basic_user"
        indexes = [
            models.Index(fields=["status", "deactivated_at"]),
            models.Index(fields=["kind", "is_active"]),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            orig = BasicUser.objects.only("institute_id").get(pk=self.pk)
            if orig.institute_id != self.institute_id:
                raise ImmutableFieldModificationError("institute_id is immutable and cannot be changed.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.institute_id})"


class UserProfile(TimeStampedModel):
    """Stores user-type-specific attributes (BR-SA-003)."""

    user = models.OneToOneField(
        BasicUser,
        on_delete=models.CASCADE,
        related_name="profile",
        primary_key=True,
    )
    display_name = models.CharField(max_length=150)
    contact_number = models.CharField(max_length=20, blank=True)
    department = models.CharField(max_length=80, blank=True)       # Mandatory for faculty/staff
    programme = models.CharField(max_length=40, blank=True)        # Mandatory for student (B.Tech, M.Tech)
    discipline = models.CharField(max_length=40, blank=True)       # CSE, ECE, ME, Design
    batch_year = models.PositiveSmallIntegerField(null=True, blank=True)  # Mandatory for student
    employee_id = models.CharField(max_length=32, blank=True)      # Mandatory for faculty/staff
    extra_attributes = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "system_admin_user_profile"

    def __str__(self):
        return f"Profile of {self.user.username}"


class UserStatusHistory(TimeStampedModel):
    """Maintains complete audit history of all status changes (AFR-SA-014)."""

    user = models.ForeignKey(
        BasicUser,
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    from_status = models.CharField(max_length=16, choices=UserLifecycleStatus.choices)
    to_status = models.CharField(max_length=16, choices=UserLifecycleStatus.choices)
    changed_by = models.IntegerField(help_text="Super Admin user_id")
    reason = models.TextField()
    effective_timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "system_admin_user_status_history"
        ordering = ["-effective_timestamp"]

    def __str__(self):
        return f"StatusHistory: User {self.user_id} ({self.from_status} -> {self.to_status})"
