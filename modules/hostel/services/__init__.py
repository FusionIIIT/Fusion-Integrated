"""Hostel service layer exports."""

from .allotment_service import allot_room, submit_accommodation_request, vacate_room
from .attendance_service import record_daily_attendance
from .complaint_service import submit_complaint, update_complaint_status
from .extended_stay_service import (
    decide_extended_stay_request,
    submit_extended_stay_request,
    update_extended_stay_compliance,
)
from .fine_service import record_fine, update_fine_status
from .guest_room_service import decide_guest_room_booking, submit_guest_room_booking
from .hostel_service import (
    assign_role_binding,
    create_hostel,
    deactivate_role_binding,
    set_hostel_active_status,
)
from .inventory_service import record_inventory_item, record_staff_member
from .leave_service import decide_leave_request, submit_leave_request
from .notice_service import publish_notice
from .notification_service import emit_notification
from .report_service import (
    get_cross_hostel_executive_summary,
    get_hostel_attendance_report,
    get_hostel_complaints_report,
    get_hostel_fines_report,
    get_hostel_occupancy_report,
)
from .room_service import create_room, execute_room_exchange, update_room_status

__all__ = [
    "allot_room",
    "assign_role_binding",
    "create_hostel",
    "create_room",
    "deactivate_role_binding",
    "decide_extended_stay_request",
    "decide_guest_room_booking",
    "decide_leave_request",
    "emit_notification",
    "execute_room_exchange",
    "get_cross_hostel_executive_summary",
    "get_hostel_attendance_report",
    "get_hostel_complaints_report",
    "get_hostel_fines_report",
    "get_hostel_occupancy_report",
    "publish_notice",
    "record_daily_attendance",
    "record_fine",
    "record_inventory_item",
    "record_staff_member",
    "set_hostel_active_status",
    "submit_accommodation_request",
    "submit_complaint",
    "submit_extended_stay_request",
    "submit_guest_room_booking",
    "submit_leave_request",
    "update_complaint_status",
    "update_extended_stay_compliance",
    "update_fine_status",
    "update_room_status",
    "vacate_room",
]
