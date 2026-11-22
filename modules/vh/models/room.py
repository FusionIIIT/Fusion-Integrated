# Room and RoomAllotment models for VHMS.
from django.db import models
from django.db.models import CheckConstraint, Index, Q

from core.db.mixins import TimeStampedModel


class Room(TimeStampedModel):
    # Physical room inventory in Visitors Hostel.
    room_number = models.CharField(max_length=20, unique=True, db_index=True)
    room_type = models.CharField(
        max_length=20,
        choices=[("suite", "Suite"), ("non_suite", "Non-suite")],
        default="non_suite",
    )
    floor = models.PositiveIntegerField(default=1)
    capacity = models.PositiveIntegerField(default=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "vh_room"
        indexes = [
            Index(fields=["room_type", "is_active"], name="vh_room_type_active_idx"),
        ]

    def __str__(self) -> str:
        return f"Room {self.room_number} ({self.room_type})"


class RoomAllotment(TimeStampedModel):
    # Assignment of an approved booking to a specific room with recorded occupancy.
    booking = models.ForeignKey(
        "vh.Booking",
        on_delete=models.CASCADE,
        related_name="allotments",
    )
    room = models.ForeignKey(
        "vh.Room",
        on_delete=models.PROTECT,
        related_name="allotments",
    )
    occupancy_type = models.CharField(
        max_length=10,
        choices=[("single", "Single"), ("double", "Double")],
        default="single",
    )
    allotted_by = models.IntegerField()  # Caretaker user_id
    allotted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vh_room_allotment"
        indexes = [
            Index(fields=["booking", "room"], name="vh_allot_bk_room_idx"),
        ]
        constraints = [
            CheckConstraint(
                condition=Q(occupancy_type__in=["single", "double"]),
                name="vh_allot_valid_occupancy",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.booking.booking_reference} -> {self.room.room_number} ({self.occupancy_type})"
        )
