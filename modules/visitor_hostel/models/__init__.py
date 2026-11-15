"""Visitors Hostel tables, split by aggregate."""
from modules.visitor_hostel.models.billing import Bill, BillLine, MealBooking
from modules.visitor_hostel.models.bookings import (
    Booking,
    BookingTransition,
    CancellationRequest,
    ModificationRequest,
)
from modules.visitor_hostel.models.inventory import (
    InventoryAdjustment,
    InventoryAlert,
    InventoryItem,
    ReplenishmentRequirement,
)
from modules.visitor_hostel.models.operations import (
    DutyAssignment,
    NotificationOutbox,
    StayAlert,
)
from modules.visitor_hostel.models.rooms import MealTariff, Room, RoomAllotment, RoomTariff

__all__ = [
    "Bill",
    "BillLine",
    "Booking",
    "BookingTransition",
    "CancellationRequest",
    "DutyAssignment",
    "InventoryAdjustment",
    "InventoryAlert",
    "InventoryItem",
    "MealBooking",
    "MealTariff",
    "ModificationRequest",
    "NotificationOutbox",
    "ReplenishmentRequirement",
    "Room",
    "RoomAllotment",
    "RoomTariff",
    "StayAlert",
]
