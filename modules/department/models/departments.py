from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.department.domain import state_machine as sm
from modules.department.domain.rules import OFFICIAL_FIELDS


class Department(TimeStampedModel):
    code = models.CharField(max_length=12, unique=True)
    name = models.CharField(max_length=120)
    core_policies = models.TextField(blank=True)
    description = models.TextField(blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    office_location = models.CharField(max_length=120, blank=True)
    website = models.URLField(blank=True)

    class Meta:
        db_table = "department_department"
        ordering = ["code"]
        constraints = [
            models.CheckConstraint(condition=~Q(name=""), name="dept_name_not_blank"),
        ]

    def __str__(self) -> str:
        return self.code


class OfficialChange(TimeStampedModel):
    """A proposed official detail that is not effective until the HOD approves it (BR-DEPT-011)."""

    STATUS = [
        (sm.CHANGE_PENDING, "Pending HOD approval"),
        (sm.CHANGE_APPROVED, "Approved"),
        (sm.CHANGE_REJECTED, "Rejected"),
    ]
    FIELDS = [(f, f) for f in OFFICIAL_FIELDS]

    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="official_changes"
    )
    field = models.CharField(max_length=20, choices=FIELDS)
    proposed_value = models.TextField()
    previous_value = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default=sm.CHANGE_PENDING)
    proposed_by = models.IntegerField()
    decided_by = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "department_official_change"
        constraints = [
            models.CheckConstraint(
                condition=Q(field__in=OFFICIAL_FIELDS), name="dept_change_official_field"
            ),
            models.UniqueConstraint(
                fields=["department", "field"],
                condition=Q(status=sm.CHANGE_PENDING),
                name="dept_change_one_pending_per_field",
            ),
            models.CheckConstraint(
                condition=Q(status=sm.CHANGE_PENDING, decided_by__isnull=True)
                | (~Q(status=sm.CHANGE_PENDING) & Q(decided_by__isnull=False)),
                name="dept_change_decided_iff_not_pending",
            ),
        ]
        indexes = [
            models.Index(fields=["department", "status", "-id"], name="dept_change_queue_idx")
        ]
