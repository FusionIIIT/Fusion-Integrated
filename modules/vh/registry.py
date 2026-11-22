# Visitors Hostel Management System module manifest and RBAC registry.

MODULE = {
    "code": "vh",
    "label": "Visitors Hostel",
    "icon": "Buildings",
    "base_path": "/vh",
    "nav_section": "Facilities",
    "sort_order": 22,
    "status": "active",
}

NAV_ITEMS = [
    # Indenter navigation
    {
        "code": "vh.new_booking",
        "label": "New Booking",
        "icon": "PlusCircle",
        "to": "/vh/booking/new",
        "required_permission": "vh.booking.create",
        "sort_order": 10,
    },
    {
        "code": "vh.my_bookings",
        "label": "My Bookings",
        "icon": "ClockCounterClockwise",
        "to": "/vh/my-bookings",
        "required_permission": "vh.booking.view",
        "sort_order": 20,
    },
    {
        "code": "vh.tariffs",
        "label": "Tariff Card",
        "icon": "Receipt",
        "to": "/vh/tariffs",
        "required_permission": "vh.tariff.view",
        "sort_order": 30,
    },
    # Caretaker navigation
    {
        "code": "vh.bookings",
        "label": "Requisitions",
        "icon": "Inbox",
        "to": "/vh/bookings",
        "required_permission": "vh.booking.review",
        "sort_order": 40,
    },
    {
        "code": "vh.stays",
        "label": "Stay & Check-in",
        "icon": "Key",
        "to": "/vh/stays",
        "required_permission": "vh.stay.manage",
        "sort_order": 50,
    },
    {
        "code": "vh.meals",
        "label": "Mess & Meals",
        "icon": "ForkKnife",
        "to": "/vh/meals",
        "required_permission": "vh.meal.manage",
        "sort_order": 60,
    },
    {
        "code": "vh.billing",
        "label": "Billing & Cash",
        "icon": "CurrencyInr",
        "to": "/vh/billing",
        "required_permission": "vh.bill.manage",
        "sort_order": 70,
    },
    {
        "code": "vh.inventory",
        "label": "Hostel Inventory",
        "icon": "Package",
        "to": "/vh/inventory",
        "required_permission": "vh.inventory.manage",
        "sort_order": 80,
    },
    {
        "code": "vh.caretaker_reports",
        "label": "Operational Logs",
        "icon": "FileText",
        "to": "/vh/caretaker-reports",
        "required_permission": "vh.report.view",
        "sort_order": 90,
    },
    # VH In-Charge navigation
    {
        "code": "vh.approvals",
        "label": "Executive Approvals",
        "icon": "CheckSquareOffset",
        "to": "/vh/approvals",
        "required_permission": "vh.booking.approve",
        "sort_order": 100,
    },
    {
        "code": "vh.supervisor_reports",
        "label": "Executive Reports",
        "icon": "ChartBar",
        "to": "/vh/supervisor-reports",
        "required_permission": "vh.report.manage",
        "sort_order": 110,
    },
    {
        "code": "vh.role_admin",
        "label": "Role Reassignment",
        "icon": "UsersThree",
        "to": "/vh/roles",
        "required_permission": "vh.role.assign",
        "sort_order": 120,
    },
]

PERMISSIONS = [
    # Booking lifecycle permissions
    ("vh.booking.create", "Submit an online booking request"),
    ("vh.booking.view", "View visible booking details and history"),
    ("vh.booking.update", "Request modification to a submitted booking"),
    ("vh.booking.delete", "Request cancellation of a booking"),
    ("vh.booking.review", "Review pending bookings, check availability, route or reject"),
    ("vh.booking.approve", "Approve or reject forwarded bookings"),
    # Room allotment and stay management
    ("vh.room.assign", "Allot rooms to approved bookings"),
    ("vh.stay.manage", "Record check-in, check-out, and stay exceptions"),
    # Meal management
    ("vh.meal.manage", "Manage mess and meal bookings for staying guests"),
    ("vh.meal.view", "View meal records"),
    # Billing and offline settlement
    ("vh.bill.create", "Generate stay and cancellation bills"),
    ("vh.bill.view", "View generated bills"),
    ("vh.bill.manage", "Record offline cash settlement and checkout verification"),
    # Inventory management
    ("vh.inventory.view", "View inventory quantities and threshold alerts"),
    ("vh.inventory.manage", "Record and update inventory stocks"),
    ("vh.inventory.approve", "Approve inventory replenishment requirements"),
    # Tariffs, operational reports, and role assignment
    ("vh.tariff.view", "View active and published tariff rates"),
    ("vh.tariff.manage", "Configure effective-dated visitor category tariffs"),
    ("vh.report.view", "View caretaker operational reports and logs"),
    ("vh.report.manage", "View supervisory summary and revenue reports"),
    ("vh.role.assign", "Reassign operational Caretaker and In-Charge roles"),
]

SYSTEM_PERMISSIONS = [
    "vh.stay.monitor",
    "vh.inventory.monitor",
]

_INDENTER_PERMS = [
    "vh.booking.create",
    "vh.booking.view",
    "vh.booking.update",
    "vh.booking.delete",
    "vh.tariff.view",
]

_CARETAKER_PERMS = [
    "vh.booking.create",
    "vh.booking.view",
    "vh.booking.review",
    "vh.room.assign",
    "vh.stay.manage",
    "vh.meal.manage",
    "vh.meal.view",
    "vh.bill.create",
    "vh.bill.view",
    "vh.bill.manage",
    "vh.inventory.view",
    "vh.inventory.manage",
    "vh.tariff.view",
    "vh.report.view",
]

_INCHARGE_PERMS = [
    "vh.booking.view",
    "vh.booking.approve",
    "vh.meal.view",
    "vh.bill.view",
    "vh.inventory.view",
    "vh.inventory.approve",
    "vh.tariff.view",
    "vh.tariff.manage",
    "vh.report.manage",
    "vh.role.assign",
]

ROLE_GRANTS = {
    "student": _INDENTER_PERMS,
    "faculty": _INDENTER_PERMS,
    "staff": _INDENTER_PERMS,
    "VhCaretaker": _CARETAKER_PERMS,
    "VhIncharge": _INCHARGE_PERMS,
}
