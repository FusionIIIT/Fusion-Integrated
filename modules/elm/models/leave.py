"""ELM tables.

People are referenced by IAM user id, never by ForeignKey: there is no user
table in this database (ADR-0013). Category and status are plain choices
instead of lookup tables, so the domain enums are the single source of truth.
"""
from django.db import models
from django.db.models import F, Q

from core.db.mixins import TimeStampedModel
from modules.elm.domain.entities import HalfDay, LeaveCategory, LeaveStatus

CATEGORY_CHOICES = [(c.value, c.name) for c in LeaveCategory]
STATUS_CHOICES = [(s.value, s.value.replace("_", " ").title()) for s in LeaveStatus]
HALF_CHOICES = [(h.value, h.name.title()) for h in HalfDay]


class LeaveBalance(TimeStampedModel):
    """One row per employee, year and category, created on first use from the
    annual entitlement."""

    user_id = models.IntegerField()
    year = models.PositiveSmallIntegerField()
    category = models.CharField(max_length=3, choices=CATEGORY_CHOICES)
    credited = models.DecimalField(max_digits=5, decimal_places=1)
    availed = models.DecimalField(max_digits=5, decimal_places=1, default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user_id", "year", "category"],
                                    name="elm_balance_one_per_category"),
            models.CheckConstraint(condition=Q(availed__gte=0) & Q(availed__lte=F("credited")),
                                   name="elm_balance_availed_within_credit"),
        ]


class LeaveRequest(TimeStampedModel):
    applicant_user_id = models.IntegerField()
    category = models.CharField(max_length=3, choices=CATEGORY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    half = models.CharField(max_length=6, choices=HALF_CHOICES, blank=True, default="")
    days = models.DecimalField(max_digits=5, decimal_places=1)
    reason = models.TextField(max_length=2000)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES,
                              default=LeaveStatus.PENDING)

    # BR-EL-013: Station Leave is part of the same application.
    is_station_leave = models.BooleanField(default=False)
    station_address = models.CharField(max_length=300, blank=True)
    station_contact = models.CharField(max_length=30, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(end_date__gte=F("start_date")),
                                   name="elm_request_end_after_start"),
            models.CheckConstraint(condition=Q(days__gt=0), name="elm_request_days_positive"),
            models.CheckConstraint(condition=Q(status__in=[s.value for s in LeaveStatus]),
                                   name="elm_request_status_valid"),
        ]
        indexes = [
            # "My leave" and the overlap check both filter on the applicant.
            models.Index(fields=["applicant_user_id", "-start_date"],
                         name="elm_request_applicant_idx"),
            # The approvals queue.
            models.Index(fields=["status", "-created_at"], name="elm_request_status_idx"),
        ]

    def __str__(self):
        return f"{self.category} {self.start_date}..{self.end_date} ({self.status})"


class LeaveRequestTransition(models.Model):
    """Append-only history: who moved a request, from where to where, and why."""

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                related_name="transitions")
    from_status = models.CharField(max_length=16)
    to_status = models.CharField(max_length=16)
    actor_user_id = models.IntegerField()
    remarks = models.CharField(max_length=500, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["at", "id"]

    def __str__(self):
        return f"{self.from_status} -> {self.to_status}"
