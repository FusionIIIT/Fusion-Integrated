"""Rooms, allotments and the effective-dated tariffs."""
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.visitor_hostel.domain import meals, tariffs


class Room(TimeStampedModel):
    ROOM_TYPE = [(tariffs.SUITE, "Suite"), (tariffs.NON_SUITE, "Non-suite")]

    number = models.CharField(max_length=16, unique=True)
    room_type = models.CharField(max_length=10, choices=ROOM_TYPE)
    floor = models.CharField(max_length=16, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "vh_room"
        ordering = ["number"]
        constraints = [
            models.CheckConstraint(condition=Q(room_type__in=tariffs.ROOM_TYPES),
                                   name="vh_room_type_valid"),
        ]

    def __str__(self) -> str:
        return self.number


class RoomAllotment(models.Model):
    OCCUPANCY = [(tariffs.SINGLE, "Single"), (tariffs.DOUBLE, "Double")]

    booking = models.ForeignKey("Booking", on_delete=models.CASCADE,
                                related_name="allotments")
    room = models.ForeignKey(Room, on_delete=models.PROTECT,
                             related_name="allotments")
    occupancy = models.CharField(max_length=8, choices=OCCUPANCY)
    allotted_by_user_id = models.IntegerField()
    allotted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vh_room_allotment"
        constraints = [
            models.UniqueConstraint(fields=["booking", "room"],
                                    name="vh_allotment_room_once_per_booking"),
            models.CheckConstraint(condition=Q(occupancy__in=tariffs.OCCUPANCIES),
                                   name="vh_allotment_occupancy_valid"),
        ]
        indexes = [models.Index(fields=["room"], name="vh_allotment_room_idx")]

    def __str__(self) -> str:
        return f"booking#{self.booking_id} room {self.room_id}"


class RoomTariff(TimeStampedModel):
    """Never edited: a new rate is a new row with a later effective_from."""

    category = models.CharField(max_length=1)
    occupancy = models.CharField(max_length=8)
    rate_per_day = models.DecimalField(max_digits=10, decimal_places=2)
    effective_from = models.DateField()
    created_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "vh_room_tariff"
        constraints = [
            models.UniqueConstraint(fields=["category", "occupancy", "effective_from"],
                                    name="vh_room_tariff_unique_version"),
            models.CheckConstraint(condition=Q(category__in=tariffs.CATEGORIES),
                                   name="vh_room_tariff_category_valid"),
            models.CheckConstraint(condition=Q(occupancy__in=tariffs.OCCUPANCIES),
                                   name="vh_room_tariff_occupancy_valid"),
            models.CheckConstraint(condition=Q(rate_per_day__gte=0),
                                   name="vh_room_tariff_rate_non_negative"),
        ]

    def __str__(self) -> str:
        return f"{self.category}/{self.occupancy} from {self.effective_from}"


class MealTariff(TimeStampedModel):
    item = models.CharField(max_length=10)
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    effective_from = models.DateField()
    created_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "vh_meal_tariff"
        constraints = [
            models.UniqueConstraint(fields=["item", "effective_from"],
                                    name="vh_meal_tariff_unique_version"),
            models.CheckConstraint(condition=Q(item__in=meals.PRICED_ITEMS),
                                   name="vh_meal_tariff_item_valid"),
            models.CheckConstraint(condition=Q(rate__gte=0),
                                   name="vh_meal_tariff_rate_non_negative"),
        ]

    def __str__(self) -> str:
        return f"{self.item} from {self.effective_from}"
