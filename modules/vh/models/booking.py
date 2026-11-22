# Booking model aggregate for VHMS.
from django.db import models
from django.db.models import CheckConstraint, F, Index, Q

from core.db.mixins import TimeStampedModel
from modules.vh.domain.rules import BILLING_RESPONSIBILITY_CHOICES, VISITOR_CATEGORY_CHOICES


class Booking(TimeStampedModel):
    # Primary booking requisition aggregate for VHMS.
    booking_reference = models.CharField(max_length=32, unique=True, db_index=True)
    indenter_id = models.IntegerField(db_index=True)
    is_offline = models.BooleanField(default=False, db_index=True)
    booking_source = models.CharField(
        max_length=20,
        choices=[("online", "Online"), ("telephonic", "Telephonic"), ("walk_in", "Walk-in")],
        default="online",
    )
    status = models.CharField(max_length=32, default="pending", db_index=True)
    visitor_category = models.CharField(
        max_length=1,
        choices=VISITOR_CATEGORY_CHOICES,
        default="A",
        db_index=True,
    )
    visit_purpose = models.TextField()
    arrival_date = models.DateField(db_index=True)
    departure_date = models.DateField(db_index=True)
    checkin_time = models.DateTimeField(null=True, blank=True)
    checkout_time = models.DateTimeField(null=True, blank=True)
    number_of_rooms = models.PositiveIntegerField(default=1)
    number_of_occupants = models.PositiveIntegerField(default=1)
    billing_responsibility = models.CharField(
        max_length=20,
        choices=BILLING_RESPONSIBILITY_CHOICES,
        default="visitor",
    )
    rejection_reason = models.TextField(blank=True, default="")
    cancellation_reason = models.TextField(blank=True, default="")
    cancellation_charge_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00
    )
    cancellation_requested_at = models.DateTimeField(null=True, blank=True)
    cancellation_confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "vh_booking"
        indexes = [
            Index(fields=["indenter_id", "status"], name="vh_bk_indenter_status_idx"),
            Index(fields=["arrival_date", "status"], name="vh_bk_arrival_status_idx"),
            Index(fields=["departure_date", "status"], name="vh_bk_departure_status_idx"),
        ]
        constraints = [
            CheckConstraint(
                condition=Q(departure_date__gte=F("arrival_date")),
                name="vh_bk_departure_gte_arrival",
            ),
            CheckConstraint(
                condition=Q(number_of_rooms__gt=0),
                name="vh_bk_rooms_gt_zero",
            ),
            CheckConstraint(
                condition=Q(number_of_occupants__gt=0),
                name="vh_bk_occupants_gt_zero",
            ),
            CheckConstraint(
                condition=Q(
                    billing_responsibility__in=["visitor", "indenter", "institute", "project"]
                ),
                name="vh_bk_valid_billing_resp",
            ),
        ]

    def __str__(self) -> str:
        return f"Booking {self.booking_reference} ({self.status})"
