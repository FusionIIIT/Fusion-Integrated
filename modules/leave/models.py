"""Leave's first owned table.

User ids deliberately remain plain integers: IAM owns identities and a leave
request must not introduce a cross-module/user-table foreign key.
"""
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveRequest(TimeStampedModel, UserScopedModel):
    """A submitted CL/RH request or its terminal withdrawal.

    Approval, balances and routing are not represented here yet; they require
    the organisation and authority contracts that the repository does not own.
    """

    CATEGORY_CL = "cl"
    CATEGORY_RH = "rh"
    CATEGORIES = [(CATEGORY_CL, "Casual Leave"), (CATEGORY_RH, "Restricted Holiday")]

    HALF_FULL = "full"
    HALF_FIRST = "first"
    HALF_SECOND = "second"
    HALF_CHOICES = [
        (HALF_FULL, "Full day"),
        (HALF_FIRST, "First half"),
        (HALF_SECOND, "Second half"),
    ]

    STATUS_PENDING = "pending"
    STATUS_WITHDRAWN = "withdrawn"
    STATUSES = [(STATUS_PENDING, "Pending"), (STATUS_WITHDRAWN, "Withdrawn")]

    category = models.CharField(max_length=2, choices=CATEGORIES)
    starts_on = models.DateField()
    ends_on = models.DateField()
    cl_half = models.CharField(max_length=6, choices=HALF_CHOICES, default=HALF_FULL)
    reason = models.CharField(max_length=500)
    station_leave = models.BooleanField(default=False)
    station_leave_details = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=12, choices=STATUSES, default=STATUS_PENDING)
    withdrawn_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_request"
        ordering = ["-starts_on", "-created_at"]
        indexes = [models.Index(fields=["user_id", "status", "starts_on"])]
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_on__gte=models.F("starts_on")),
                name="leave_request_valid_date_range",
            ),
            models.CheckConstraint(
                condition=(Q(category="cl") | Q(cl_half="full")),
                name="leave_request_half_only_for_cl",
            ),
        ]
