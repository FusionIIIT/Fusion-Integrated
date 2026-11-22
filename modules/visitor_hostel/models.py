from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class VisitorCategoryTariff(TimeStampedModel):
    CATEGORY_CHOICES = [
        ('A', 'Category A'),
        ('B', 'Category B'),
        ('C', 'Category C'),
        ('D', 'Category D'),
    ]
    ROOM_TYPE_CHOICES = [
        ('suite', 'Suite'),
        ('non_suite', 'Non-Suite'),
    ]
    OCCUPANCY_CHOICES = [
        ('single', 'Single'),
        ('double', 'Double'),
    ]

    category = models.CharField(max_length=1, choices=CATEGORY_CHOICES)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPE_CHOICES)
    occupancy = models.CharField(max_length=20, choices=OCCUPANCY_CHOICES)
    daily_rate = models.DecimalField(max_digits=8, decimal_places=2)
    effective_from = models.DateField(default=timezone.now)

    class Meta:
        db_table = 'vh_tariff'
        ordering = ['-effective_from']

    def __str__(self):
        return f"Cat {self.category} - {self.room_type} ({self.occupancy}): {self.daily_rate}"


class Room(TimeStampedModel):
    ROOM_TYPE_CHOICES = [
        ('suite', 'Suite'),
        ('non_suite', 'Non-Suite'),
    ]
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('maintenance', 'Maintenance'),
    ]

    room_number = models.CharField(max_length=10, unique=True)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')

    class Meta:
        db_table = 'vh_room'

    def __str__(self):
        return f"Room {self.room_number} ({self.room_type})"


class BookingRequest(TimeStampedModel):
    STATUS_CHOICES = [
        ('pending', 'Pending Caretaker Review'),
        ('forwarded', 'Forwarded to In-Charge'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('cancelled', 'Cancelled'),
    ]
    BILLING_RESPONSIBILITY_CHOICES = [
        ('Visitor', 'Visitor'),
        ('Indenter', 'Indenter'),
        ('Institute', 'Institute'),
        ('Project', 'Project'),
    ]

    indenter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vh_bookings',
        null=True,
        blank=True
    )
    visitor_name = models.CharField(max_length=100)
    visitor_phone = models.CharField(max_length=20, blank=True)
    visitor_email = models.EmailField(blank=True)
    visitor_category = models.CharField(max_length=1, choices=VisitorCategoryTariff.CATEGORY_CHOICES)
    purpose = models.TextField()
    is_offline = models.BooleanField(default=False)

    check_in_date = models.DateField()
    check_out_date = models.DateField()
    number_of_rooms = models.PositiveIntegerField(default=1)
    occupancy = models.CharField(max_length=20, choices=VisitorCategoryTariff.OCCUPANCY_CHOICES, default='single')
    room_type = models.CharField(max_length=20, choices=VisitorCategoryTariff.ROOM_TYPE_CHOICES, default='non_suite')

    billing_responsibility = models.CharField(max_length=20, choices=BILLING_RESPONSIBILITY_CHOICES, default='Visitor')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'vh_booking_request'

    def __str__(self):
        return f"Booking #{self.id} - {self.visitor_name} ({self.status})"


class RoomAllotment(TimeStampedModel):
    booking = models.ForeignKey(BookingRequest, on_delete=models.CASCADE, related_name='allotments')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='allotments')
    actual_check_in = models.DateTimeField(null=True, blank=True)
    actual_check_out = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'vh_room_allotment'

    def __str__(self):
        return f"Allotment: Booking #{self.booking_id} -> Room {self.room.room_number}"


class MealBooking(TimeStampedModel):
    MEAL_CHOICES = [
        ('breakfast', 'Breakfast'),
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
        ('full_day', 'Full Day'),
        ('tea', 'Add-on: Tea'),
        ('milk', 'Add-on: Milk'),
    ]

    booking = models.ForeignKey(BookingRequest, on_delete=models.CASCADE, related_name='meal_bookings')
    date = models.DateField()
    meal_type = models.CharField(max_length=20, choices=MEAL_CHOICES)
    quantity = models.PositiveIntegerField(default=1)
    rate = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('50.00'))

    class Meta:
        db_table = 'vh_meal_booking'

    def __str__(self):
        return f"{self.meal_type} x{self.quantity} for Booking #{self.booking_id} on {self.date}"


class Bill(TimeStampedModel):
    booking = models.OneToOneField(BookingRequest, on_delete=models.CASCADE, related_name='bill')
    room_charge = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    meal_charge = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    cancellation_charge = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    is_settled_offline = models.BooleanField(default=False)
    settlement_date = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    is_immutable = models.BooleanField(default=False)

    class Meta:
        db_table = 'vh_bill'

    def __str__(self):
        return f"Bill #{self.id} for Booking #{self.booking_id} - Total: {self.total_amount}"


class InventoryItem(TimeStampedModel):
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, blank=True)
    quantity = models.IntegerField(default=0)
    minimum_threshold = models.IntegerField(default=5)

    class Meta:
        db_table = 'vh_inventory_item'

    def is_below_threshold(self):
        return self.quantity <= self.minimum_threshold

    def __str__(self):
        return f"{self.name} (Qty: {self.quantity}, Min: {self.minimum_threshold})"


class InventoryReplenishment(TimeStampedModel):
    STATUS_CHOICES = [
        ('pending', 'Pending In-Charge Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='replenishments')
    requested_quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = 'vh_inventory_replenishment'
