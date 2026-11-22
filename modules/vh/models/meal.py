# Meal booking model for VHMS guests.
from django.db import models
from django.db.models import CheckConstraint, Index, Q

from core.db.mixins import TimeStampedModel


class MealBooking(TimeStampedModel):
    # Records meals and add-ons ordered for guests during their stay.
    booking = models.ForeignKey(
        "vh.Booking",
        on_delete=models.CASCADE,
        related_name="meal_bookings",
    )
    meal_date = models.DateField(db_index=True)
    meal_option = models.CharField(
        max_length=20,
        choices=[("full_day", "Full-day"), ("individual", "Individual"), ("add_on", "Add-on")],
    )
    individual_type = models.CharField(
        max_length=20,
        blank=True,
        default="",
        choices=[("breakfast", "Breakfast"), ("lunch", "Lunch"), ("dinner", "Dinner")],
    )
    add_on_type = models.CharField(
        max_length=20,
        blank=True,
        default="",
        choices=[("tea", "Tea"), ("milk", "Milk")],
    )
    quantity = models.PositiveIntegerField(default=1)
    rate = models.DecimalField(max_digits=8, decimal_places=2)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "vh_meal_booking"
        indexes = [
            Index(fields=["booking", "meal_date"], name="vh_meal_bk_date_idx"),
        ]
        constraints = [
            CheckConstraint(
                condition=Q(quantity__gt=0),
                name="vh_meal_quantity_gt_zero",
            ),
            CheckConstraint(
                condition=Q(meal_option__in=["full_day", "individual", "add_on"]),
                name="vh_meal_valid_option",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.booking.booking_reference}: {self.meal_option} on {self.meal_date}"
