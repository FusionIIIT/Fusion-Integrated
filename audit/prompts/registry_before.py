"""Registry for ELM module in Fusion platform (ADR-0010 compliant).
Model: Qwen 2.5 Coder 14B implementation.
"""
MODULE = {
    "code": "leave_management",
    "label": "Leave Management (ELM)",
    "icon": "CalendarBlank",
    "base_path": "/leave",
    "nav_section": "Human Resources",
    "sort_order": 15,
    "status": "active",
}

NAV_ITEMS = [
    # Employee self-service (EL-UC-001, 007, 008, 009, 010, 012, 013)
    {"code": "leave.apply", "label": "Apply Leave", "icon": "CalendarPlus",
     "to": "/leave/apply", "required_permission": "elm.leave.apply", "sort_order": 10},
    {"code": "leave.history", "label": "My Leaves & Balances", "icon": "ClockCounterClockwise",
     "to": "/leave/history", "required_permission": "elm.leave.view_self", "sort_order": 20},
    {"code": "leave.substitute_tasks", "label": "Substitute Tasks", "icon": "UserSwitch",
     "to": "/leave/substitute", "required_permission": "elm.substitute.respond", "sort_order": 30},

    # Reviewer / Authority Work queues (EL-UC-003, 004, 005, 011)
    {"code": "leave.unit_head", "label": "Unit Head Approvals", "icon": "CheckSquare",
     "to": "/leave/unit-head", "required_permission": "elm.review.unit_head", "sort_order": 40},
    {"code": "leave.establishment", "label": "Establishment Routing", "icon": "FileSearch",
     "to": "/leave/establishment", "required_permission": "elm.review.establishment", "sort_order": 50},
    {"code": "leave.sanctioning", "label": "Sanction Decisions", "icon": "Stamp",
     "to": "/leave/sanction", "required_permission": "elm.sanction.decide", "sort_order": 60},
    {"code": "leave.resumption_queue", "label": "Resumption Reviews", "icon": "ArrowCounterClockwise",
     "to": "/leave/resumptions", "required_permission": "elm.resumption.review", "sort_order": 70},

    # Administration (EL-UC-014, 015, 016, 017, 018)
    {"code": "leave.admin_policy", "label": "ELM Policy & Calendars", "icon": "GearSix",
     "to": "/leave/admin/policy", "required_permission": "elm.admin.policy", "sort_order": 80},
    {"code": "leave.offline_sync", "label": "Offline Leave Sync", "icon": "Database",
     "to": "/leave/admin/offline-sync", "required_permission": "elm.admin.offline_sync", "sort_order": 90},
]

PERMISSIONS = [
    ("elm.leave.apply", "Create and submit leave applications"),
    ("elm.leave.view_self", "View own leave history, balances, and export records"),
    ("elm.leave.withdraw", "Withdraw pending leave requests before final decision"),
    ("elm.leave.cancel", "Cancel approved leave prior to start"),
    ("elm.leave.extend", "Request extension of ongoing EL/COL/VL"),
    ("elm.leave.resume", "Submit duty resumption after EL/COL/VL"),
    ("elm.substitute.respond", "Accept or decline nominated substitute responsibilities"),
    ("elm.review.unit_head", "Perform Unit Head review and decisions/recommendations"),
    ("elm.review.establishment", "Perform establishment verification and authority routing"),
    ("elm.sanction.decide", "Make final sanctioning decisions (Dean, Registrar, Director)"),
    ("elm.resumption.review", "Review duty resumption declarations"),
    ("elm.admin.policy", "Configure leave policy, SLA thresholds, and publish calendars"),
    ("elm.admin.offline_sync", "Record already-sanctioned offline leaves and maintain records"),
]

_EMPLOYEE_BASE = [
    "elm.leave.apply", "elm.leave.view_self", "elm.leave.withdraw",
    "elm.leave.cancel", "elm.leave.extend", "elm.leave.resume",
    "elm.substitute.respond",
]

_UNIT_HEAD_PERMS = [*_EMPLOYEE_BASE, "elm.review.unit_head"]
_ESTABLISHMENT_PERMS = [*_EMPLOYEE_BASE, "elm.review.establishment", "elm.admin.offline_sync"]
_SANCTION_PERMS = [*_EMPLOYEE_BASE, "elm.sanction.decide", "elm.resumption.review"]
_ADMIN_PERMS = [*_EMPLOYEE_BASE, *_UNIT_HEAD_PERMS, *_ESTABLISHMENT_PERMS, *_SANCTION_PERMS, "elm.admin.policy"]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE_BASE,
    "staff": _EMPLOYEE_BASE,
    "unit_head": _UNIT_HEAD_PERMS,
    "hod": _UNIT_HEAD_PERMS,
    "deputy_registrar": _ESTABLISHMENT_PERMS,
    "dean": _SANCTION_PERMS,
    "registrar": _SANCTION_PERMS,
    "director": [*_SANCTION_PERMS, "elm.review.unit_head"],
    "leave_administrator": _ADMIN_PERMS,
}
