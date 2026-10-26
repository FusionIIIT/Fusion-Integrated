"""
modules/leave/registry.py
Module registry entry for the Employee Leave Management module.
Follows the pattern established by modules/placement/registry.py.
"""

MODULE = {
    "code": "leave",
    "label": "Leave Management",
    "icon": "CalendarX",
    "base_path": "/leave",
    "description": "Employee leave applications, balances, and policy management.",
    "version": "1.0.0",
}

NAV_ITEMS = [
    {
        "label": "My Leaves",
        "path": "/leave/my",
        "icon": "FileText",
        "permission": "leave.application.view_self",
    },
    {
        "label": "Apply Leave",
        "path": "/leave/apply",
        "icon": "PlusCircle",
        "permission": "leave.application.apply",
    },
    {
        "label": "My Balance",
        "path": "/leave/balance",
        "icon": "BarChart2",
        "permission": "leave.application.view_self",
    },
    {
        "label": "Pending Actions",
        "path": "/leave/queue",
        "icon": "Clock",
        "permission": "leave.unit_head.review",
    },
    {
        "label": "All Applications",
        "path": "/leave/admin/applications",
        "icon": "List",
        "permission": "leave.application.view_all",
    },
    {
        "label": "Holiday Calendar",
        "path": "/leave/admin/calendar",
        "icon": "Calendar",
        "permission": "leave.admin.calendar",
    },
    {
        "label": "Leave Policy",
        "path": "/leave/admin/policy",
        "icon": "Settings",
        "permission": "leave.admin.policy",
    },
    {
        "label": "Record Offline Leave",
        "path": "/leave/admin/offline",
        "icon": "PenTool",
        "permission": "leave.admin.offline_record",
    },
]

PERMISSIONS = [
    {
        "code": "leave.application.apply",
        "label": "Apply for leave",
        "description": "Submit a new leave application.",
    },
    {
        "code": "leave.application.view_self",
        "label": "View own applications",
        "description": "View the current user's own leave applications and balances.",
    },
    {
        "code": "leave.application.view_all",
        "label": "View all applications",
        "description": "View leave applications for all users.",
    },
    {
        "code": "leave.application.withdraw",
        "label": "Withdraw application",
        "description": "Withdraw a pending leave application.",
    },
    {
        "code": "leave.application.cancel",
        "label": "Cancel sanctioned leave",
        "description": "Request cancellation of an already-sanctioned leave.",
    },
    {
        "code": "leave.application.extend",
        "label": "Extend ongoing leave",
        "description": "Request extension of an ongoing EL/COL/VL leave.",
    },
    {
        "code": "leave.substitute.respond",
        "label": "Respond to substitute request",
        "description": "Accept or decline a substitute nomination.",
    },
    {
        "code": "leave.unit_head.review",
        "label": "Review as unit head",
        "description": "Approve, recommend, or reject applications in the unit head queue.",
    },
    {
        "code": "leave.admin.manage",
        "label": "Admin: manage all",
        "description": "Full administrative access to leave management.",
    },
    {
        "code": "leave.admin.calendar",
        "label": "Admin: manage holiday calendar",
        "description": "Create/update holiday and restricted-holiday entries.",
    },
    {
        "code": "leave.admin.policy",
        "label": "Admin: manage leave policy",
        "description": "Create/update leave policy (entitlements per year).",
    },
    {
        "code": "leave.admin.offline_record",
        "label": "Admin: record offline leave",
        "description": "Record a leave that was sanctioned offline/manually.",
    },
]

# Maps role slug -> list of permission codes granted
ROLE_GRANTS: dict[str, list[str]] = {
    "employee": [
        "leave.application.apply",
        "leave.application.view_self",
        "leave.application.withdraw",
        "leave.application.cancel",
        "leave.application.extend",
        "leave.substitute.respond",
    ],
    "unit_head": [
        "leave.application.apply",
        "leave.application.view_self",
        "leave.application.withdraw",
        "leave.application.cancel",
        "leave.application.extend",
        "leave.substitute.respond",
        "leave.application.view_all",
        "leave.unit_head.review",
    ],
    "registrar": [
        "leave.application.view_all",
        "leave.unit_head.review",
    ],
    "dean": [
        "leave.application.view_all",
        "leave.unit_head.review",
    ],
    "director": [
        "leave.application.view_all",
        "leave.unit_head.review",
    ],
    "leave_admin": [
        "leave.application.apply",
        "leave.application.view_self",
        "leave.application.withdraw",
        "leave.application.cancel",
        "leave.application.extend",
        "leave.substitute.respond",
        "leave.application.view_all",
        "leave.unit_head.review",
        "leave.admin.manage",
        "leave.admin.calendar",
        "leave.admin.policy",
        "leave.admin.offline_record",
    ],
}
