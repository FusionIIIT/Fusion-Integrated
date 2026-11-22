"""Export service functions for hostel.
"""
from modules.hostel.services.accommodations import (
    allot_room,
    record_room_exchange,
    submit_accommodation_request,
)
from modules.hostel.services.operations import (
    impose_fine,
    process_complaint_decision,
    process_leave_decision,
    publish_notice,
    record_student_attendance,
    submit_complaint,
    submit_leave_request,
)

__all__ = [
    "allot_room",
    "impose_fine",
    "process_complaint_decision",
    "process_leave_decision",
    "publish_notice",
    "record_room_exchange",
    "record_student_attendance",
    "submit_accommodation_request",
    "submit_complaint",
    "submit_leave_request",
]
