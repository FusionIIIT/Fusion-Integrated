"""Server-driven navigation and IAM permission manifest."""
from .permissions import PERMISSIONS, ROLE_GRANTS, SYSTEM_PERMISSIONS

MODULE = {
    "code": "visitor_hostel", "label": "Visitors Hostel", "icon": "Bed",
    "base_path": "/visitors-hostel", "nav_section": "Campus",
    "sort_order": 60, "status": "planned",
}

NAV_ITEMS = [
    {"code": "visitor_hostel.bookings", "label": "Bookings",
     "icon": "CalendarCheck", "to": "/visitors-hostel/bookings",
     "required_permission": "visitor_hostel.booking.view_self",
     "sort_order": 10},
    {"code": "visitor_hostel.operations", "label": "VH Operations",
     "icon": "Buildings", "to": "/visitors-hostel/operations",
     "required_permission": "visitor_hostel.booking.view",
     "sort_order": 20},
    {"code": "visitor_hostel.offline_booking", "label": "Record offline booking",
     "icon": "Phone", "to": "/visitors-hostel/offline-booking",
     "required_permission": "visitor_hostel.booking.record_offline",
     "sort_order": 21},
    {"code": "visitor_hostel.inventory", "label": "Inventory",
     "icon": "Package", "to": "/visitors-hostel/inventory",
     "required_permission": "visitor_hostel.inventory.manage",
     "sort_order": 30},
    {"code": "visitor_hostel.reports.caretaker", "label": "Caretaker reports",
     "icon": "ChartBar", "to": "/visitors-hostel/reports",
     "required_permission": "visitor_hostel.report.view_caretaker",
     "sort_order": 40},
    {"code": "visitor_hostel.reports.in_charge", "label": "VH In-Charge reports",
     "icon": "ChartBar", "to": "/visitors-hostel/reports",
     "required_permission": "visitor_hostel.report.view_in_charge",
     "sort_order": 41},
]
