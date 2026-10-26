"""Module navigation and role permissions for Employee Leave Management."""

MODULE = {
    "code": "leave_elm",
    "label": "Employee Leave",
    "icon": "CalendarCheck",
    "base_path": "/leave",
    "nav_section": "Employee Services",
    "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "leave_elm.mine",
        "label": "My Leave",
        "icon": "Calendar",
        "to": "/leave",
        "required_permission": "leave_elm.application.view_self",
        "sort_order": 10,
    },
    {
        "code": "leave_elm.review",
        "label": "Leave Reviews",
        "icon": "ClipboardCheck",
        "to": "/leave/reviews",
        "required_permission": "leave_elm.application.review",
        "sort_order": 20,
    },
]

PERMISSIONS = [
    ("leave_elm.application.view_self", "View own leave requests and balances"),
    ("leave_elm.application.create", "Apply for leave"),
    ("leave_elm.application.withdraw", "Withdraw own pending leave requests"),
    ("leave_elm.application.review", "Review and decide leave requests"),
    ("leave_elm.configuration.manage", "Manage leave policies and calendars"),
    ("leave_elm.records.manage", "Maintain authorized leave records"),
]

SYSTEM_PERMISSIONS = []

_EMPLOYEE = [
    "leave_elm.application.view_self",
    "leave_elm.application.create",
    "leave_elm.application.withdraw",
]
_REVIEWER = ["leave_elm.application.review"]
_ADMIN = ["leave_elm.configuration.manage", "leave_elm.records.manage"]

ROLE_GRANTS = {
    "employee": _EMPLOYEE,
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "unit_head": [*_EMPLOYEE, *_REVIEWER],
    "establishment": [*_EMPLOYEE, *_REVIEWER],
    "deputy_registrar_estt": [*_EMPLOYEE, *_REVIEWER],
    "dean": [*_EMPLOYEE, *_REVIEWER],
    "registrar": [*_EMPLOYEE, *_REVIEWER],
    "director": [*_EMPLOYEE, *_REVIEWER],
    "leave_administrator": [*_EMPLOYEE, *_ADMIN],
    "Unit Head": [*_EMPLOYEE, *_REVIEWER],
    "Deputy Registrar (Estt.)": [*_EMPLOYEE, *_REVIEWER],
    "Dean": [*_EMPLOYEE, *_REVIEWER],
    "Registrar": [*_EMPLOYEE, *_REVIEWER],
    "Director": [*_EMPLOYEE, *_REVIEWER],
    "Leave Administrator": [*_EMPLOYEE, *_ADMIN],
}
