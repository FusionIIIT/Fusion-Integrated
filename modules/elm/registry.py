"""What the server tells the shell about the ELM module (ADR-0010)."""

MODULE = {
    "code": "elm",
    "label": "Leave Management",
    "icon": "FaCalendarAlt",
    "base_path": "/elm",
    "nav_section": "Campus",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.mine",
        "label": "My Leaves",
        "icon": "FaClipboardList",
        "to": "/elm/mine",
        "required_permission": "elm.leave.view_self",
        "sort_order": 10,
    },
    {
        "code": "elm.balances",
        "label": "Leave Balances",
        "icon": "FaChartBar",
        "to": "/elm/balances",
        "required_permission": "elm.balance.view",
        "sort_order": 20,
    },
    {
        "code": "elm.approvals",
        "label": "Approval Queue",
        "icon": "FaCheckDouble",
        "to": "/elm/approvals",
        "required_permission": "elm.leave.review",
        "sort_order": 30,
    },
    {
        "code": "elm.holidays",
        "label": "Holiday Calendar",
        "icon": "FaCalendarAlt",
        "to": "/elm/holidays",
        "required_permission": "elm.holiday.view",
        "sort_order": 40,
    },
]

PERMISSIONS = [
    ("elm.leave.view_self", "View own leave applications"),
    ("elm.leave.create", "Apply for leave"),
    ("elm.leave.cancel", "Cancel own leave application"),
    ("elm.leave.review", "Approve or reject leave applications in queue"),
    ("elm.balance.view", "View leave balances"),
    ("elm.holiday.view", "View holiday calendar"),
]

SYSTEM_PERMISSIONS: list[str] = []

_APPLICANT = [
    "elm.leave.view_self",
    "elm.leave.create",
    "elm.leave.cancel",
    "elm.balance.view",
    "elm.holiday.view",
]

_REVIEWER = [
    *_APPLICANT,
    "elm.leave.review",
]

ROLE_GRANTS = {
    "student": _APPLICANT,
    "placement_coordinator": _APPLICANT,
    "placement_officer": _REVIEWER,
    "placement_chairman": _REVIEWER,
    "Dean Academic": _REVIEWER,
    "acadadmin": _REVIEWER,
}

