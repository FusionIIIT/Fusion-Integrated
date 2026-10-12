"""Role and permission grants for ELM capability assignment."""

from django.contrib.auth.models import AbstractUser, Permission
from django.db import models

from core.db.mixins import TimeStampedModel


class ELMRole(TimeStampedModel):
    """Authority role: employee, unit head, leave administrator, deputy
    registrar, dean, registrar, director."""

    class Category(models.TextChoices):
        EMPLOYEE = "employee", "Employee managing own leave"
        UNIT_HEAD = "unit_head", "Unit Head"
        SANCTIONING = "sanctioning", "Sanctioning Authority"
        ESTABLISHMENT = "establishment", "Establishment processing"
        LEAVE_ADMIN = "leave_admin", "Leave Administrator"
        OPERATOR = "operator", "Operator"

    name = models.CharField(max_length=80)
    category = models.CharField(max_length=32, choices=Category.choices)

    class Meta:
        db_table = "elm_role"

    def __str__(self) -> str:
        return self.name


class RoleGrant(TimeStampedModel):
    """Assignment of an ELM role to a user with a designated scope."""

    role = models.ForeignKey(ELMRole, on_delete=models.CASCADE, related_name="grants")
    user = models.IntegerField(
        db_column="user_id",
        db_index=True,
        help_text="IAM user id of the employee who holds this role.",
    )
    unit_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="Unit Head's unit; null for institute-wide roles.",
    )
    scope = models.JSONField(
        default=dict,
        help_text="Scoped settings stored as JSON (e.g. leave year configuration).",
    )

    class Meta:
        db_table = "elm_role_grant"
        unique_together = [
            ("role", "user", "unit_id"),
        ]

    def __str__(self) -> str:
        return f"{self.role} -> {self.user_id}"
