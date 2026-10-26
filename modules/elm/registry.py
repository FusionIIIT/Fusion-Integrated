"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""
MODULE = {
    "code": "leave_elm", "label": "Leave Management", "icon": "CalendarBlank",
    "base_path": "/leave", "nav_section": "Leave", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "leave.apply", "label": "Apply for Leave", "icon": "PencilSimple", "to": "/leave/apply", "required_permission": "leave_elm.application.apply", "sort_order": 10},
    {"code": "leave.mine", "label": "My Applications", "icon": "ListChecks", "to": "/leave/mine", "required_permission": "leave_elm.application.view", "sort_order": 20},
    {"code": "leave.balance", "label": "Leave Balance", "icon": "Scales", "to": "/leave/balance", "required_permission": "leave_elm.balance.view", "sort_order": 30},
    {"code": "leave.approvals", "label": "Approvals", "icon": "UserCheck", "to": "/leave/approvals", "required_permission": "leave_elm.application.approve", "sort_order": 50},
    {"code": "leave.types", "label": "Leave Types", "icon": "Gear", "to": "/leave/types", "required_permission": "leave_elm.policy.manage", "sort_order": 60},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("leave_elm.application.view", "View leave applications"),
    ("leave_elm.application.apply", "Apply for leave"),
    ("leave_elm.application.approve", "Approve leave applications"),
    ("leave_elm.balance.view", "View leave balances"),
    ("leave_elm.policy.manage", "Manage leave policies"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = []

_EMPLOYEE = ["leave_elm.application.view", "leave_elm.balance.view"]
_LEAVE_APPROVER = ["leave_elm.application.view", "leave_elm.application.approve", "leave_elm.balance.view"]
_LEAVE_ADMIN = ["leave_elm.application.view", "leave_elm.balance.view", "leave_elm.policy.manage"]

#: Keyed by the role name as it exists in globals_designation.
ROLE_GRANTS = {
    "Employee": _EMPLOYEE,
    "Leave Approver": _LEAVE_APPROVER,
    "Leave Admin": _LEAVE_ADMIN,
}
