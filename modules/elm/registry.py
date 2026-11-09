"""Employee Leave Management (ELM) module registry."""

MODULE = {
    "code": "elm",
    "label": "Leave Management",
    "icon": "FaCalendarAlt",
    "base_path": "/leave",
    "nav_section": "Leave",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.apply",
        "label": "Apply for Leave",
        "icon": "FaPlusCircle",
        "to": "/leave/apply",
        "required_permission": "elm.leave.apply",
        "sort_order": 10,
    },
    {
        "code": "elm.mine",
        "label": "My Leaves",
        "icon": "FaCalendarCheck",
        "to": "/leave/mine",
        "required_permission": "elm.leave.view_self",
        "sort_order": 20,
    },
    {
        "code": "elm.substitute",
        "label": "Substitute Requests",
        "icon": "FaUserFriends",
        "to": "/leave/substitute",
        "required_permission": "elm.substitute.respond",
        "sort_order": 30,
    },
    {
        "code": "elm.unit_head",
        "label": "Unit Head Approvals",
        "icon": "FaUserTie",
        "to": "/leave/unit-head",
        "required_permission": "elm.review.unit_head",
        "sort_order": 40,
    },
    {
        "code": "elm.establishment",
        "label": "Establishment Routing",
        "icon": "FaBuilding",
        "to": "/leave/establishment",
        "required_permission": "elm.review.establishment",
        "sort_order": 50,
    },
    {
        "code": "elm.sanctions",
        "label": "Sanction Decisions",
        "icon": "FaGavel",
        "to": "/leave/sanctions",
        "required_permission": "elm.sanction.decide",
        "sort_order": 60,
    },
    {
        "code": "elm.admin",
        "label": "Leave Administration",
        "icon": "FaCogs",
        "to": "/leave/admin",
        "required_permission": "elm.admin.manage",
        "sort_order": 70,
    },
]

PERMISSIONS = [
    ("elm.leave.apply", "Apply for leave"),
    ("elm.leave.view_self", "View own leave applications and balances"),
    ("elm.leave.withdraw", "Withdraw own pending leave application"),
    ("elm.leave.cancel", "Request cancellation of approved leave"),
    ("elm.leave.extend", "Request extension of ongoing leave"),
    ("elm.leave.resume", "Submit resumption of duty"),
    ("elm.substitute.respond", "Respond to substitute requests"),
    ("elm.review.unit_head", "Review leave requests at Unit Head level"),
    ("elm.review.establishment", "Verify and route higher-sanction requests at Establishment"),
    ("elm.sanction.decide", "Make final sanctioning decisions"),
    ("elm.admin.manage", "Manage ELM policies, calendars, records, and SLA"),
    ("elm.leave.view_all", "View all employee leave records"),
    ("elm.sla.process", "Trigger SLA threshold processing"),
    ("elm.year_end.process", "Trigger year-end leave balance processing"),
]

SYSTEM_PERMISSIONS = [
    "elm.sla.process",
    "elm.year_end.process",
]

SCOPE_PERMISSIONS = [
    "elm.leave.view_all",
]

_EMPLOYEE = [
    "elm.leave.apply",
    "elm.leave.view_self",
    "elm.leave.withdraw",
    "elm.leave.cancel",
    "elm.leave.extend",
    "elm.leave.resume",
    "elm.substitute.respond",
]

_UNIT_HEAD = [
    *_EMPLOYEE,
    "elm.review.unit_head",
]

_ESTABLISHMENT = [
    *_EMPLOYEE,
    "elm.review.establishment",
    "elm.admin.manage",
    "elm.leave.view_all",
]

_SANCTIONING = [
    *_EMPLOYEE,
    "elm.sanction.decide",
    "elm.leave.view_all",
]

_ADMIN = [
    *_EMPLOYEE,
    "elm.admin.manage",
    "elm.leave.view_all",
    "elm.review.unit_head",
    "elm.review.establishment",
    "elm.sanction.decide",
]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "unit_head": _UNIT_HEAD,
    "HOD": _UNIT_HEAD,
    "dr_estt": _ESTABLISHMENT,
    "deputy_registrar": _ESTABLISHMENT,
    "dean": _SANCTIONING,
    "Dean Academic": _SANCTIONING,
    "registrar": _SANCTIONING,
    "Registrar": _SANCTIONING,
    "director": _SANCTIONING,
    "Director": _SANCTIONING,
    "leave_admin": _ADMIN,
    "acadadmin": _ADMIN,
}
