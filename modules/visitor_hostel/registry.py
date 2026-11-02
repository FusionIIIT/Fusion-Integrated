MODULE = {
    "code": "visitor_hostel", 
    "label": "Visitors Hostel", 
    "icon": "Buildings",
    "base_path": "/vh", 
    "nav_section": "Facilities", 
    "sort_order": 20, 
    "status": "active"
}
NAV_ITEMS = [
    {"code": "vh.request", "label": "Request Booking", "icon": "PlusCircle", "to": "/vh/booking-request", "required_permission": "vh.booking.create", "sort_order": 10},
    {"code": "vh.mine", "label": "My Bookings", "icon": "CalendarBlank", "to": "/vh/my-bookings", "required_permission": "vh.booking.view_self", "sort_order": 20},
    {"code": "vh.caretaker", "label": "Caretaker Desk", "icon": "ClipboardText", "to": "/vh/caretaker-dashboard", "required_permission": "vh.caretaker.manage", "sort_order": 30},
    {"code": "vh.allotment", "label": "Room Allotment", "icon": "Key", "to": "/vh/allotments", "required_permission": "vh.allotment.manage", "sort_order": 40},
    {"code": "vh.meals", "label": "Meals & Dining", "icon": "ForkKnife", "to": "/vh/meals", "required_permission": "vh.meals.manage", "sort_order": 50},
    {"code": "vh.billing", "label": "Billing & Settlement", "icon": "Receipt", "to": "/vh/billing", "required_permission": "vh.billing.manage", "sort_order": 60},
    {"code": "vh.inventory", "label": "Inventory", "icon": "Package", "to": "/vh/inventory", "required_permission": "vh.inventory.manage", "sort_order": 70},
    {"code": "vh.incharge", "label": "Approvals & Reports", "icon": "ChartBar", "to": "/vh/incharge-dashboard", "required_permission": "vh.incharge.manage", "sort_order": 80},
]
PERMISSIONS = [
    ("vh.booking.create", "Submit booking request"),
    ("vh.booking.view_self", "View personal bookings"),
    ("vh.booking.cancel_self", "Request booking cancellation"),
    ("vh.caretaker.manage", "Caretaker desk operations"),
    ("vh.allotment.manage", "Room allotment and checkin/out"),
    ("vh.meals.manage", "Record and manage meal bookings"),
    ("vh.billing.manage", "Generate and settle cash bills"),
    ("vh.inventory.manage", "Inventory tracking and alerts"),
    ("vh.incharge.manage", "Supervisor approvals and reporting"),
]
SYSTEM_PERMISSIONS = ["vh.system.auto_cancel_noshow"]
ROLE_GRANTS = {
    "student": ["vh.booking.create", "vh.booking.view_self", "vh.booking.cancel_self"],
    "faculty": ["vh.booking.create", "vh.booking.view_self", "vh.booking.cancel_self"],
    "staff": ["vh.booking.create", "vh.booking.view_self", "vh.booking.cancel_self"],
    "vh_caretaker": ["vh.caretaker.manage", "vh.allotment.manage", "vh.meals.manage", "vh.billing.manage", "vh.inventory.manage"],
    "vh_incharge": ["vh.incharge.manage", "vh.billing.manage", "vh.inventory.manage"],
}
