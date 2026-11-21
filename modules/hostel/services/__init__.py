"""Hostel Management business services."""

from .allotment_service import (
    record_allotment_decision,
    record_reallotment,
    record_room_vacation,
    submit_accommodation_request,
)
from .attendance_service import record_attendance_batch
from .complaint_service import submit_complaint, update_complaint_status
from .extended_stay_service import (
    record_charge_and_compliance,
    record_extended_stay_decision,
    submit_extended_stay_request,
)
from .fine_service import record_fine
from .guest_room_service import (
    record_guest_room_decision,
    submit_guest_room_request,
)
from .hostel_service import (
    create_hostel,
    create_or_update_role_binding,
    toggle_hostel_status,
    update_hostel,
)
from .inventory_service import (
    create_or_update_inventory_item,
    create_or_update_staff_assignment,
)
from .leave_service import record_leave_decision, submit_leave_request
from .notice_service import publish_notice
from .notification_service import create_notification
from .report_service import generate_operational_report
from .room_service import (
    create_room,
    record_individual_room_exchange,
    update_room,
)
from .security_service import create_or_update_security_shift

__all__ = [
    "create_hostel",
    "update_hostel",
    "toggle_hostel_status",
    "create_or_update_role_binding",
    "create_room",
    "update_room",
    "record_individual_room_exchange",
    "submit_accommodation_request",
    "record_allotment_decision",
    "record_reallotment",
    "record_room_vacation",
    "record_attendance_batch",
    "submit_leave_request",
    "record_leave_decision",
    "submit_complaint",
    "update_complaint_status",
    "submit_guest_room_request",
    "record_guest_room_decision",
    "submit_extended_stay_request",
    "record_extended_stay_decision",
    "record_charge_and_compliance",
    "record_fine",
    "create_or_update_inventory_item",
    "create_or_update_staff_assignment",
    "create_or_update_security_shift",
    "publish_notice",
    "generate_operational_report",
    "create_notification",
]
