"""IAM grants for hostel API operations; role assignment remains IAM-owned."""

PERMISSIONS = [
    ("visitor_hostel.booking.request", "Request and view own hostel bookings"),
    ("visitor_hostel.booking.manage", "Caretaker booking and stay operations"),
    ("visitor_hostel.booking.approve", "Decide forwarded hostel bookings"),
    ("visitor_hostel.inventory.manage", "Maintain hostel inventory"),
    ("visitor_hostel.inventory.approve", "Decide replenishment requirements"),
    ("visitor_hostel.tariff.manage", "Maintain hostel tariffs"),
]
ROLE_GRANTS = {
    "student": [PERMISSIONS[0][0]],
    "faculty": [PERMISSIONS[0][0]],
    "staff": [PERMISSIONS[0][0]],
    "vh_caretaker": [PERMISSIONS[i][0] for i in (0, 1, 3)],
    "vh_in_charge": [PERMISSIONS[i][0] for i in (0, 2, 4, 5)],
}

MODULE = {
    "code": "visitor_hostel",
    "label": "Visitors Hostel",
    "icon": "FaBuilding",
    "base_path": "/visitor-hostel",
    "nav_section": "Hostel",
    "sort_order": 20,
    "status": "active",
}
NAV_ITEMS = [
    {
        "code": "visitor_hostel.bookings",
        "label": "Hostel bookings",
        "icon": "FaBuilding",
        "to": "/visitor-hostel/bookings",
        "required_permission": "visitor_hostel.booking.request",
        "sort_order": 10,
    },
]
