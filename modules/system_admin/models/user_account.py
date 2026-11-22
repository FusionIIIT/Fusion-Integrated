"""UserAccount model for basic identity and activation lifecycle."""
from django.db import models
from django.db.models import CheckConstraint, Q

from core.db.mixins import TimeStampedModel


class UserAccount(TimeStampedModel):
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

    user_id = models.IntegerField(primary_key=True)
    institute_id = models.CharField(max_length=32, unique=True, db_index=True)
    username = models.CharField(max_length=64, unique=True, db_index=True)
    email = models.EmailField(db_index=True)
    user_type = models.CharField(max_length=16, choices=USER_TYPE_CHOICES, db_index=True)
    name = models.CharField(max_length=150, blank=True)
    contact_number = models.CharField(max_length=32, blank=True)
    department = models.CharField(max_length=80, blank=True)
    programme = models.CharField(max_length=40, blank=True)
    discipline = models.CharField(max_length=40, blank=True)
    batch_year = models.PositiveSmallIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=24, choices=STATUS_CHOICES, default="active", db_index=True
    )
    deactivated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "system_admin_user_account"
        ordering = ["-created_at"]
        constraints = [
            CheckConstraint(
                condition=Q(user_type__in=["student", "faculty", "staff"]),
                name="chk_sa_user_type",
            ),
            CheckConstraint(
                condition=Q(status__in=["active", "deactivated", "archived"]),
                name="chk_sa_user_status",
            ),
        ]


    @property
    def roles(self):
        from modules.system_admin.models.role_assignment import RoleAssignment
        return RoleAssignment.objects.filter(user_id=self.user_id)

    def save(self, *args, **kwargs):
        if not self.user_id:
            max_id = UserAccount.objects.aggregate(models.Max("user_id"))["user_id__max"] or 1000
            self.user_id = max_id + 1
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.institute_id} ({self.username}) - {self.status}"
