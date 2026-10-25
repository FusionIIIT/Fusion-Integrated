from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class Leave(TimeStampedModel, UserScopedModel):
    LEAVE_CATEGORIES = [
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Extra Leave"),
        ("COL", "Compensatory Off Leave"),
        ("VL", "Vacation Leave"),
    ]

    REQUEST_STATUS = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    leave_category = models.CharField(max_length=3, choices=LEAVE_CATEGORIES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    request_status = models.CharField(
        max_length=10,
        choices=REQUEST_STATUS,
        default="PENDING",
    )

    class Meta:
        db_table = "elm_leave"

    def __str__(self):
        return (
            f"User {self.user_id} - {self.get_leave_category_display()} "
            f"from {self.start_date} to {self.end_date}"
        )