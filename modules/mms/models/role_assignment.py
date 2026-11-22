"""Role management (BR-MMS-002/003/004/006/007; UC-001).

Exactly one active Caretaker and exactly one active Warden at a time,
enforced by partial unique indexes so the invariant holds even if the
service layer is bypassed.
"""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class RoleAssignment(TimeStampedModel):
    DESIGNATION_CHOICES = [("caretaker", "Mess Caretaker"), ("warden", "Mess Warden")]

    designation = models.CharField(max_length=16, choices=DESIGNATION_CHOICES)
    #: Institute employee id (IAM user_id). Not a ForeignKey — no user table
    #: in this database (ADR-0013).
    employee_user_id = models.IntegerField(db_index=True)
    effective_from = models.DateTimeField()
    effective_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    assigned_by_user_id = models.IntegerField()

    class Meta:
        db_table = "mms_role_assignment"
        indexes = [
            models.Index(fields=["designation", "is_active"], name="role_assignment_active_idx"),
            models.Index(fields=["employee_user_id"], name="role_assignment_employee_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["designation"],
                condition=Q(designation="caretaker", is_active=True),
                name="one_active_caretaker",
            ),
            models.UniqueConstraint(
                fields=["designation"],
                condition=Q(designation="warden", is_active=True),
                name="one_active_warden",
            ),
            models.CheckConstraint(
                condition=Q(effective_until__isnull=True)
                | Q(effective_until__gt=models.F("effective_from")),
                name="role_assignment_valid_period",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.designation}:{self.employee_user_id}"
