"""Visitors Hostel (VH) database models.

All user references are stored as plain integer IDs (no cross-module FKs).
"""
import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.db.mixins import TimeStampedModel


class VisitorCategory(TimeStampedModel):
    """Institute visitor categories (A, B, C, D) per BR-VH-019."""

    CATEGORY_A = "A"
    CATEGORY_B = "B"
    CATEGORY_C = "C"
    CATEGORY_D = "D"
    CATEGORY_CHOICES = [
        (CATEGORY_A, "Category A - Institute Guests / Official"),
        (CATEGORY_B, "Category B - Invited Academic / Research Visitors"),
        (CATEGORY_C, "Category C - Students / Alumni Guests"),
        (CATEGORY_D, "Category D - Others / Personal"),
    ]

    code = models.CharField(max_length=10, unique=True, choices=CATEGORY_CHOICES)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "vh_visitor_category"
        verbose_name_plural = "Visitor Categories"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class RoomType(models.TextChoices):
    SUITE = "SUITE", "Suite"
    NON_SUITE = "NON_SUITE", "Non-Suite"


class OccupancyType(models.TextChoices):
    SINGLE = "SINGLE", "Single"
    DOUBLE = "DOUBLE", "Double"


class RoomStatus(models.TextChoices):
    AVAILABLE = "AVAILABLE", "Available"
    OCCUPIED = "OCCUPIED", "Occupied"
    MAINTENANCE = "MAINTENANCE", "Under Maintenance"


class Room(TimeStampedModel):
    """Hostel room definition (BR-VH-013, 014, 015, 016)."""

    room_number = models.CharField(max_length=20, unique=True, db_index=True)
    room_type = models.CharField(
        max_length=20,
        choices=RoomType.choices,
        default=RoomType.NON_SUITE,
    )
    occupancy_type = models.CharField(
        max_length=20,
        choices=OccupancyType.choices,
        default=OccupancyType.DOUBLE,
    )
    floor = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(
        max_length=20,
        choices=RoomStatus.choices,
        default=RoomStatus.AVAILABLE,
    )

    class Meta:
        db_table = "vh_room"
        ordering = ["room_number"]

    def __str__(self) -> str:
        return f"Room {self.room_number} ({self.get_room_type_display()}, {self.status})"


class Tariff(TimeStampedModel):
    """Category-specific and occupancy-specific tariff (BR-VH-023, 024, AFR-VH-046..048)."""

    category = models.ForeignKey(
        VisitorCategory,
        on_delete=models.CASCADE,
        related_name="tariffs",
    )
    room_type = models.CharField(max_length=20, choices=RoomType.choices)
    occupancy_type = models.CharField(max_length=20, choices=OccupancyType.choices)
    rate_per_day = models.DecimalField(max_digits=8, decimal_places=2)
    effective_from = models.DateField(default=timezone.now)

    class Meta:
        db_table = "vh_tariff"
        unique_together = ("category", "room_type", "occupancy_type", "effective_from")
        ordering = ["-effective_from", "category"]

    def __str__(self) -> str:
        return (
            f"Tariff {self.category.code} {self.room_type}/{self.occupancy_type}: "
            f"{self.rate_per_day}/day"
        )


class BillingResponsibility(models.TextChoices):
    VISITOR = "VISITOR", "Visitor"
    INDENTER = "INDENTER", "Indenter"
    INSTITUTE = "INSTITUTE", "Institute"
    PROJECT = "PROJECT", "Project"


class BookingStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    FORWARDED = "FORWARDED", "Forwarded to In-Charge"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    ROOM_ALLOTTED = "ROOM_ALLOTTED", "Room Allotted"
    CHECKED_IN = "CHECKED_IN", "Checked In"
    CHECKED_OUT = "CHECKED_OUT", "Checked Out"
    CANCELLATION_REQUESTED = "CANCELLATION_REQUESTED", "Cancellation Requested"
    CANCELLED = "CANCELLED", "Cancelled"


class OfflineBookingType(models.TextChoices):
    TELEPHONIC = "TELEPHONIC", "Telephonic"
    WALK_IN = "WALK_IN", "Walk-in"


def generate_booking_reference() -> str:
    return f"VH-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


class Booking(TimeStampedModel):
    """Visitor hostel booking requisition (online and offline) per CFR-VH-002, CFR-VH-004."""

    booking_reference = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        default=generate_booking_reference,
    )
    indenter_id = models.IntegerField(db_index=True)
    indenter_type = models.CharField(max_length=50, blank=True)

    is_offline = models.BooleanField(default=False)
    offline_booking_type = models.CharField(
        max_length=20,
        blank=True,
        choices=OfflineBookingType.choices,
    )

    visitor_name = models.CharField(max_length=150)
    visitor_email = models.EmailField(blank=True)
    visitor_phone = models.CharField(max_length=20, blank=True)
    visitor_address = models.TextField(blank=True)
    visitor_category = models.ForeignKey(
        VisitorCategory,
        on_delete=models.PROTECT,
        related_name="bookings",
    )
    visit_purpose = models.TextField()

    check_in_date = models.DateField()
    check_out_date = models.DateField()
    number_of_rooms = models.PositiveSmallIntegerField(default=1)
    number_of_occupants = models.PositiveSmallIntegerField(default=1)

    billing_responsibility = models.CharField(
        max_length=20,
        choices=BillingResponsibility.choices,
        default=BillingResponsibility.VISITOR,
    )
    status = models.CharField(
        max_length=30,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING,
        db_index=True,
    )

    assigned_caretaker_id = models.IntegerField(null=True, blank=True, db_index=True)
    assigned_incharge_id = models.IntegerField(null=True, blank=True, db_index=True)

    caretaker_remarks = models.TextField(blank=True)
    incharge_remarks = models.TextField(blank=True)
    cancellation_reason = models.TextField(blank=True)
    calculated_cancellation_charge = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )

    class Meta:
        db_table = "vh_booking"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.booking_reference} - {self.visitor_name} ({self.status})"


class RoomAllotment(TimeStampedModel):
    """Assignment of room to an approved booking (BR-VH-012, AFR-VH-036)."""

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="allotments",
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        related_name="allotments",
    )
    allotted_at = models.DateTimeField(auto_now_add=True)
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    is_no_show = models.BooleanField(default=False)
    is_overstay = models.BooleanField(default=False)

    class Meta:
        db_table = "vh_room_allotment"
        ordering = ["-allotted_at"]

    def __str__(self) -> str:
        return f"Allotment {self.room.room_number} for {self.booking.booking_reference}"


class MealType(models.TextChoices):
    BREAKFAST = "BREAKFAST", "Breakfast"
    LUNCH = "LUNCH", "Lunch"
    DINNER = "DINNER", "Dinner"
    FULL_DAY = "FULL_DAY", "Full Day"


class MealAddOn(models.TextChoices):
    NONE = "NONE", "None"
    TEA = "TEA", "Tea"
    MILK = "MILK", "Milk"


class MealBooking(TimeStampedModel):
    """Meal reservations for residing guests (BR-VH-025, 029, 030, CFR-VH-010)."""

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="meal_bookings",
    )
    date = models.DateField()
    meal_type = models.CharField(max_length=20, choices=MealType.choices)
    add_on = models.CharField(
        max_length=20,
        choices=MealAddOn.choices,
        default=MealAddOn.NONE,
    )
    number_of_persons = models.PositiveSmallIntegerField(default=1)
    rate = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0.00")
    )
    total_amount = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0.00")
    )

    class Meta:
        db_table = "vh_meal_booking"
        ordering = ["-date"]

    def __str__(self) -> str:
        return f"Meal for {self.booking.booking_reference}: {self.meal_type} on {self.date}"


class PaymentMode(models.TextChoices):
    CASH = "CASH", "Cash"


class Bill(TimeStampedModel):
    """Bill and offline cash settlement record (BR-VH-033..037, CFR-VH-011)."""

    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name="bill",
    )
    room_charges = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    meal_charges = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    cancellation_charges = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    payment_mode = models.CharField(
        max_length=20,
        choices=PaymentMode.choices,
        default=PaymentMode.CASH,
    )
    is_settled = models.BooleanField(default=False)
    settled_at = models.DateTimeField(null=True, blank=True)
    is_finalized = models.BooleanField(default=False)
    guest_verification_notes = models.TextField(blank=True)

    class Meta:
        db_table = "vh_bill"

    def clean(self):
        if self.pk:
            orig = Bill.objects.filter(pk=self.pk).first()
            if orig and orig.is_finalized and not self.is_finalized:
                raise ValidationError("Finalized bills cannot be unfinalized (BR-VH-037).")

    def save(self, *args, **kwargs):
        if self.pk:
            orig = Bill.objects.filter(pk=self.pk).first()
            if orig and orig.is_finalized:
                # Financial values cannot be mutated once finalized
                if (
                    self.room_charges != orig.room_charges
                    or self.meal_charges != orig.meal_charges
                    or self.cancellation_charges != orig.cancellation_charges
                    or self.total_amount != orig.total_amount
                ):
                    raise ValidationError("Finalized bills are immutable for audit (BR-VH-037).")
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return (
            f"Bill for {self.booking.booking_reference}: Rs {self.total_amount} "
            f"(settled={self.is_settled}, finalized={self.is_finalized})"
        )


class InventoryCategory(models.TextChoices):
    LINEN = "LINEN", "Linen"
    UTENSILS = "UTENSILS", "Utensils"
    CONSUMABLES = "CONSUMABLES", "Consumables"
    OTHERS = "OTHERS", "Others"


class InventoryItem(TimeStampedModel):
    """Inventory item tracking with threshold alert support (CFR-VH-012, BR-VH-041)."""

    name = models.CharField(max_length=150, unique=True)
    category = models.CharField(
        max_length=50,
        choices=InventoryCategory.choices,
        default=InventoryCategory.CONSUMABLES,
    )
    current_quantity = models.PositiveIntegerField(default=0)
    minimum_threshold = models.PositiveIntegerField(default=10)

    class Meta:
        db_table = "vh_inventory_item"
        ordering = ["name"]

    @property
    def is_below_threshold(self) -> bool:
        return self.current_quantity < self.minimum_threshold

    def __str__(self) -> str:
        return f"{self.name} (Qty: {self.current_quantity}, Min: {self.minimum_threshold})"


class ReplenishmentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"


class InventoryReplenishment(TimeStampedModel):
    """Replenishment requests reviewed by VH In-Charge (CFR-VH-013)."""

    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name="replenishments",
    )
    quantity_requested = models.PositiveIntegerField()
    requested_by_user_id = models.IntegerField()
    status = models.CharField(
        max_length=20,
        choices=ReplenishmentStatus.choices,
        default=ReplenishmentStatus.PENDING,
    )
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "vh_inventory_replenishment"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Replenish {self.item.name} x {self.quantity_requested} ({self.status})"


class VHMSUserRoleType(models.TextChoices):
    CARETAKER = "CARETAKER", "Caretaker"
    IN_CHARGE = "IN_CHARGE", "VH In-Charge"


class VHMSUserRole(TimeStampedModel):
    """Role assignment for Caretaker and VH In-Charge (BR-VH-045..050, UC-VH-019)."""

    role_type = models.CharField(max_length=20, choices=VHMSUserRoleType.choices)
    user_id = models.IntegerField(db_index=True)
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "vh_user_role"
        ordering = ["-start_date"]

    def __str__(self) -> str:
        return f"{self.get_role_type_display()} - User {self.user_id} (active={self.is_active})"

    @classmethod
    def get_active_caretaker(cls) -> "VHMSUserRole | None":
        return cls.objects.filter(role_type=VHMSUserRoleType.CARETAKER, is_active=True).first()

    @classmethod
    def get_active_incharge(cls) -> "VHMSUserRole | None":
        return cls.objects.filter(role_type=VHMSUserRoleType.IN_CHARGE, is_active=True).first()

    @classmethod
    def reassign_role(
        cls,
        role_type: str,
        user_id: int,
        start_date=None,
        end_date=None,
    ) -> "VHMSUserRole":
        """Reassign operational role immediately and transfer records (BR-VH-045..050, UC-VH-019)."""
        start = start_date or timezone.localdate()
        # Deactivate current active role immediately (BR-VH-045, BR-VH-046, BR-VH-048)
        cls.objects.filter(role_type=role_type, is_active=True).update(
            is_active=False,
            end_date=start,
        )

        new_role = cls.objects.create(
            role_type=role_type,
            user_id=user_id,
            start_date=start,
            end_date=end_date,
            is_active=True,
        )

        # Transfer pending and ongoing records to the newly assigned role holder (BR-VH-049, BR-VH-050)
        if role_type == VHMSUserRoleType.CARETAKER:
            Booking.objects.filter(
                status__in=[
                    BookingStatus.PENDING,
                    BookingStatus.ROOM_ALLOTTED,
                    BookingStatus.CHECKED_IN,
                    BookingStatus.CANCELLATION_REQUESTED,
                ]
            ).update(assigned_caretaker_id=user_id)
        elif role_type == VHMSUserRoleType.IN_CHARGE:
            Booking.objects.filter(
                status__in=[
                    BookingStatus.FORWARDED,
                    BookingStatus.APPROVED,
                ]
            ).update(assigned_incharge_id=user_id)

        return new_role


class ModificationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    CONFIRMED = "CONFIRMED", "Confirmed"
    REJECTED = "REJECTED", "Rejected"


class BookingModification(TimeStampedModel):
    """Booking modification requests and confirmed outcomes (UC-VH-006, UC-VH-022, BR-VH-010)."""

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="modifications",
    )
    requested_by_user_id = models.IntegerField()
    new_check_in_date = models.DateField(null=True, blank=True)
    new_check_out_date = models.DateField(null=True, blank=True)
    new_number_of_rooms = models.PositiveSmallIntegerField(null=True, blank=True)
    new_number_of_occupants = models.PositiveSmallIntegerField(null=True, blank=True)
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=ModificationStatus.choices,
        default=ModificationStatus.PENDING,
    )
    confirmed_by_user_id = models.IntegerField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "vh_booking_modification"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Modification for {self.booking.booking_reference} ({self.status})"


class VHAlertType(models.TextChoices):
    NO_SHOW = "NO_SHOW", "No-Show Alert"
    OVERSTAY = "OVERSTAY", "Overstay Alert"
    INVENTORY_THRESHOLD = "INVENTORY_THRESHOLD", "Inventory Below Threshold"
    STAY_REMINDER = "STAY_REMINDER", "Stay Reminder"


class VHAlert(TimeStampedModel):
    """Operational exception alerts and reminders (BR-VH-017, BR-VH-018, BR-VH-041, UC-VH-024, UC-VH-025)."""

    alert_type = models.CharField(max_length=30, choices=VHAlertType.choices)
    booking = models.ForeignKey(
        Booking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alerts",
    )
    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alerts",
    )
    message = models.TextField()
    recipient_role = models.CharField(
        max_length=20,
        choices=VHMSUserRoleType.choices,
        default=VHMSUserRoleType.CARETAKER,
    )
    recipient_user_id = models.IntegerField(null=True, blank=True)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "vh_alert"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Alert [{self.alert_type}]: {self.message[:50]}"


class VHNotificationEventType(models.TextChoices):
    BOOKING_SUBMITTED = "BOOKING_SUBMITTED", "Booking Submitted"
    BOOKING_FORWARDED = "BOOKING_FORWARDED", "Booking Forwarded"
    BOOKING_APPROVED = "BOOKING_APPROVED", "Booking Approved"
    BOOKING_REJECTED = "BOOKING_REJECTED", "Booking Rejected"
    CANCELLATION_REQUESTED = "CANCELLATION_REQUESTED", "Cancellation Requested"
    BOOKING_CANCELLED = "BOOKING_CANCELLED", "Booking Cancelled"
    MODIFICATION_REQUESTED = "MODIFICATION_REQUESTED", "Modification Requested"
    MODIFICATION_CONFIRMED = "MODIFICATION_CONFIRMED", "Modification Confirmed"
    INVENTORY_THRESHOLD = "INVENTORY_THRESHOLD", "Inventory Below Threshold Email"


class VHNotificationLog(TimeStampedModel):
    """System-generated email notification audit trail (UC-VH-023, UC-VH-025, CFR-VH-014, BR-VH-043)."""

    event_type = models.CharField(max_length=35, choices=VHNotificationEventType.choices)
    booking = models.ForeignKey(
        Booking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notification_logs",
    )
    recipient_email = models.EmailField(blank=True)
    recipient_user_id = models.IntegerField(null=True, blank=True)
    subject = models.CharField(max_length=255)
    body = models.TextField()

    class Meta:
        db_table = "vh_notification_log"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Notification [{self.event_type}] to {self.recipient_email or self.recipient_user_id}"
