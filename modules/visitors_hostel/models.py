"""VHMS-owned tables. IAM identities cross this boundary as integer ids only."""
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class Building(TimeStampedModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "vh_building"
        ordering = ["name"]


class RoomType(TimeStampedModel):
    ROOM_KIND = [("suite", "Suite"), ("non_suite", "Non-suite")]
    name = models.CharField(max_length=60, unique=True)
    room_kind = models.CharField(max_length=12, choices=ROOM_KIND)
    max_occupancy = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "vh_room_type"


class Room(TimeStampedModel):
    STATUS = [("available", "Available"), ("maintenance", "Maintenance"),
              ("blocked", "Blocked")]
    building = models.ForeignKey(Building, on_delete=models.PROTECT,
                                 related_name="rooms")
    room_number = models.CharField(max_length=20)
    room_type = models.ForeignKey(RoomType, on_delete=models.PROTECT,
                                  related_name="rooms")
    occupancy = models.CharField(max_length=8,
                                 choices=[("single", "Single"), ("double", "Double")])
    status = models.CharField(max_length=12, choices=STATUS, default="available")
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "vh_room"
        constraints = [models.UniqueConstraint(fields=["building", "room_number"],
                                                name="vh_room_number_unique")]
        indexes = [models.Index(fields=["status", "occupancy"], name="vh_room_status_idx")]


class Booking(TimeStampedModel):
    SOURCE = [("online", "Online"), ("offline", "Offline")]
    STATUS = [(v, v.replace("_", " ").title()) for v in (
        "pending", "forwarded", "approved", "rejected", "cancellation_requested",
        "cancelled", "room_allotted", "checked_in", "checked_out")]
    CATEGORY = [(v, v) for v in ("A", "B", "C", "D")]
    BILLING = [(v, v) for v in ("Visitor", "Indenter", "Institute", "Project")]

    booking_number = models.CharField(max_length=24, unique=True, db_index=True)
    source = models.CharField(max_length=8, choices=SOURCE, default="online")
    status = models.CharField(max_length=24, choices=STATUS, default="pending", db_index=True)
    indenter_user_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    created_by_user_id = models.PositiveBigIntegerField(db_index=True)
    visitor_name = models.CharField(max_length=160)
    visitor_email = models.EmailField(blank=True)
    visitor_phone = models.CharField(max_length=30)
    visitor_organization = models.CharField(max_length=160, blank=True)
    purpose = models.CharField(max_length=500)
    visitor_category = models.CharField(max_length=1, choices=CATEGORY)
    arrival_date = models.DateField(db_index=True)
    departure_date = models.DateField()
    arrival_time = models.TimeField(null=True, blank=True)
    departure_time = models.TimeField(null=True, blank=True)
    room_count = models.PositiveSmallIntegerField(default=1)
    occupant_count = models.PositiveSmallIntegerField(default=1)
    requested_occupancy = models.CharField(max_length=8,
        choices=[("single", "Single"), ("double", "Double")])
    requested_room_kind = models.CharField(max_length=12,
        choices=[("suite", "Suite"), ("non_suite", "Non-suite")])
    billing_responsibility = models.CharField(max_length=12, choices=BILLING)
    department_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    project_reference = models.CharField(max_length=80, blank=True)
    decision_note = models.CharField(max_length=500, blank=True)
    cancellation_charge = models.DecimalField(max_digits=12, decimal_places=2,
                                               default=0)
    cancellation_requested_at = models.DateTimeField(null=True, blank=True)
    cancellation_confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "vh_booking"
        indexes = [models.Index(fields=["indenter_user_id", "-created_at"],
                                name="vh_booking_owner_idx"),
                   models.Index(fields=["status", "arrival_date"],
                                name="vh_booking_status_idx")]


class BookingTransition(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT,
                                related_name="transitions")
    from_status = models.CharField(max_length=24)
    to_status = models.CharField(max_length=24)
    actor_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=40)
    reason = models.CharField(max_length=500, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vh_booking_transition"
        ordering = ["occurred_at", "pk"]
        indexes = [models.Index(fields=["booking", "occurred_at"],
                                name="vh_transition_hist_idx")]


class BookingChangeRequest(TimeStampedModel):
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT,
                                related_name="change_requests")
    requested_by_user_id = models.PositiveBigIntegerField()
    requested_changes = models.JSONField(default=dict)
    status = models.CharField(max_length=12, default="pending",
                              choices=[("pending", "Pending"),
                                       ("confirmed", "Confirmed"),
                                       ("declined", "Declined")])

    class Meta:
        db_table = "vh_booking_change_request"


class RoomAllocation(TimeStampedModel):
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT,
                                related_name="allocations")
    room = models.ForeignKey(Room, on_delete=models.PROTECT,
                             related_name="allocations")
    arrival_date = models.DateField()
    departure_date = models.DateField()
    occupancy = models.CharField(max_length=8,
                                 choices=[("single", "Single"), ("double", "Double")])
    tariff_daily_snapshot = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "vh_room_allocation"
        indexes = [models.Index(fields=["room", "arrival_date", "departure_date"],
                                name="vh_alloc_dates_idx")]


class StayRecord(models.Model):
    allocation = models.OneToOneField(RoomAllocation, on_delete=models.PROTECT,
                                      related_name="stay")
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_in_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    checked_out_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    bill_verified = models.BooleanField(default=False)
    bill_verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "vh_stay_record"


class StayAlert(models.Model):
    KIND = [("no_show", "No-show"), ("overstay", "Overstay")]
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT,
                                related_name="stay_alerts")
    kind = models.CharField(max_length=10, choices=KIND)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vh_stay_alert"
        constraints = [models.UniqueConstraint(fields=["booking", "kind"],
                                                name="vh_stay_alert_once")]


class Tariff(TimeStampedModel):
    CATEGORY = [(v, v) for v in ("A", "B", "C", "D")]
    occupancy = models.CharField(max_length=8,
                                 choices=[("single", "Single"), ("double", "Double")])
    visitor_category = models.CharField(max_length=1, choices=CATEGORY)
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2)
    effective_from = models.DateField(db_index=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "vh_tariff"
        constraints = [models.UniqueConstraint(
            fields=["occupancy", "visitor_category", "effective_from"],
            name="vh_tariff_effective_unique")]


class MealBooking(TimeStampedModel):
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT,
                                related_name="meal_bookings")
    meal_date = models.DateField()
    options = models.JSONField(default=list)
    add_ons = models.JSONField(default=list)
    quantity = models.PositiveSmallIntegerField(default=1)
    unit_rate = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        db_table = "vh_meal_booking"


class MealRate(TimeStampedModel):
    OPTION = [(v, v) for v in ("Full day", "Breakfast", "Lunch", "Dinner", "Tea", "Milk")]
    option = models.CharField(max_length=16, choices=OPTION)
    rate = models.DecimalField(max_digits=8, decimal_places=2)
    effective_from = models.DateField(db_index=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "vh_meal_rate"
        constraints = [models.UniqueConstraint(fields=["option", "effective_from"],
                                                name="vh_meal_rate_effective_unique")]


class Bill(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name="bills")
    bill_number = models.CharField(max_length=24, unique=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    currency = models.CharField(max_length=3, default="INR")
    tariff_snapshot = models.JSONField(default=dict)
    line_items = models.JSONField(default=list)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    billing_responsibility = models.CharField(max_length=12, choices=Booking.BILLING)
    verified_at_checkout = models.BooleanField(default=False)

    class Meta:
        db_table = "vh_bill"
        ordering = ["-generated_at"]


class CashSettlement(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.PROTECT, related_name="settlements")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    received_at = models.DateTimeField(auto_now_add=True)
    received_by_user_id = models.PositiveBigIntegerField()
    reference_note = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "vh_cash_settlement"


class InventoryItem(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    current_quantity = models.DecimalField(max_digits=12, decimal_places=2)
    minimum_threshold = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.CharField(max_length=24)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "vh_inventory_item"


class InventoryChange(models.Model):
    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT,
                             related_name="changes")
    quantity_delta = models.DecimalField(max_digits=12, decimal_places=2)
    quantity_after = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.CharField(max_length=300, blank=True)
    actor_user_id = models.PositiveBigIntegerField()
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vh_inventory_change"


class ReplenishmentRequest(TimeStampedModel):
    STATUS = [("pending", "Pending"), ("approved", "Approved"),
              ("rejected", "Rejected")]
    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT,
                             related_name="replenishment_requests")
    requested_quantity = models.DecimalField(max_digits=12, decimal_places=2)
    requested_by_user_id = models.PositiveBigIntegerField()
    status = models.CharField(max_length=10, choices=STATUS, default="pending")
    reviewed_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "vh_replenishment_request"


class NotificationOutbox(models.Model):
    STATUS = [("pending", "Pending"), ("sent", "Sent"), ("failed", "Failed")]
    topic = models.CharField(max_length=60)
    dedupe_key = models.CharField(max_length=200, unique=True)
    recipient_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    recipient_email = models.EmailField(blank=True)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=8, choices=STATUS, default="pending")
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=300, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vh_notification_outbox"
        indexes = [models.Index(fields=["status", "created_at"],
                                name="vh_notify_pending_idx")]


class OperationalRoleAssignment(TimeStampedModel):
    ROLE = [("caretaker", "Caretaker"), ("vh_in_charge", "VH In-Charge")]
    role = models.CharField(max_length=16, choices=ROLE)
    user_id = models.PositiveBigIntegerField(db_index=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "vh_role_assignment"
        constraints = [models.UniqueConstraint(
            fields=["role"], condition=Q(ends_at__isnull=True),
            name="vh_one_open_assignment")]
