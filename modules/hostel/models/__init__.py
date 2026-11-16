"""Aggregate models export for hostel.
"""
from modules.hostel.models.accommodations import (
    AccommodationRequest,
    RoomAllotment,
    RoomExchange,
)
from modules.hostel.models.hostels import Hostel, HostelRoleBinding, Room
from modules.hostel.models.operations import (
    ExtendedStayRequest,
    GuestRoomBooking,
    HostelComplaint,
    HostelFine,
    HostelInventory,
    HostelNotice,
    LeaveRequest,
    SecurityShift,
    StudentAttendance,
)

__all__ = [
    "AccommodationRequest",
    "ExtendedStayRequest",
    "GuestRoomBooking",
    "Hostel",
    "HostelComplaint",
    "HostelFine",
    "HostelInventory",
    "HostelNotice",
    "HostelRoleBinding",
    "LeaveRequest",
    "Room",
    "RoomAllotment",
    "RoomExchange",
    "SecurityShift",
    "StudentAttendance",
]
