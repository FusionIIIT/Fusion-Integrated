"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all. Icons name entries in `client/src/ui/icons.ts`.
"""
MODULE = {
    "code": "elm", "label": "Employee Leave", "icon": "FaCalendarAlt",
    "base_path": "/elm", "nav_section": "Employee", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "elm.my", "label": "My Leave", "icon": "FaIdCard",
     "to": "/elm/my", "required_permission": "elm.leave_request.view_self",
     "sort_order": 10},
    {"code": "elm.approvals", "label": "Approvals", "icon": "FaClipboardCheck",
     "to": "/elm/approvals", "required_permission": "elm.leave_request.review",
     "sort_order": 20},
    {"code": "elm.sanctions", "label": "Sanctions", "icon": "FaFileSignature",
     "to": "/elm/sanctions", "required_permission": "elm.leave_request.sanction",
     "sort_order": 30},
    {"code": "elm.substitutions", "label": "Substitutions", "icon": "FaUserCheck",
     "to": "/elm/substitutions", "required_permission": "elm.substitute.respond",
     "sort_order": 40},
    {"code": "elm.records", "label": "Leave Records", "icon": "FaClipboardList",
     "to": "/elm/records", "required_permission": "elm.record.manage",
     "sort_order": 50},
    {"code": "elm.policy", "label": "Leave Policy", "icon": "FaCog",
     "to": "/elm/policy", "required_permission": "elm.policy.manage",
     "sort_order": 60},
    {"code": "elm.calendar", "label": "Holiday Calendar", "icon": "FaCalendarAlt",
     "to": "/elm/calendar", "required_permission": "elm.calendar.manage",
     "sort_order": 70},
    {"code": "elm.sla", "label": "SLA", "icon": "FaChartBar",
     "to": "/elm/sla", "required_permission": "elm.sla.manage",
     "sort_order": 80},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("elm.leave_request.view_self", "See and manage one's own leave"),
    ("elm.leave_request.create", "Apply for leave"),
    ("elm.leave_request.withdraw", "Withdraw a pending leave request"),
    ("elm.leave_request.cancel", "Request cancellation of approved leave"),
    ("elm.leave_request.extension", "Request extension of ongoing leave"),
    ("elm.leave_request.resumption", "Record return to duty after leave"),
    ("elm.leave_request.view", "See leave requests across the module"),
    ("elm.leave_request.review", "Review and recommend leave as unit head"),
    ("elm.leave_request.establishment", "Verify leave against establishment"),
    ("elm.leave_request.sanction", "Grant or refuse final sanction"),
    ("elm.leave_request.print", "Print and export leave records"),
    ("elm.substitute.respond", "Accept or decline a substitute nomination"),
    ("elm.leave_account.view", "See leave balances and the ledger"),
    ("elm.policy.manage", "Configure leave types and entitlements"),
    ("elm.calendar.manage", "Publish holidays and vacation periods"),
    ("elm.record.manage", "Manage the leave records of all employees"),
    ("elm.offline.record", "Record a paper-sanctioned leave offline"),
    ("elm.sla.manage", "Configure SLA thresholds and run processing"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = [
    "elm.leave_request.year_end",
    "elm.sla.process",
    "elm.leave_request.escalate",
]

_EMPLOYEE = [
    "elm.leave_request.view_self",
    "elm.leave_request.create",
    "elm.leave_request.withdraw",
    "elm.leave_request.cancel",
    "elm.leave_request.extension",
    "elm.leave_request.resumption",
    "elm.leave_request.print",
    "elm.substitute.respond",
    "elm.leave_account.view",
]

_UNIT_HEAD = [
    "elm.leave_request.view",
    "elm.leave_request.review",
    "elm.leave_account.view",
]

_ESTABLISHMENT = [
    "elm.leave_request.view",
    "elm.leave_request.review",
    "elm.leave_request.establishment",
    "elm.leave_account.view",
]

_SANCTION = [
    "elm.leave_request.view",
    "elm.leave_request.sanction",
    "elm.leave_account.view",
]

_ADMIN = [
    "elm.leave_request.view",
    "elm.leave_request.print",
    "elm.leave_account.view",
    "elm.policy.manage",
    "elm.calendar.manage",
    "elm.record.manage",
    "elm.offline.record",
    "elm.sla.manage",
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "unit_head": _UNIT_HEAD,
    "deputy_registrar": _ESTABLISHMENT,
    "establishment": _ESTABLISHMENT,
    "dean": _SANCTION,
    "registrar": _SANCTION,
    "director": _SANCTION,
    "leave_admin": _ADMIN,
    "acadadmin": _ADMIN,
}
