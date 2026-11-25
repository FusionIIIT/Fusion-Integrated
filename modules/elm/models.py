"""Initial ELM domain model.

This is an initial implementation slice, not a claim that every ELM workflow
and business rule in the supplied specification is complete.
"""
from django.db import models
from django.db.models import Q
from core.db.mixins import TimeStampedModel


class LeaveBalance(TimeStampedModel):
    """Annual balance ledger keyed to Fusion's external employee user id."""
    CATEGORY_CHOICES = [
        ("CL", "Casual Leave"), ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"), ("EL", "Earned Leave"),
        ("COL", "Commuted Leave"), ("VL", "Vacation Leave"),
    ]
    user_id = models.PositiveBigIntegerField(db_index=True)
    year = models.PositiveSmallIntegerField(db_index=True)
    category = models.CharField(max_length=3, choices=CATEGORY_CHOICES)
    entitled_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    carried_forward_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    consumed_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    class Meta:
        db_table = "elm_leave_balance"
        constraints = [
            models.UniqueConstraint(fields=("user_id", "year", "category"),
                                    name="elm_balance_user_year_category_uniq"),
            models.CheckConstraint(condition=Q(entitled_days__gte=0),
                                   name="elm_balance_entitled_nonnegative"),
            models.CheckConstraint(condition=Q(carried_forward_days__gte=0),
                                   name="elm_balance_carry_nonnegative"),
            models.CheckConstraint(condition=Q(consumed_days__gte=0),
                                   name="elm_balance_consumed_nonnegative"),
        ]

    @property
    def available_days(self):
        return self.entitled_days + self.carried_forward_days - self.consumed_days


class LeaveRequest(TimeStampedModel):
    CATEGORY_CHOICES = LeaveBalance.CATEGORY_CHOICES
    STATUS_CHOICES = [
        ("awaiting_substitute", "Awaiting Substitute Response"),
        ("applicant_action_required", "Applicant Action Required"),
        ("unit_head_review", "Unit Head Review"),
        ("higher_sanction", "Higher Sanction"),
        ("approved", "Approved"), ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"), ("cancelled", "Cancelled"),
    ]
    HALF_CHOICES = [("full", "Full day"), ("first", "First half"),
                    ("second", "Second half")]

    applicant_user_id = models.PositiveBigIntegerField(db_index=True)
    category = models.CharField(max_length=3, choices=CATEGORY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.CharField(max_length=6, choices=HALF_CHOICES, default="full")
    reason = models.TextField()
    station_leave_required = models.BooleanField(default=False)
    station_leave_details = models.TextField(blank=True)
    substitute_user_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    substitute_response = models.CharField(
        max_length=8, choices=[("pending", "Pending"), ("accepted", "Accepted"),
                               ("declined", "Declined")],
        default="pending")
    status = models.CharField(max_length=32, choices=STATUS_CHOICES,
                              default="unit_head_review", db_index=True)
    current_reviewer_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    final_decision_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    final_decision_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True)

    class Meta:
        db_table = "elm_leave_request"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("applicant_user_id", "status"),
                         name="elm_request_applicant_status"),
            models.Index(fields=("current_reviewer_user_id", "status"),
                         name="elm_request_reviewer_status"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(end_date__gte=models.F("start_date")),
                                   name="elm_request_dates_ordered"),
        ]


class LeaveAction(TimeStampedModel):
    """Append-only record of decisions and other request lifecycle actions."""
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                related_name="actions")
    actor_user_id = models.PositiveBigIntegerField(db_index=True)
    action = models.CharField(max_length=40)
    note = models.TextField(blank=True)
    from_status = models.CharField(max_length=32, blank=True)
    to_status = models.CharField(max_length=32, blank=True)

    class Meta:
        db_table = "elm_leave_action"
        ordering = ("created_at",)
