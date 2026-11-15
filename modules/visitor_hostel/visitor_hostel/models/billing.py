"""Meals and bills. A bill's amounts are written once (BR-VH-037)."""
from django.db import models
from django.db.models import F, Q

from modules.visitor_hostel.domain import billing, meals


class MealBooking(models.Model):
    KIND = [(meals.FULL_DAY, "Full day"), (meals.INDIVIDUAL, "Individual meal"),
            (meals.ADD_ON, "Add-on")]

    booking = models.ForeignKey("Booking", on_delete=models.CASCADE,
                                related_name="meals")
    meal_date = models.DateField()
    kind = models.CharField(max_length=10, choices=KIND)
    item = models.CharField(max_length=10, blank=True)
    quantity = models.PositiveSmallIntegerField(default=1)
    recorded_by_user_id = models.IntegerField()
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vh_meal_booking"
        constraints = [
            models.CheckConstraint(
                condition=(Q(kind=meals.FULL_DAY, item="")
                           | Q(kind=meals.INDIVIDUAL, item__in=meals.INDIVIDUAL_ITEMS)
                           | Q(kind=meals.ADD_ON, item__in=meals.ADD_ON_ITEMS)),
                name="vh_meal_kind_item_valid"),
            models.CheckConstraint(condition=Q(quantity__gte=1),
                                   name="vh_meal_quantity_positive"),
        ]
        indexes = [models.Index(fields=["booking", "meal_date"], name="vh_meal_idx")]

    def __str__(self) -> str:
        return f"booking#{self.booking_id} {self.kind}:{self.item} {self.meal_date}"


class Bill(models.Model):
    STATUS = [("generated", "Generated"), ("settled", "Settled")]
    SETTLEMENT_MODE = [("cash", "Cash (offline)")]             # BR-VH-036

    booking = models.OneToOneField("Booking", on_delete=models.PROTECT,
                                   related_name="bill")
    billing_responsibility = models.CharField(max_length=10)
    billing_reference = models.CharField(max_length=120, blank=True)
    room_amount = models.DecimalField(max_digits=12, decimal_places=2)
    meal_amount = models.DecimalField(max_digits=12, decimal_places=2)
    cancellation_amount = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    generated_by_user_id = models.IntegerField()
    generated_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(max_length=10, choices=STATUS, default="generated")
    settlement_mode = models.CharField(max_length=8, choices=SETTLEMENT_MODE,
                                       blank=True)
    settled_amount = models.DecimalField(max_digits=12, decimal_places=2,
                                         null=True, blank=True)
    receipt_reference = models.CharField(max_length=60, blank=True)
    settled_by_user_id = models.IntegerField(null=True, blank=True)
    settled_at = models.DateTimeField(null=True, blank=True)

    # The guest checks the bill at the desk; the Caretaker records it (AFR-VH-065).
    guest_verified = models.BooleanField(default=False)
    verification_note = models.CharField(max_length=300, blank=True)
    verified_by_user_id = models.IntegerField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "vh_bill"
        constraints = [
            models.CheckConstraint(
                condition=Q(total=F("room_amount") + F("meal_amount")
                            + F("cancellation_amount")),
                name="vh_bill_total_is_sum"),
            models.CheckConstraint(
                condition=Q(room_amount__gte=0) & Q(meal_amount__gte=0)
                & Q(cancellation_amount__gte=0),
                name="vh_bill_amounts_non_negative"),
            models.CheckConstraint(
                condition=~Q(status="settled")
                | (Q(settled_at__isnull=False) & Q(settlement_mode="cash")
                   & Q(settled_amount=F("total"))),
                name="vh_bill_settled_is_complete_cash"),
            models.CheckConstraint(
                condition=Q(guest_verified=False) | Q(verified_at__isnull=False),
                name="vh_bill_verified_has_time"),
        ]
        indexes = [models.Index(fields=["status", "generated_at"], name="vh_bill_idx")]

    def __str__(self) -> str:
        return f"bill#{self.pk} booking#{self.booking_id} {self.total}"


class BillLine(models.Model):
    KIND = [(billing.ROOM, "Room rent"), (billing.MEAL, "Meals"),
            (billing.CANCELLATION, "Cancellation / no-show charge")]

    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="lines")
    kind = models.CharField(max_length=14, choices=KIND)
    description = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    unit_rate = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    # The tariff row the rate was copied from; the rate itself is the record.
    tariff_ref = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "vh_bill_line"
        constraints = [
            models.CheckConstraint(condition=Q(kind__in=billing.LINE_KINDS),
                                   name="vh_bill_line_kind_valid"),
        ]

    def __str__(self) -> str:
        return f"bill#{self.bill_id} {self.kind} {self.amount}"
