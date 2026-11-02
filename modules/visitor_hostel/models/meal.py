from django.db import models
from decimal import Decimal
from .booking import BookingDetail

class MealBooking(models.Model):
    booking = models.ForeignKey(BookingDetail, on_delete=models.CASCADE, related_name="meal_bookings")
    date = models.DateField()
    breakfast = models.BooleanField(default=False)
    lunch = models.BooleanField(default=False)
    dinner = models.BooleanField(default=False)
    tea_count = models.PositiveIntegerField(default=0)
    milk_count = models.PositiveIntegerField(default=0)
    full_day = models.BooleanField(default=False)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    is_finalized = models.BooleanField(default=False)

    class Meta:
        db_table = "vh_meal_booking"
        unique_together = ('booking', 'date')
        ordering = ["date"]

    def __str__(self):
        return f"Meals {self.booking.booking_id} on {self.date}: {self.amount}"
