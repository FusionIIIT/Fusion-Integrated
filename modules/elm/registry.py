MODULE = {
    "code": "leave_elm", 
    "label": "Employee Leave Management", 
    "icon": "Calendar",
    "base_path": "/leave", 
    "nav_section": "Employee", 
    "sort_order": 40, 
    "status": "active"
}

NAV_ITEMS = [
    {"label": "My Leave Requests", "to": "/leave/requests", "permission": "leave_elm.request.view_self"},
    {"label": "My Leave Balances", "to": "/leave/balances", "permission": "leave_elm.balance.view_self"},
    {"label": "Substitute Queue", "to": "/leave/substitute-queue", "permission": "leave_elm.substitute.respond"},
    {"label": "Unit Head Review Queue", "to": "/leave/unit-head-queue", "permission": "leave_elm.request.review"},
    {"label": "Sanctioning Authority Queue", "to": "/leave/sanction-queue", "permission": "leave_elm.request.sanction"},
    {"label": "Holiday Calendar", "to": "/leave/calendar", "permission": "leave_elm.calendar.view"}
]

PERMISSIONS = [
    "leave_elm.request.view_self",
    "leave_elm.request.apply",
    "leave_elm.request.withdraw",
    "leave_elm.request.cancel",
    "leave_elm.request.review",
    "leave_elm.request.sanction",
    "leave_elm.substitute.respond",
    "leave_elm.balance.view_self",
    "leave_elm.balance.manage",
    "leave_elm.calendar.view",
    "leave_elm.calendar.manage",
    "leave_elm.policy.manage",
    "leave_elm.offline.record"
]

ROLE_GRANTS = [
    {"role": "employee", "groups": ["Faculty", "Staff"]},
    {"role": "Unit Head"},
    {"role": "Establishment"},
    {"role": "Dean"},
    {"role": "Registrar"},
    {"role": "Director"},
    {"role": "Leave Administrator"}
]
