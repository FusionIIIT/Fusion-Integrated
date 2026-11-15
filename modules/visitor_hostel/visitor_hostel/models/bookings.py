"""Bookings and their audit trail.

People are plain `user_id` integers — the IAM's ids, never a foreign key.
"""
from django.db import models
from django.db.models import F, Q

from core.db.mixins import TimeStampedModel
from modules.visitor_hostel.domain import requisition as req
from modules.visitor_hostel.domain import state_machine as sm
from modules.visitor_hostel.domain import tariffs


def _choices(values, labels=None):
    labels = labels or {}
    return [(v, labels.get(v, v.replace("_", " ").title())) for v in values]


class Booking(TimeStampedModel):
    STATUS = _choices(sm.ALL_STATES)
    CATEGORY = [(c, f"Category {c}") for c in tariffs.CATEGORIES]
    OCCUPANCY = _choices(tariffs.OCCUPANCIES)
    BILLING = _choices(req.BILLING_RESPONSIBILITIES)
    SOURCE = _choices((req.ONLINE, *req.OFFLINE_SOURCES), {"walk_in": "Walk-in"})

    # Null only for an offline booking taken for someone outside the institute.
    indenter_user_id = models.IntegerField(null=True, blank=True)
    recorded_by_user_id = models.IntegerField()
    source = models.CharField(max_length=12, choices=SOURCE, default=req.ONLINE)
    is_offline = models.BooleanField(default=False)            # BR-VH-005

    visitor_name = models.CharField(max_length=120)
    visitor_phone = models.CharField(max_length=32, blank=True)
    visitor_email = models.EmailField(blank=True)
    visitor_organization = models.CharField(max_length=160, blank=True)
    visitor_address = models.CharField(max_length=300, blank=True)
    purpose = models.TextField(max_length=1000)
    category = models.CharField(max_length=1, choices=CATEGORY)
    occupancy = models.CharField(max_length=8, choices=OCCUPANCY)

    arrival_date = models.DateField()
    arrival_time = models.TimeField(null=True, blank=True)
    departure_date = models.DateField()
    departure_time = models.TimeField(null=True, blank=True)
    rooms_required = models.PositiveSmallIntegerField(default=1)
    occupants = models.PositiveSmallIntegerField(default=1)

    billing_responsibility = models.CharField(max_length=10, choices=BILLING)
    billing_reference = models.CharField(max_length=120, blank=True)

    status = models.CharField(max_length=16, choices=STATUS, default=sm.PENDING)
    decision_reason = models.CharField(max_length=300, blank=True)
    # Who holds the record now; moved to the new holder on reassignment.
    caretaker_user_id = models.IntegerField(null=True, blank=True)
    incharge_user_id = models.IntegerField(null=True, blank=True)

    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "vh_booking"
        constraints = [
            models.CheckConstraint(condition=Q(status__in=sm.ALL_STATES),
                                   name="vh_booking_status_valid"),
            models.CheckConstraint(condition=Q(category__in=tariffs.CATEGORIES),
                                   name="vh_booking_category_valid"),
            models.CheckConstraint(condition=Q(occupancy__in=tariffs.OCCUPANCIES),
                                   name="vh_booking_occupancy_valid"),
            models.CheckConstraint(
                condition=Q(billing_responsibility__in=req.BILLING_RESPONSIBILITIES),
                name="vh_booking_billing_valid"),
            models.CheckConstraint(
                condition=(Q(is_offline=False, source=req.ONLINE)
                           | Q(is_offline=True, source__in=req.OFFLINE_SOURCES)),
                name="vh_booking_offline_flag_matches_source"),
            models.CheckConstraint(
                condition=Q(is_offline=True) | Q(indenter_user_id__isnull=False),
                name="vh_booking_online_has_indenter"),
            models.CheckConstraint(condition=Q(departure_date__gte=F("arrival_date")),
                                   name="vh_booking_dates_ordered"),
            models.CheckConstraint(condition=Q(rooms_required__gte=1)
                                   & Q(occupants__gte=1),
                                   name="vh_booking_counts_positive"),
            models.CheckConstraint(
                condition=~Q(status__in=(sm.CHECKED_IN, sm.CHECKED_OUT))
                | Q(checked_in_at__isnull=False),
                name="vh_booking_checked_in_has_time"),
            models.CheckConstraint(
                condition=~Q(status=sm.CHECKED_OUT) | Q(checked_out_at__isnull=False),
                name="vh_booking_checked_out_has_time"),
        ]
        indexes = [
            models.Index(fields=["status", "arrival_date"], name="vh_booking_status_idx"),
            models.Index(fields=["indenter_user_id", "-created_at"],
                         name="vh_booking_indenter_idx"),
            models.Index(fields=["departure_date", "status"],
                         name="vh_booking_departure_idx"),
        ]

    def __str__(self) -> str:
        return f"booking#{self.pk} {self.status}"


class BookingTransition(models.Model):
    """Append-only audit of every status change and confirmed modification."""

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE,
                                related_name="transitions")
    from_status = models.CharField(max_length=16, blank=True)
    to_status = models.CharField(max_length=16)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_lane = models.CharField(max_length=12)
    reason = models.CharField(max_length=300, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vh_booking_transition"
        indexes = [models.Index(fields=["booking", "at"], name="vh_transition_idx")]

    def __str__(self) -> str:
        return f"booking#{self.booking_id} {self.from_status}->{self.to_status}"


class CancellationRequest(TimeStampedModel):
    """UC-VH-007's request and the charge case it fell into (BR-VH-006..009)."""

    STATUS = [("requested", "Requested"), ("confirmed", "Confirmed")]

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE,
                                   related_name="cancellation")
    requested_by_user_id = models.IntegerField()
    requested_on = models.DateField()
    days_before_arrival = models.IntegerField()
    charge_case = models.CharField(max_length=20)
    charge_percent = models.DecimalField(max_digits=5, decimal_places=2)
    one_day_rent = models.DecimalField(max_digits=10, decimal_places=2,
                                       null=True, blank=True)
    charge_amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="requested")
    confirmed_by_user_id = models.IntegerField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "vh_cancellation_request"
        constraints = [
            models.CheckConstraint(
                condition=~Q(status="confirmed") | Q(confirmed_at__isnull=False),
                name="vh_cancellation_confirmed_has_time"),
            models.CheckConstraint(condition=Q(charge_amount__gte=0),
                                   name="vh_cancellation_charge_non_negative"),
        ]

    def __str__(self) -> str:
        return f"cancel booking#{self.booking_id} {self.charge_case}"


class ModificationRequest(TimeStampedModel):
    """UC-VH-006's request; confirmed under UC-VH-022 (authority unresolved)."""

    STATUS = [("requested", "Requested"), ("confirmed", "Confirmed")]

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE,
                                related_name="modifications")
    requested_by_user_id = models.IntegerField()
    changes = models.JSONField()
    previous = models.JSONField(default=dict, blank=True)
    reason = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="requested")
    confirmed_by_user_id = models.IntegerField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "vh_modification_request"
        constraints = [
            models.UniqueConstraint(fields=["booking"], condition=Q(status="requested"),
                                    name="vh_one_open_modification_per_booking"),
            models.CheckConstraint(
                condition=~Q(status="confirmed") | Q(confirmed_at__isnull=False),
                name="vh_modification_confirmed_has_time"),
        ]

    def __str__(self) -> str:
        return f"modify booking#{self.booking_id} {self.status}"
