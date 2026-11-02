"""Fusion module, navigation, and IAM permission contract for ELM."""

MODULE = {
    "code": "leave_elm",
    "label": "Leave Management",
    "icon": "Calendar",
    "base_path": "/leave",
    "nav_section": "Leave",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "leave.mine", "label": "My Leave", "icon": "Calendar",
     "to": "/leave/mine", "required_permission": "leave_elm.view.self",
     "sort_order": 5},
    {"code": "leave.apply", "label": "Apply for Leave", "icon": "CheckSquare",
     "to": "/leave/apply", "required_permission": "leave_elm.apply.self",
     "sort_order": 10},
    {"code": "leave.approvals", "label": "Approval Queue", "icon": "CheckCircle",
     "to": "/leave/approvals", "required_permission": "leave_elm.review.queue",
     "sort_order": 20},
    {"code": "leave.admin", "label": "Leave Administration", "icon": "Settings",
     "to": "/leave/admin", "required_permission": "leave_elm.manage.policy",
     "sort_order": 30},
]

PERMISSIONS = [
    ("leave_elm.apply.self", "Submit own leave applications"),
    ("leave_elm.view.self", "View own leave balances and history"),
    ("leave_elm.cancel.self", "Request cancellation of own approved leave"),
    ("leave_elm.extend.self", "Request extension of own ongoing leave"),
    ("leave_elm.resume.self", "Submit own leave resumption"),
    ("leave_elm.substitute.respond", "Respond to a substitute assignment"),
    ("leave_elm.review.queue", "View leave tasks assigned to the current user"),
    ("leave_elm.review.unit", "Review leave requests as Unit Head"),
    ("leave_elm.review.establishment", "Process routed leave requests"),
    ("leave_elm.review.final", "Make configured final sanction decisions"),
    ("leave_elm.manage.policy", "Maintain leave policy and hierarchy"),
    ("leave_elm.manage.calendar", "Maintain holiday and RH calendars"),
    ("leave_elm.manage.records", "Maintain leave records and offline sanctions"),
    ("leave_elm.manage.sla", "Configure leave workflow SLA thresholds"),
    ("leave_elm.view.all", "View all employee leave records"),
    ("leave_elm.process.year_end", "Run annual leave-account processing"),
    ("leave_elm.process.sla", "Process pending leave SLA thresholds"),
]

SYSTEM_PERMISSIONS = [
    "leave_elm.process.year_end",
    "leave_elm.process.sla",
]

_EMPLOYEE = [
    "leave_elm.apply.self",
    "leave_elm.view.self",
    "leave_elm.cancel.self",
    "leave_elm.extend.self",
    "leave_elm.resume.self",
    "leave_elm.substitute.respond",
]

ROLE_GRANTS = {
    "Faculty": _EMPLOYEE,
    "Staff": _EMPLOYEE,
    "Unit Head": ["leave_elm.review.queue", "leave_elm.review.unit", *_EMPLOYEE],
    "Deputy Registrar (Estt.)": [
        "leave_elm.review.queue",
        "leave_elm.review.establishment",
        "leave_elm.review.final",
        *_EMPLOYEE,
    ],
    "Dean": ["leave_elm.review.queue", "leave_elm.review.final", *_EMPLOYEE],
    "Registrar": ["leave_elm.review.queue", "leave_elm.review.final", *_EMPLOYEE],
    "Director": ["leave_elm.review.queue", "leave_elm.review.final", *_EMPLOYEE],
    "Leave Administrator": [
        "leave_elm.review.queue",
        *_EMPLOYEE,
        "leave_elm.manage.policy",
        "leave_elm.manage.calendar",
        "leave_elm.manage.records",
        "leave_elm.manage.sla",
        "leave_elm.view.all",
    ],
}
