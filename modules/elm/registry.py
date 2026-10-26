"""What the server tells the shell about the Employee Leave Management module (ADR-0010)."""

MODULE = {
    "code": "leave_elm",
    "label": "Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/leave",
    "nav_section": "Leave",
    "sort_order": 20,
    "status": "active",
}


def _nav(code, label, icon, to, permission, sort_order):
    return {
        "code": code,
        "label": label,
        "icon": icon,
        "to": to,
        "required_permission": permission,
        "sort_order": sort_order,
    }


NAV_ITEMS = [
    _nav("leave.apply", "Apply for Leave", "PencilSimple", "/leave/apply",
         "leave_elm.application.apply", 10),
    _nav("leave.mine", "My Applications", "ListChecks", "/leave/mine",
         "leave_elm.application.view", 20),
    _nav("leave.balance", "Leave Balance", "Scales", "/leave/balance",
         "leave_elm.balance.view", 30),
    _nav("leave.approvals", "Approvals", "UserCheck", "/leave/approvals",
         "leave_elm.application.approve", 50),
    _nav("leave.types", "Leave Types", "Gear", "/leave/types",
         "leave_elm.policy.manage", 60),
]

PERMISSIONS = [
    ("leave_elm.application.view", "View leave applications"),
    ("leave_elm.application.apply", "Apply for leave"),
    ("leave_elm.application.approve", "Approve leave applications"),
    ("leave_elm.balance.view", "View leave balances"),
    ("leave_elm.policy.manage", "Manage leave policies"),
]

SYSTEM_PERMISSIONS = []

_EMPLOYEE = ["leave_elm.application.view", "leave_elm.application.apply", "leave_elm.balance.view"]
_LEAVE_APPROVER = [
    "leave_elm.application.view", "leave_elm.application.approve", "leave_elm.balance.view",
]
_LEAVE_ADMIN = ["leave_elm.application.view", "leave_elm.balance.view", "leave_elm.policy.manage"]

#: Keyed by the designation name; each key is a role.
ROLE_GRANTS = {
    "Employee": _EMPLOYEE,
    "Leave Approver": _LEAVE_APPROVER,
    "Leave Admin": _LEAVE_ADMIN,
}
