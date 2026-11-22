"""Visitor Hostel Management System (VHMS) module registry."""

MODULE = {
    "code": "vh",
    "label": "Visitors Hostel",
    "icon": "FaHotel",
    "base_path": "/vh",
    "nav_section": "Facilities",
    "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "vh.request",
        "label": "Book Accommodation",
        "icon": "FaPlusCircle",
        "to": "/vh/request",
        "required_permission": "vh.booking.create",
        "sort_order": 10,
    },
    {
        "code": "vh.bookings",
        "label": "My Bookings",
        "icon": "FaListAlt",
        "to": "/vh/bookings",
        "required_permission": "vh.booking.view_self",
        "sort_order": 20,
    },
    {
        "code": "vh.manage",
        "label": "Booking Requisitions",
        "icon": "FaClipboardCheck",
        "to": "/vh/manage",
        "required_permission": "vh.booking.review",
        "sort_order": 30,
    },
    {
        "code": "vh.approvals",
        "label": "Hostel Approvals",
        "icon": "FaCheckDouble",
        "to": "/vh/approvals",
        "required_permission": "vh.booking.approve",
        "sort_order": 40,
    },
    {
        "code": "vh.stays",
        "label": "Stays & Billing",
        "icon": "FaBed",
        "to": "/vh/stays",
        "required_permission": "vh.stay.manage",
        "sort_order": 50,
    },
    {
        "code": "vh.meals",
        "label": "Mess & Meals",
        "icon": "FaUtensils",
        "to": "/vh/meals",
        "required_permission": "vh.meal.manage",
        "sort_order": 60,
    },
    {
        "code": "vh.inventory",
        "label": "Hostel Inventory",
        "icon": "FaBoxes",
        "to": "/vh/inventory",
        "required_permission": "vh.inventory.manage",
        "sort_order": 70,
    },
    {
        "code": "vh.reports",
        "label": "VH Reports",
        "icon": "FaChartBar",
        "to": "/vh/reports",
        "required_permission": "vh.reports.view",
        "sort_order": 80,
    },
]

PERMISSIONS = [
    ("vh.booking.create", "Submit online booking request for visitors"),
    ("vh.booking.view_self", "View and track own submitted bookings"),
    ("vh.booking.review", "Review and route booking requests (Caretaker)"),
    ("vh.booking.approve", "Approve or reject forwarded bookings (In-Charge)"),
    ("vh.stay.manage", "Manage room allotment, check-in, check-out and bills"),
    ("vh.meal.manage", "Manage mess and meal bookings for residing guests"),
    ("vh.inventory.manage", "Manage inventory stock and replenishment requirements"),
    ("vh.reports.view", "View supervisory and operational hostel reports"),
    ("vh.role.manage", "Manage operational caretaker and in-charge role assignments"),
]

SYSTEM_PERMISSIONS = [
    "vh.role.manage",
]

SCOPE_PERMISSIONS = [
    "vh.reports.view",
]

_INDENTER = [
    "vh.booking.create",
    "vh.booking.view_self",
]

_CARETAKER = [
    *_INDENTER,
    "vh.booking.review",
    "vh.stay.manage",
    "vh.meal.manage",
    "vh.inventory.manage",
    "vh.reports.view",
]

_IN_CHARGE = [
    *_INDENTER,
    "vh.booking.approve",
    "vh.inventory.manage",
    "vh.reports.view",
]

_ADMIN = [
    *_CARETAKER,
    *_IN_CHARGE,
    "vh.role.manage",
]

ROLE_GRANTS = {
    "faculty": _INDENTER,
    "staff": _INDENTER,
    "student": _INDENTER,
    "caretaker": _CARETAKER,
    "vh_caretaker": _CARETAKER,
    "incharge": _IN_CHARGE,
    "vh_incharge": _IN_CHARGE,
    "admin": _ADMIN,
}

