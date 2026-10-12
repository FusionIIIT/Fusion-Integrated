from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel


class LeavePolicy(TimeStampedModel):
    """EL-UC-014, BR-EL-030"""

    CATEGORY_CHOICES = [
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Compensatory Leave"),
        ("VL", "Vacation Leave"),
    ]

    category = models.CharField(max_length=3, choices=CATEGORY_CHOICES)
    annual_entitlement = models.DecimalField(max_digits=5, decimal_places=1)
    carries_forward = models.BooleanField(default=False)
    applies_to = models.CharField(
        max_length=20, choices=[("all", "All"), ("faculty", "Faculty"), ("staff", "Staff")]
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "leave_policy"
        constraints = [
            models.UniqueConstraint(fields=["category"], name="policy_unique_category"),
        ]
        indexes = [
            models.Index(fields=["category", "is_active"], name="policy_category_active_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.category} - {self.annual_entitlement}"


class OrgUnit(TimeStampedModel):
    """EL-UC-014, BR-EL-030"""

    name = models.CharField(max_length=120, unique=True)
    unit_head_user_id = models.IntegerField()

    class Meta:
        db_table = "leave_org_unit"

    def __str__(self) -> str:
        return self.name
