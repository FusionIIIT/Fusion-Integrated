from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveBalance(TimeStampedModel, UserScopedModel):
    """EL-UC-012, BR-EL-030"""

    CATEGORY_CHOICES = [
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Commuted Leave"),
        ("VL", "Vacation Leave"),
    ]

    user_id = models.IntegerField()
    year = models.IntegerField()
    category = models.CharField(max_length=3, choices=CATEGORY_CHOICES)
    entitled = models.DecimalField(max_digits=5, decimal_places=1)
    used = models.DecimalField(max_digits=5, decimal_places=1, default=0)

    class Meta:
        db_table = "leave_balance"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "year", "category"], name="balance_unique_user_year_category"
            ),
        ]
        indexes = [
            models.Index(fields=["user_id", "year"], name="balance_user_year_idx"),
            models.Index(fields=["user_id", "category"], name="balance_user_category_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} {self.year} {self.category} {self.entitled} {self.used}"
