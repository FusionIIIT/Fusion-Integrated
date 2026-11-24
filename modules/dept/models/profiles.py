"""User profile extension within department (CFR-DEPT-009, CFR-DEPT-010, BR-DEPT-019)."""

import uuid

from django.db import models

from modules.dept.models.department import Department


class UserProfileExtension(models.Model):
    PROFILE_TYPE_CHOICES = [
        ("STUDENT", "Student"),
        ("FACULTY", "Faculty"),
        ("ALUMNI", "Alumni"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="profile_extensions",
    )
    user_id = models.CharField(max_length=64)
    profile_type = models.CharField(max_length=32, choices=PROFILE_TYPE_CHOICES)
    office_room = models.CharField(max_length=64, blank=True, default="")
    research_interests = models.TextField(blank=True, default="")
    contact_phone = models.CharField(max_length=32, blank=True, default="")
    emergency_contact = models.CharField(max_length=128, blank=True, default="")
    courses_taught = models.JSONField(default=list, blank=True)
    batch_or_roll = models.CharField(max_length=32, blank=True, default="")
    graduation_year = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dept_user_profile_extension"
        ordering = ["user_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["department", "user_id"],
                name="unique_dept_user_profile",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} ({self.profile_type})"
