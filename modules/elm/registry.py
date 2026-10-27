"""ELM module manifest, navigation structure, and role permission grants."""

MODULE = {
    "code": "elm",
    "label": "Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/elm",
    "nav_section": "Services",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.mine",
        "label": "My Leaves",
        "icon": "CalendarCheck",
        "to": "/elm/mine",
        "required_permission": "elm.leave.view_self",
        "sort_order": 10,
    },
    {
        "code": "elm.apply",
        "label": "Apply Leave",
        "icon": "PlusCircle",
        "to": "/elm/apply",
        "required_permission": "elm.leave.apply",
        "sort_order": 20,
    },
    {
        "code": "elm.substitute",
        "label": "Substitute Requests",
        "icon": "UserSwitch",
        "to": "/elm/substitute",
        "required_permission": "elm.leave.substitute",
        "sort_order": 30,
    },
    {
        "code": "elm.approvals",
        "label": "Pending Approvals",
        "icon": "ClockCounterClockwise",
        "to": "/elm/approvals",
        "required_permission": "elm.leave.unit_head_review",
        "sort_order": 40,
    },
    {
        "code": "elm.admin",
        "label": "Leave Admin",
        "icon": "Gear",
        "to": "/elm/admin",
        "required_permission": "elm.leave.admin",
        "sort_order": 50,
    },
]

from .permissions import PERMISSIONS  # noqa: E402

_ALL_EMPLOYEES = [
    "elm.leave.apply",
    "elm.leave.view_self",
    "elm.leave.substitute",
]

_UNIT_HEAD = [
    *_ALL_EMPLOYEES,
    "elm.leave.unit_head_review",
]

_ESTABLISHMENT = [
    *_ALL_EMPLOYEES,
    "elm.leave.establishment_review",
    "elm.leave.admin",
    "elm.leave.report",
]

_SANCTIONING_AUTHORITY = [
    *_ALL_EMPLOYEES,
    "elm.leave.sanction",
    "elm.leave.report",
]

_LEAVE_ADMIN = [
    *_ALL_EMPLOYEES,
    "elm.leave.admin",
    "elm.leave.report",
]

ROLE_GRANTS = {
    "faculty": _ALL_EMPLOYEES,
    "staff": _ALL_EMPLOYEES,
    "unit_head": _UNIT_HEAD,
    "hod": _UNIT_HEAD,
    "establishment": _ESTABLISHMENT,
    "dean": _SANCTIONING_AUTHORITY,
    "registrar": _SANCTIONING_AUTHORITY,
    "director": _SANCTIONING_AUTHORITY,
    "leave_admin": _LEAVE_ADMIN,
    "admin": [*_ALL_EMPLOYEES, *_LEAVE_ADMIN, *_SANCTIONING_AUTHORITY],
}
