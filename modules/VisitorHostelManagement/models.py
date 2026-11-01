"""Database models for Visitor Hostel Management System (VHMS)."""
from django.db import models
from core.db.mixins import TimeStampedModel


class RoleAssignment(TimeStampedModel):
    role = models.CharField(max_length=20, choices=[("caretaker", "Caretaker"), ("incharge", "VH In-Charge")])
    user_id = models.IntegerField(db_index=True)
    is_active = models.BooleanField(default=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    class Meta: db_table = "vh_role_assignment"


class VisitorCategory(TimeStampedModel):
    category = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    class Meta: db_table = "vh_visitor_category"


class Tariff(TimeStampedModel):
    category = models.CharField(max_length=10)
    room_type = models.CharField(max_length=20)
    rate_per_day = models.DecimalField(max_digits=10, decimal_places=2)
    effective_from = models.DateField()
    class Meta:
        db_table = "vh_tariff"
        indexes = [models.Index(fields=["category", "room_type", "effective_from"])]


class Room(TimeStampedModel):
    room_number = models.CharField(max_length=20, unique=True)
    room_type = models.CharField(max_length=20, default="single")
    status = models.CharField(max_length=20, default="available")
    class Meta: db_table = "vh_room"


class Booking(TimeStampedModel):
    BILLING_CHOICES = [("visitor", "Visitor"), ("indenter", "Indenter"), ("institute", "Institute"), ("project", "Project")]
    STATUS_CHOICES = [
        ("pending", "Pending"), ("forwarded", "Forwarded"), ("approved", "Approved"),
        ("rejected", "Rejected"), ("cancelled", "Cancelled"), ("checked_in", "Checked In"),
        ("checked_out", "Checked Out"), ("no_show", "No Show"),
    ]
    indenter_id = models.IntegerField(db_index=True)
    visitor_name = models.CharField(max_length=120)
    visitor_email = models.CharField(max_length=120, blank=True)
    visitor_phone = models.CharField(max_length=20, blank=True)
    visitor_category = models.CharField(max_length=10, default="A")
    purpose = models.TextField(blank=True)
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    number_of_rooms = models.IntegerField(default=1)
    number_of_occupants = models.IntegerField(default=1)
    billing_responsibility = models.CharField(max_length=20, choices=BILLING_CHOICES, default="visitor")
    is_offline = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    caretaker_remarks = models.TextField(blank=True)
    incharge_remarks = models.TextField(blank=True)
    cancellation_reason = models.TextField(blank=True)
    cancellation_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    assigned_caretaker_id = models.IntegerField(null=True, blank=True)
    assigned_incharge_id = models.IntegerField(null=True, blank=True)
    actual_check_in = models.DateTimeField(null=True, blank=True)
    actual_check_out = models.DateTimeField(null=True, blank=True)
    rooms = models.ManyToManyField(Room, blank=True, related_name="bookings")
    class Meta:
        db_table = "vh_booking"
        indexes = [models.Index(fields=["status", "check_in_date"])]


class MealBooking(TimeStampedModel):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="meals")
    meal_date = models.DateField()
    meal_type = models.CharField(max_length=20)
    add_on = models.CharField(max_length=20, default="none")
    cost = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    class Meta: db_table = "vh_meal_booking"


class Bill(TimeStampedModel):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="bill")
    room_rent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    meal_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cancellation_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    billing_responsibility = models.CharField(max_length=20)
    is_settled = models.BooleanField(default=False)
    settlement_mode = models.CharField(max_length=20, default="cash")
    settled_at = models.DateTimeField(null=True, blank=True)
    verified_by_guest = models.BooleanField(default=False)
    is_immutable = models.BooleanField(default=False)
    class Meta: db_table = "vh_bill"


class InventoryItem(TimeStampedModel):
    item_name = models.CharField(max_length=120)
    category = models.CharField(max_length=50, default="consumables")
    quantity = models.IntegerField(default=0)
    min_threshold = models.IntegerField(default=10)
    replenishment_requested = models.BooleanField(default=False)
    replenishment_approved = models.BooleanField(default=False)
    replenishment_qty = models.IntegerField(default=0)
    class Meta: db_table = "vh_inventory_item"


class Notification(TimeStampedModel):
    recipient_email = models.CharField(max_length=120)
    recipient_user_id = models.IntegerField(null=True, blank=True)
    event_type = models.CharField(max_length=50)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    class Meta: db_table = "vh_notification"
