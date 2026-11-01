"""User Management Models for System Admin Control Plane."""
from django.db import models
from core.db.mixins import TimeStampedModel


class BasicUserProfile(TimeStampedModel):
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

    internal_user_id = models.IntegerField(unique=True, db_index=True)
    institute_id = models.CharField(max_length=32, unique=True, db_index=True)
    user_type = models.CharField(max_length=16, choices=USER_TYPE_CHOICES, db_index=True)
    full_name = models.CharField(max_length=150)
    institute_email = models.EmailField(unique=True, db_index=True)
    contact_number = models.CharField(max_length=20, blank=True)
    department = models.CharField(max_length=100, blank=True)
    programme = models.CharField(max_length=50, blank=True)
    discipline = models.CharField(max_length=50, blank=True)
    batch_year = models.PositiveSmallIntegerField(null=True, blank=True)
    employee_id = models.CharField(max_length=32, blank=True)
    date_of_joining = models.DateField()
    expected_completion_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="active", db_index=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    deactivation_reason = models.TextField(blank=True)
    initial_password_issued = models.BooleanField(default=True)
    has_dashboard_access = models.BooleanField(default=True)

    class Meta:
        db_table = "systemadmin_basic_user"
        ordering = ["institute_id"]
        indexes = [
            models.Index(fields=["user_type", "status"], name="sa_user_type_status_idx"),
            models.Index(fields=["department"], name="sa_user_dept_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.institute_id}) - {self.user_type}"


class UserStatusHistory(TimeStampedModel):
    user = models.ForeignKey(
        BasicUserProfile,
        on_delete=models.CASCADE,
        related_name="status_history"
    )
    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)
    reason = models.TextField()
    actor_username = models.CharField(max_length=64)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "systemadmin_user_status_history"
        ordering = ["-changed_at"]

    def __str__(self) -> str:
        return f"{self.user.institute_id}: {self.from_status} -> {self.to_status} by {self.actor_username}"
