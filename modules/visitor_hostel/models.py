from datetime import time
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class VisitorCategoryTariff(TimeStampedModel):
    CATEGORY_CHOICES = [
        ("A", "Category A"),
        ("B", "Category B"),
        ("C", "Category C"),
        ("D", "Category D"),
    ]
    ROOM_TYPE_CHOICES = [
        ("suite", "Suite"),
        ("non_suite", "Non-Suite"),
    ]
    OCCUPANCY_CHOICES = [
        ("single", "Single"),
        ("double", "Double"),
    ]

    category = models.CharField(max_length=1, choices=CATEGORY_CHOICES)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPE_CHOICES)
    occupancy = models.CharField(max_length=20, choices=OCCUPANCY_CHOICES)
    daily_rate = models.DecimalField(max_digits=8, decimal_places=2)
    effective_from = models.DateField(default=timezone.localdate)

    class Meta:
        db_table = "vh_tariff"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(daily_rate__gte=0), name="vh_rate_nonnegative"
            )
        ]

        ordering = ["-effective_from"]

    def __str__(self):
        return f"Cat {self.category} - {self.room_type} ({self.occupancy}): {self.daily_rate}"


class Room(TimeStampedModel):
    ROOM_TYPE_CHOICES = [
        ("suite", "Suite"),
        ("non_suite", "Non-Suite"),
    ]
    STATUS_CHOICES = [
        ("available", "Available"),
        ("occupied", "Occupied"),
        ("maintenance", "Maintenance"),
    ]

    room_number = models.CharField(max_length=10, unique=True)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="available")

    class Meta:
        db_table = "vh_room"

    def __str__(self):
        return f"Room {self.room_number} ({self.room_type})"


class BookingRequest(TimeStampedModel):
    STATUS_CHOICES = [
        ("pending", "Pending Caretaker Review"),
        ("forwarded", "Forwarded to In-Charge"),
        ("approved", "Approved"),
        ("confirmed", "Confirmed"),
        ("rejected", "Rejected"),
        ("checked_in", "Checked In"),
        ("checked_out", "Checked Out"),
        ("cancelled", "Cancelled"),
    ]
    BILLING_RESPONSIBILITY_CHOICES = [
        ("Visitor", "Visitor"),
        ("Indenter", "Indenter"),
        ("Institute", "Institute"),
        ("Project", "Project"),
    ]

    # Legacy Django ids are retained separately until an operator verifies the IAM mapping.
    legacy_indenter_id = models.PositiveBigIntegerField(null=True, blank=True, editable=False)
    indenter_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    visitor_name = models.CharField(max_length=100)
    visitor_phone = models.CharField(max_length=20, blank=True)
    visitor_email = models.EmailField(blank=True)
    visitor_category = models.CharField(
        max_length=1, choices=VisitorCategoryTariff.CATEGORY_CHOICES
    )
    purpose = models.TextField()
    is_offline = models.BooleanField(default=False)

    check_in_date = models.DateField()
    check_out_date = models.DateField()
    check_in_time = models.TimeField(default=time(14, 0))
    check_out_time = models.TimeField(default=time(11, 0))
    number_of_occupants = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    cancellation_requested_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    modification_request = models.JSONField(default=dict, blank=True)
    number_of_rooms = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    occupancy = models.CharField(
        max_length=20, choices=VisitorCategoryTariff.OCCUPANCY_CHOICES, default="single"
    )
    room_type = models.CharField(
        max_length=20, choices=VisitorCategoryTariff.ROOM_TYPE_CHOICES, default="non_suite"
    )

    billing_responsibility = models.CharField(
        max_length=20, choices=BILLING_RESPONSIBILITY_CHOICES, default="Visitor"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    rejection_reason = models.TextField(blank=True, null=True)  # noqa: DJ001 - legacy nullable data

    class Meta:
        db_table = "vh_booking_request"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(number_of_rooms__gte=1), name="vh_rooms_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(number_of_occupants__gte=1), name="vh_occupants_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(check_out_date__gt=models.F("check_in_date"))
                | (
                    models.Q(check_out_date=models.F("check_in_date"))
                    & models.Q(check_out_time__gt=models.F("check_in_time"))
                ),
                name="vh_stay_dates_ordered",
            ),
        ]

    def __str__(self):
        return f"Booking #{self.id} - {self.visitor_name} ({self.status})"


class RoomAllotment(TimeStampedModel):
    booking = models.ForeignKey(BookingRequest, on_delete=models.CASCADE, related_name="allotments")
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="allotments")
    actual_check_in = models.DateTimeField(null=True, blank=True)
    actual_check_out = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "vh_room_allotment"
        constraints = [
            models.UniqueConstraint(fields=["booking", "room"], name="vh_unique_allotment")
        ]

    def __str__(self):
        return f"Allotment: Booking #{self.booking_id} -> Room {self.room.room_number}"


class MealBooking(TimeStampedModel):
    MEAL_CHOICES = [
        ("breakfast", "Breakfast"),
        ("lunch", "Lunch"),
        ("dinner", "Dinner"),
        ("full_day", "Full Day"),
        ("tea", "Add-on: Tea"),
        ("milk", "Add-on: Milk"),
    ]

    booking = models.ForeignKey(
        BookingRequest, on_delete=models.CASCADE, related_name="meal_bookings"
    )
    date = models.DateField()
    meal_type = models.CharField(max_length=20, choices=MEAL_CHOICES)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    rate = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("50.00"))

    class Meta:
        db_table = "vh_meal_booking"
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gte=1), name="vh_meal_positive"),
            models.CheckConstraint(
                condition=models.Q(rate__gte=0), name="vh_meal_rate_nonnegative"
            ),
        ]

    def __str__(self):
        return f"{self.meal_type} x{self.quantity} for Booking #{self.booking_id} on {self.date}"


class BillQuerySet(models.QuerySet):
    def update(self, **kwargs):
        from django.core.exceptions import ValidationError

        raise ValidationError(
            "Billing records must be changed through audited settlement operations."
        )

    def delete(self):
        from django.core.exceptions import ValidationError

        raise ValidationError("Billing records cannot be deleted.")


class Bill(TimeStampedModel):
    booking = models.OneToOneField(BookingRequest, on_delete=models.PROTECT, related_name="bill")
    room_charge = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    meal_charge = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    cancellation_charge = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    is_settled_offline = models.BooleanField(default=False)
    settlement_date = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    is_immutable = models.BooleanField(default=False)
    objects = BillQuerySet.as_manager()

    class Meta:
        db_table = "vh_bill"

    def __str__(self):
        return f"Bill #{self.id} for Booking #{self.booking_id} - Total: {self.total_amount}"

    def save(self, *args, **kwargs):
        from django.core.exceptions import ValidationError

        if self.pk:
            old = type(self).objects.get(pk=self.pk)
            protected = (
                "booking_id",
                "room_charge",
                "meal_charge",
                "cancellation_charge",
                "total_amount",
                "is_immutable",
            )
            if old.is_immutable and any(getattr(old, f) != getattr(self, f) for f in protected):
                raise ValidationError("Generated bill amounts are immutable.")
            if old.is_settled_offline and any(
                getattr(old, f) != getattr(self, f)
                for f in ("is_settled_offline", "settlement_date", "remarks")
            ):
                raise ValidationError("Recorded settlement is immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        from django.core.exceptions import ValidationError

        raise ValidationError("Billing records cannot be deleted.")


class InventoryItem(TimeStampedModel):
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, blank=True)
    quantity = models.IntegerField(default=0)
    minimum_threshold = models.IntegerField(default=5)

    class Meta:
        db_table = "vh_inventory_item"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gte=0), name="vh_stock_nonnegative"
            ),
            models.CheckConstraint(
                condition=models.Q(minimum_threshold__gte=0), name="vh_threshold_nonnegative"
            ),
        ]

    def __str__(self):
        return f"{self.name} (Qty: {self.quantity}, Min: {self.minimum_threshold})"

    def is_below_threshold(self):
        return self.quantity < self.minimum_threshold


class InventoryReplenishment(TimeStampedModel):
    STATUS_CHOICES = [
        ("pending", "Pending In-Charge Approval"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="replenishments")
    requested_quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "vh_inventory_replenishment"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(requested_quantity__gte=1), name="vh_replenish_positive"
            )
        ]

    def __str__(self):
        return f"Replenishment #{self.pk}: {self.status}"


class AuditEvent(models.Model):
    actor_id = models.PositiveBigIntegerField()
    action = models.CharField(max_length=64)
    booking = models.ForeignKey(
        BookingRequest, null=True, on_delete=models.PROTECT, related_name="audit_events"
    )
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} by {self.actor_id}"


class Notification(models.Model):
    """Durable notification outbox; delivery infrastructure consumes these events."""

    key = models.CharField(max_length=180, unique=True)
    event = models.CharField(max_length=64)
    booking = models.ForeignKey(BookingRequest, null=True, on_delete=models.PROTECT)
    recipient_role = models.CharField(max_length=32, blank=True)
    recipient_id = models.PositiveBigIntegerField(null=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.CharField(max_length=200, blank=True)
    next_attempt_at = models.DateTimeField(default=timezone.now)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.key


class RoleAssignment(models.Model):
    """One current appointment per operational role, configured by platform operators."""

    role = models.CharField(
        max_length=32,
        unique=True,
        choices=[("vh_caretaker", "Caretaker"), ("vh_in_charge", "In-Charge")],
    )
    user_id = models.PositiveBigIntegerField()
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    email = models.EmailField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_at__gt=models.F("starts_at")), name="vh_role_interval_valid"
            )
        ]

    def __str__(self):
        return f"{self.role}: {self.user_id}"
