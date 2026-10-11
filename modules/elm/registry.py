MODULE = {"code": "leave_elm", "label": "Leave Management", "icon": "CalendarBlank", "base_path": "/leave", "nav_section": "Leave", "sort_order": 20, "status": "active"}

NAV_ITEMS = [
    {"code": "leave.apply", "label": "Apply for Leave", "icon": "PencilSimple", "to": "/leave/apply", "required_permission": "leave_elm.application.apply", "sort_order": 10},
    {"code": "leave.mine", "label": "My Applications", "icon": "ListChecks", "to": "/leave/mine", "required_permission": "leave_elm.application.view", "sort_order": 20},
    {"code": "leave.balance", "label": "Leave Balance", "icon": "Scales", "to": "/leave/balance", "required_permission": "leave_elm.balance.view", "sort_order": 30},
    {"code": "leave.approvals", "label": "Approvals", "icon": "UserCheck", "to": "/leave/approvals", "required_permission": "leave_elm.application.approve", "sort_order": 50},
    {"code": "leave.types", "label": "Leave Types", "icon": "Gear", "to": "/leave/types", "required_permission": "leave_elm.policy.manage", "sort_order": 60},
]

"""Permissions this module recognises. No nav: it has no screens of its own."""

PERMISSIONS = [
    ("leave_elm.application.view", "View leave applications"),
    ("leave_elm.application.apply", "Apply for leave"),
    ("leave_elm.application.approve", "Approve leave applications"),
    ("leave_elm.balance.view", "View leave balances"),
    ("leave_elm.policy.manage", "Manage leave policies"),
]

SYSTEM_PERMISSIONS = []

_EMPLOYEE = ["leave_elm.application.view", "leave_elm.application.apply", "leave_elm.balance.view"]
_LEAVE_APPROVER = ["leave_elm.application.view", "leave_elm.application.approve", "leave_elm.balance.view"]
_LEAVE_ADMIN = ["leave_elm.application.view", "leave_elm.balance.view", "leave_elm.policy.manage"]

#: Keyed by the role name.
ROLE_GRANTS = {
    "Employee": _EMPLOYEE,
    "Leave Approver": _LEAVE_APPROVER,
    "Leave Admin": _LEAVE_ADMIN,
}
