"""Employee Leave Management module permissions and navigation."""

MODULE = {
    "code": "elm",
    "label": "Employee Leave Management",
    "icon": "CalendarCheck",
    "base_path": "/elm",
    "nav_section": "Employee Services",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.applications",
        "label": "My Leave Applications",
        "icon": "Calendar",
        "to": "/elm/applications",
        "required_permission": "elm.application.view_self",
        "sort_order": 10,
    },
    {
        "code": "elm.apply",
        "label": "Apply for Leave",
        "icon": "CalendarPlus",
        "to": "/elm/apply",
        "required_permission": "elm.application.apply",
        "sort_order": 20,
    },
]

PERMISSIONS = [
    ("elm.application.view_self", "View one's own leave applications"),
    ("elm.application.apply", "Submit leave applications"),
    ("elm.application.withdraw", "Withdraw a pending leave application"),
    ("elm.application.review", "Review and decide leave applications"),
    ("elm.substitute.respond", "Respond to substitute requests"),
    ("elm.establishment.route", "Route leave applications through Establishment"),
]

SYSTEM_PERMISSIONS = []

_EMPLOYEE = [
    "elm.application.view_self",
    "elm.application.apply",
    "elm.application.withdraw",
    "elm.substitute.respond",
]

_LEAVE_APPROVER = [
    "elm.application.view_self",
    "elm.application.review",
    "elm.establishment.route",
]

ROLE_GRANTS = {
    "employee": _EMPLOYEE,
    "unit_head": _LEAVE_APPROVER,
    "establishment_officer": _LEAVE_APPROVER,
}
