"""Fusion module registration for Employee Leave Management."""
MODULE = {"code": "leave_elm", "label": "Employee Leave", "icon": "FaCalendarAlt",
          "base_path": "/leave", "nav_section": "Employee", "sort_order": 30,
          "status": "active"}
NAV_ITEMS = [
    {"code": "leave_elm.workspace", "label": "Leave Management", "icon": "FaCalendarAlt",
     "to": "/leave", "required_permission": "leave_elm.application.apply",
     "sort_order": 10},
    {"code": "leave_elm.review", "label": "Review Leave", "icon": "ClipboardCheck",
     "to": "/leave/review", "required_permission": "leave_elm.application.review",
     "sort_order": 20},
]
PERMISSIONS = [
    ("leave_elm.application.apply", "Apply for and withdraw own leave"),
    ("leave_elm.application.view_self", "View own leave applications"),
    ("leave_elm.application.review", "Review assigned leave applications"),
    ("leave_elm.balance.view", "View own leave balances"),
    ("leave_elm.policy.manage", "Configure leave policy, balances, and approval routes"),
]
SYSTEM_PERMISSIONS = []
_EMPLOYEE = ["leave_elm.application.apply", "leave_elm.application.view_self",
             "leave_elm.balance.view"]
ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "Dean Academic": ["leave_elm.application.review"],
    "HOD (CSE)": ["leave_elm.application.review"],
    "Registrar": ["leave_elm.application.review", "leave_elm.policy.manage"],
    "acadadmin": ["leave_elm.policy.manage"],
}
