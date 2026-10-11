"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""
MODULE = {
    "code": "leave_management", "label": "Leave Management", "icon": "Calendar",
    "base_path": "/leave", "nav_section": "HR/Admin", "sort_order": 15,
    "status": "active",
}

NAV_ITEMS = [
    # Placeholder for future leave-related navigation items
    {"code": "leave.dashboard", "label": "My Leave Status",
     "icon": "Calendar", "to": "/leave/mine",
     "required_permission": "leave_management.application.view_self",
     "sort_order": 5},
    {"code": "leave.requests", "label": "Request Leave",
     "icon": "PlusCircle", "to": "/leave/new",
     "required_permission": "leave_management.application.create",
     "sort_order": 10},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("leave_management.application.view_self", "View own leave applications"),
    ("leave_management.application.create", "Submit a leave request"),
    ("leave_management.application.view", "View all leave applications"),
    ("leave_management.application.review", "Review and sanction leave applications"),
    ("leave_management.application.delete", "Withdraw a leave application"),
    ("leave_management.application.auto_withdraw", "System auto-withdrawal"),
    ("leave_management.balance.view", "View leave balances"),
    ("leave_management.balance.manage", "Manage leave balances (Admin)"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = [
    "leave_management.application.auto_withdraw",
]

# Placeholder roles/grants structure, mirroring placement/registry.py
# Actual roles will be defined by the system's RBAC structure.
ROLE_GRANTS = {
    "employee": ["leave_management.application.view_self", "leave_management.application.create"],
    "manager": ["leave_management.application.view", "leave_management.application.review"],
    "admin": [code for code, _ in PERMISSIONS if code not in SYSTEM_PERMISSIONS],
}
