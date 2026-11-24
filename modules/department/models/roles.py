from django.db import models
from django.db.models import F, Q

from core.db.mixins import TimeStampedModel
from modules.department.domain.roles import DEPT_ADMIN, HOD


class RoleTenure(TimeStampedModel):
    """A business record of who holds HOD or Dept_Admin, and when (Q1). It grants no permission."""

    ROLES = [(HOD, "HOD"), (DEPT_ADMIN, "Dept_Admin")]

    department = models.ForeignKey(
        "department.Department", on_delete=models.PROTECT, related_name="tenures"
    )
    role = models.CharField(max_length=10, choices=ROLES)
    user_id = models.IntegerField()
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    assigned_by = models.IntegerField()
    transition_applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "department_role_tenure"
        constraints = [
            models.CheckConstraint(
                condition=Q(valid_to__gt=F("valid_from")), name="dept_tenure_interval"
            ),
            models.CheckConstraint(
                condition=Q(role__in=[HOD, DEPT_ADMIN]), name="dept_tenure_role_known"
            ),
        ]
        indexes = [
            models.Index(
                fields=["department", "role", "valid_from"], name="dept_tenure_lookup_idx"
            ),
            models.Index(fields=["user_id", "role"], name="dept_tenure_user_idx"),
            models.Index(
                fields=["transition_applied_at", "valid_from"], name="dept_tenure_pending_idx"
            ),
        ]
