"""What the server tells the shell about Employee Leave Management (ELM).

Server-driven navigation and RBAC configuration for ELM module.
"""

MODULE = {
    "code": "elm",
    "label": "Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/elm",
    "nav_section": "HR & Admin",
    "sort_order": 25,
    "status": "active",
}

NAV_ITEMS = [
    # -- Self-service leave actions for employees (faculty/staff) -----------
    {
        "code": "elm.apply",
        "label": "Apply for Leave",
        "icon": "PlusCircle",
        "to": "/elm/apply",
        "required_permission": "elm.leave.apply",
        "sort_order": 10,
    },
    {
        "code": "elm.mine",
        "label": "My Leaves & Balances",
        "icon": "ClockCounterClockwise",
        "to": "/elm/mine",
        "required_permission": "elm.leave.view_self",
        "sort_order": 20,
    },
    {
        "code": "elm.substitute",
        "label": "Substitute Requests",
        "icon": "Users",
        "to": "/elm/substitute-requests",
        "required_permission": "elm.leave.substitute",
        "sort_order": 30,
    },

    # -- Reviewers & sanctioning authorities -------------------------------
    {
        "code": "elm.unit_head_reviews",
        "label": "Unit Head Reviews",
        "icon": "ClipboardText",
        "to": "/elm/unit-head-reviews",
        "required_permission": "elm.leave.review",
        "sort_order": 40,
    },
    {
        "code": "elm.establishment_routing",
        "label": "Establishment Verification",
        "icon": "ArrowsSplit",
        "to": "/elm/establishment-routing",
        "required_permission": "elm.leave.route",
        "sort_order": 50,
    },
    {
        "code": "elm.sanctions",
        "label": "Sanctioning Decisions",
        "icon": "CheckSquareOffset",
        "to": "/elm/sanction-decisions",
        "required_permission": "elm.leave.sanction",
        "sort_order": 60,
    },

    # -- Administrative maintenance & calendars ---------------------------
    {
        "code": "elm.admin_calendars",
        "label": "Holiday Calendars & Policies",
        "icon": "GearSix",
        "to": "/elm/admin",
        "required_permission": "elm.leave.admin",
        "sort_order": 70,
    },
]

PERMISSIONS = [
    ("elm.leave.apply", "Apply for leave and submit station details"),
    ("elm.leave.view_self", "View own leave balances, applications, and history"),
    ("elm.leave.withdraw", "Withdraw pending leave requests before final decision"),
    ("elm.leave.cancel", "Request pre-start cancellation of approved leave"),
    ("elm.leave.extend", "Request extension of ongoing EL, COL, or VL"),
    ("elm.leave.resume", "Submit resumption of duty after leave"),
    ("elm.leave.substitute", "Respond to substitute responsibility requests"),
    ("elm.leave.review", "Review and decide/recommend leave as Unit Head"),
    ("elm.leave.route", "Verify records and route leave in Establishment"),
    ("elm.leave.sanction", "Sanction or reject leave as Competent Authority"),
    ("elm.leave.admin", "Maintain leave quotas, holiday calendars, and offline records"),
]

SYSTEM_PERMISSIONS = [
    "elm.leave.year_end_process",
    "elm.leave.sla_escalate",
]

_EMPLOYEE_BASE = [
    "elm.leave.apply",
    "elm.leave.view_self",
    "elm.leave.withdraw",
    "elm.leave.cancel",
    "elm.leave.extend",
    "elm.leave.resume",
    "elm.leave.substitute",
]

_UNIT_HEAD = [
    *_EMPLOYEE_BASE,
    "elm.leave.review",
]

_ESTABLISHMENT = [
    *_EMPLOYEE_BASE,
    "elm.leave.route",
]

_SANCTIONING_AUTHORITY = [
    *_EMPLOYEE_BASE,
    "elm.leave.sanction",
]

_LEAVE_ADMIN = [
    *_EMPLOYEE_BASE,
    "elm.leave.admin",
    "elm.leave.review",
    "elm.leave.route",
    "elm.leave.sanction",
]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE_BASE,
    "staff": _EMPLOYEE_BASE,
    "hod": _UNIT_HEAD,
    "unit_head": _UNIT_HEAD,
    "establishment": _ESTABLISHMENT,
    "dr_establishment": _ESTABLISHMENT,
    "dean": _SANCTIONING_AUTHORITY,
    "registrar": _SANCTIONING_AUTHORITY,
    "director": _SANCTIONING_AUTHORITY,
    "leave_admin": _LEAVE_ADMIN,
    "admin": _LEAVE_ADMIN,
}
