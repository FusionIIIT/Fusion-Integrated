"""ELM-owned module registration and role grants for the Fusion IAM."""
MODULE = {
    "code": "employee_leave", "label": "Employee Leave", "icon": "Calendar",
    "base_path": "/elm", "nav_section": "Employee Services",
    "sort_order": 20, "status": "active",
}

_EMPLOYEE = [
    "employee_leave.balance.view_self",
    "employee_leave.request.create",
    "employee_leave.request.view_self",
    "employee_leave.substitute.respond",
]
_UNIT_HEAD = [
    *_EMPLOYEE,
    "employee_leave.task.decide",
    "employee_leave.request.view",
]
_PROCESSOR = [
    *_UNIT_HEAD,
    "employee_leave.request.process",
    "employee_leave.calendar.manage",
    "employee_leave.policy.manage",
]
_ADMIN = [
    *_PROCESSOR,
    "employee_leave.employee.manage",
    "employee_leave.report.view",
    "employee_leave.year_end.process",
]

PERMISSIONS = [
    ("employee_leave.balance.view_self", "View own leave balances"),
    ("employee_leave.request.create", "Apply for and manage own leave"),
    ("employee_leave.request.view_self", "View own leave requests and history"),
    ("employee_leave.request.view", "View leave requests in assigned workflow"),
    ("employee_leave.task.decide", "Act on assigned leave workflow tasks"),
    ("employee_leave.request.process", "Process leave and resumption requests"),
    ("employee_leave.substitute.respond", "Respond to assigned substitute requests"),
    ("employee_leave.calendar.manage", "Maintain and publish leave calendars"),
    ("employee_leave.policy.manage", "Maintain leave policies and approval routes"),
    ("employee_leave.employee.manage", "Maintain employee leave profiles and units"),
    ("employee_leave.report.view", "View leave reports"),
    ("employee_leave.year_end.process", "Run year-end leave processing"),
]

SYSTEM_PERMISSIONS = []

NAV_ITEMS = [
    {"code": "employee_leave.requests", "label": "My Leave",
     "icon": "Calendar", "to": "/elm/requests",
     "required_permission": "employee_leave.request.view_self", "sort_order": 10},
    {"code": "employee_leave.approvals", "label": "Leave Approvals",
     "icon": "ClipboardCheck", "to": "/elm/approvals",
     "required_permission": "employee_leave.task.decide", "sort_order": 20},
    {"code": "employee_leave.admin", "label": "Leave Administration",
     "icon": "Settings", "to": "/elm/admin",
     "required_permission": "employee_leave.policy.manage", "sort_order": 30},
]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "unit_head": _UNIT_HEAD,
    "establishment": _PROCESSOR,
    "leave_administrator": _ADMIN,
    "Registrar": _PROCESSOR,
    "Deputy Registrar (Estt.)": _PROCESSOR,
    "Dean": _PROCESSOR,
    "Director": _ADMIN,
}
