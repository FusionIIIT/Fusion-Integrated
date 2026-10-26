"""Leave data owned by the ELM module; IAM identities are integer references."""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class LeaveType(TimeStampedModel):
    code = models.SlugField(max_length=32, unique=True)
    name = models.CharField(max_length=80)
    annual_allowance = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "leave_type"
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(condition=Q(annual_allowance__gte=0),
                                   name="leave_type_allowance_nonnegative"),
        ]


class LeaveBalance(TimeStampedModel):
    user_id = models.IntegerField(db_index=True)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT,
                                   related_name="balances")
    year = models.PositiveSmallIntegerField()
    allocated_days = models.DecimalField(max_digits=6, decimal_places=2)
    carried_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    class Meta:
        db_table = "leave_balance"
        constraints = [
            models.UniqueConstraint(fields=["user_id", "leave_type", "year"],
                                    name="leave_balance_user_type_year_uniq"),
            models.CheckConstraint(condition=Q(allocated_days__gte=0)
                                   & Q(carried_days__gte=0), name="leave_balance_nonnegative"),
        ]


class LeaveManagerAssignment(TimeStampedModel):
    """Explicit reporting scope until an HR employment contract is available."""

    manager_user_id = models.IntegerField(db_index=True)
    employee_user_id = models.IntegerField(db_index=True)
    assigned_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_manager_assignment"
        constraints = [
            models.UniqueConstraint(fields=["manager_user_id", "employee_user_id"],
                                    name="leave_manager_employee_uniq"),
            models.CheckConstraint(
                condition=~Q(manager_user_id=models.F("employee_user_id")),
                name="leave_manager_not_self",
            ),
        ]


class LeaveRequest(TimeStampedModel):
    STATUS = [("pending", "Pending"), ("approved", "Approved"),
              ("rejected", "Rejected"), ("cancelled", "Cancelled")]

    user_id = models.IntegerField(db_index=True)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT,
                                   related_name="requests")
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.PositiveSmallIntegerField()
    reason = models.CharField(max_length=1000)
    status = models.CharField(max_length=12, choices=STATUS, default="pending", db_index=True)
    reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "leave_request"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=Q(end_date__gte=models.F("start_date")),
                                   name="leave_request_date_order"),
            models.CheckConstraint(condition=Q(days__gt=0), name="leave_request_days_positive"),
        ]
        indexes = [models.Index(fields=["user_id", "-created_at"],
                                name="leave_request_user_recent_idx")]
