"""Registry entry, permissions, and designations for Visitor Hostel Management."""

MODULE = {"code": "visitor_hostel", "label": "Visitor Hostel", "icon": "FaHotel", "base_path": "/visitor-hostel", "nav_section": "Campus", "sort_order": 400, "status": "planned"}

PERMISSIONS = [
    ("visitor_hostel.booking.create", "Submit booking request"),
    ("visitor_hostel.booking.view_self", "View own bookings"),
    ("visitor_hostel.booking.cancel", "Cancel own booking"),
    ("visitor_hostel.booking.review", "Review and route bookings"),
    ("visitor_hostel.booking.allot", "Allot rooms"),
    ("visitor_hostel.booking.checkin", "Record check-in"),
    ("visitor_hostel.booking.checkout", "Record check-out"),
    ("visitor_hostel.booking.approve", "Approve forwarded bookings"),
    ("visitor_hostel.tariff.manage", "Manage tariffs"),
    ("visitor_hostel.meal.manage", "Manage meal bookings"),
    ("visitor_hostel.billing.manage", "Manage bills and settlements"),
    ("visitor_hostel.inventory.manage", "Manage inventory"),
    ("visitor_hostel.inventory.approve", "Approve replenishment"),
    ("visitor_hostel.report.view", "View reports"),
    ("visitor_hostel.role.reassign", "Reassign operational roles"),
]

SYSTEM_PERMISSIONS = ["visitor_hostel.role.reassign"]
SCOPE_PERMISSIONS = []

_INDENTER = ["visitor_hostel.booking.create", "visitor_hostel.booking.view_self", "visitor_hostel.booking.cancel"]
_CARETAKER = [*_INDENTER, "visitor_hostel.booking.review", "visitor_hostel.booking.allot", "visitor_hostel.booking.checkin",
              "visitor_hostel.booking.checkout", "visitor_hostel.meal.manage", "visitor_hostel.billing.manage",
              "visitor_hostel.inventory.manage", "visitor_hostel.report.view"]
_INCHARGE = [*_CARETAKER, "visitor_hostel.booking.approve", "visitor_hostel.tariff.manage", "visitor_hostel.inventory.approve"]

ROLE_GRANTS = {
    "student": _INDENTER, "faculty": _INDENTER, "staff": _INDENTER,
    "Hostel Caretaker": _CARETAKER, "Hostel Incharge": _INCHARGE,
}
NAV_ITEMS = []
