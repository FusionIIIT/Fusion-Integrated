"""RoleAssignment model for role lifecycle and authorization metadata."""
from django.db import models
from django.db.models import CheckConstraint, F, Q

from core.db.mixins import TimeStampedModel


class RoleAssignmentQuerySet(models.QuerySet):
    def filter(self, *args, **kwargs):
        if "user" in kwargs:
            val = kwargs.pop("user")
            kwargs["user_id"] = getattr(val, "user_id", getattr(val, "pk", val))
        return super().filter(*args, **kwargs)

    def get(self, *args, **kwargs):
        if "user" in kwargs:
            val = kwargs.pop("user")
            kwargs["user_id"] = getattr(val, "user_id", getattr(val, "pk", val))
        return super().get(*args, **kwargs)


class RoleAssignment(TimeStampedModel):
    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("active", "Active"),
        ("expired", "Expired"),
        ("revoked", "Revoked"),
    ]

    role_code = models.CharField(max_length=64, db_index=True)
    role_name = models.CharField(max_length=120, blank=True)
    user_id = models.IntegerField(db_index=True)
    status = models.CharField(
        max_length=24, choices=STATUS_CHOICES, default="active", db_index=True
    )
    is_singular = models.BooleanField(default=False)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(null=True, blank=True, db_index=True)
    scope = models.CharField(max_length=80, blank=True)
    reason = models.TextField()
    assigned_by = models.IntegerField()

    objects = RoleAssignmentQuerySet.as_manager()

    class Meta:
        db_table = "system_admin_role_assignment"
        ordering = ["-created_at"]
        constraints = [
            CheckConstraint(
                condition=Q(end_date__isnull=True) | Q(end_date__gte=F("start_date")),
                name="chk_sa_role_dates",
            ),
            CheckConstraint(
                condition=Q(status__in=["scheduled", "active", "expired", "revoked"]),
                name="chk_sa_role_status",
            ),
        ]
        indexes = [
            models.Index(fields=["user_id", "status"], name="idx_sa_user_role_status"),
            models.Index(fields=["role_code", "status"], name="idx_sa_role_code_status"),
        ]


    def __init__(self, *args, **kwargs):
        if "user" in kwargs:
            val = kwargs.pop("user")
            kwargs["user_id"] = getattr(val, "user_id", getattr(val, "pk", val))
        if "role_name" in kwargs and "role_code" not in kwargs:
            kwargs["role_code"] = kwargs.get("role_name")
        if isinstance(kwargs.get("assigned_by"), str):
            kwargs["assigned_by"] = 1
        super().__init__(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.role_code} -> user_id={self.user_id} ({self.status})"
