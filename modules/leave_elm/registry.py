"""Leave Management module registry.

Plain MODULE dictionary, NAV_ITEMS dictionaries, PERMISSIONS list of (code,label),
ROLE_GRANTS dict of role names to permission-code lists, SYSTEM_PERMISSIONS list.
"""
MODULE = {
    "code": "leave_elm",
    "label": "Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/leave",
    "nav_section": "HR & Admin",
    "sort_order": 5,
    "status": "active",
}

NAV_ITEMS = [
    # -- Employee: My Leave (view balances, history, apply, cancel, extend, resumption) ---
    {
        "code": "leave_elm.mine",
        "label": "My Leave",
        "icon": "CalendarCheck",
        "to": "/leave/mine",
        "required_permission": "leave_elm.leave.view_self",
        "sort_order": 10,
    },

    # -- Unit Head / Sanctioning Authority: Queue (review, approve/reject) ---
    {
        "code": "leave_elm.queue",
        "label": "Leave Queue",
        "icon": "ClipboardList",
        "to": "/leave/queue",
        "required_permission": "leave_elm.leave.review",
        "sort_order": 20,
    },

    # -- Admin: Configuration (policy, hierarchy, calendar) ---
    {
        "code": "leave_elm.admin",
        "label": "Admin",
        "icon": "Settings",
        "to": "/leave/admin",
        "required_permission": "leave_elm.policy.manage",
        "sort_order": 30,
    },
]

PERMISSIONS = [
    ("leave_elm.leave.view_self", "View own leave applications and balances"),
    ("leave_elm.leave.apply", "Create and submit new leave application"),
    ("leave_elm.leave.withdraw", "Withdraw pending leave application"),
    ("leave_elm.leave.cancel", "Request cancellation of approved leave"),
    ("leave_elm.leave.extend", "Request extension of ongoing leave"),
    ("leave_elm.leave.resumption", "Submit resumption of duty"),
    ("leave_elm.leave.view", "View all leave applications"),
    ("leave_elm.leave.review", "Review and approve/reject leave requests"),
    ("leave_elm.leave.approve", "Approve leave request"),
    ("leave_elm.leave.reject", "Reject leave request"),
    ("leave_elm.substitute.accept", "Accept substitute responsibility assignment"),
    ("leave_elm.substitute.decline", "Decline substitute responsibility assignment"),
    ("leave_elm.policy.manage", "Manage leave policy parameters and hierarchy configuration"),
    ("leave_elm.calendar.manage", "Manage holiday/RH calendar"),
    ("leave_elm.hierarchy.manage", "Manage leave sanctioning hierarchy"),
    ("leave_elm.record.maintain", "Maintain or correct leave records within authorized scope"),
]

SYSTEM_PERMISSIONS = [
    "leave_elm.year_end.process",
    "leave_elm.sla.reminder",
    "leave_elm.sla.escalate",
]

# Role grants mapping role names to permission codes
ROLE_GRANTS = {
    # Employee roles (Faculty, Staff)
    "faculty": [
        "leave_elm.leave.view_self",
        "leave_elm.leave.apply",
        "leave_elm.leave.withdraw",
        "leave_elm.leave.cancel",
        "leave_elm.leave.extend",
        "leave_elm.leave.resumption",
        "leave_elm.substitute.accept",
        "leave_elm.substitute.decline",
    ],
    "staff": [
        "leave_elm.leave.view_self",
        "leave_elm.leave.apply",
        "leave_elm.leave.withdraw",
        "leave_elm.leave.cancel",
        "leave_elm.leave.extend",
        "leave_elm.leave.resumption",
        "leave_elm.substitute.accept",
        "leave_elm.substitute.decline",
    ],

    # Unit Head role
    "unit_head": [
        "leave_elm.leave.view",
        "leave_elm.leave.review",
        "leave_elm.leave.approve",
        "leave_elm.leave.reject",
        "leave_elm.substitute.accept",
        "leave_elm.substitute.decline",
    ],

    # Establishment processing role (Deputy Registrar Estt.)
    "deputy_registrar_estt": [
        "leave_elm.leave.view",
        "leave_elm.leave.review",
        "leave_elm.leave.approve",
        "leave_elm.leave.reject",
    ],

    # Dean role
    "dean": [
        "leave_elm.leave.view",
        "leave_elm.leave.review",
        "leave_elm.leave.approve",
        "leave_elm.leave.reject",
    ],

    # Registrar role
    "registrar": [
        "leave_elm.leave.view",
        "leave_elm.leave.review",
        "leave_elm.leave.approve",
        "leave_elm.leave.reject",
    ],

    # Director role (self-sanction)
    "director": [
        "leave_elm.leave.view",
        "leave_elm.leave.approve",  # Self-sanction only
    ],

    # Leave Administrator role
    "leave_administrator": [
        "leave_elm.policy.manage",
        "leave_elm.calendar.manage",
        "leave_elm.hierarchy.manage",
        "leave_elm.record.maintain",
    ],
}
