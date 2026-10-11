MODULE = {
    "code": "leave_cell", "label": "Leave Management", "icon": "CalendarBlank",
    "base_path": "/leave", "nav_section": "Leave", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "leave.applications", "label": "Leave Applications",
     "icon": "Users", "to": "/leave/applications",
     "required_permission": "leave_cell.application.view", "sort_order": 10},
    {"code": "leave.offers", "label": "Leave Offers",
     "icon": "Signature", "to": "/leave/offers",
     "required_permission": "leave_cell.offer.respond", "sort_order": 20},
]

PERMISSIONS = [
    ("leave_cell.application.view", "See all leave applications"),
    ("leave_cell.application.create", "Apply for leave"),
    ("leave_cell.application.review", "Shortlist and reject leave applications"),
    ("leave_cell.application.delete", "Withdraw a leave application"),
    ("leave_cell.application.auto_withdraw", "System auto-withdrawal"),
    ("leave_cell.offer.respond", "Accept or decline a leave offer"),
]

SYSTEM_PERMISSIONS = [
    "leave_cell.application.auto_withdraw",
]

_STUDENT = [
    "leave_cell.application.create",
]

_COORDINATOR = [
    "leave_cell.application.view",
    "leave_cell.application.review",
]

_OFFICER = [
    *_COORDINATOR,
    "leave_cell.application.create",
    "leave_cell.offer.respond",
]

_CHAIRMAN = [
    "leave_cell.application.view",
]

ROLE_GRANTS = {
    "student": _STUDENT,
    "leave_coordinator": _COORDINATOR,
    "leave_officer": _OFFICER,
    "leave_chairman": _CHAIRMAN,
}
