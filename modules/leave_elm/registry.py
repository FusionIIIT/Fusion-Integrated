"""What the server tells the shell about this module (ADR-0010).

For a pure-API module with no screens, NAV_ITEMS is empty.
"""
MODULE = {
    "code": "leave_elm", "label": "Leave Management", "icon": "CalendarCheck",
    "base_path": "/leave", "nav_section": "Leave", "sort_order": 10,
    "status": "active",
}

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("leave_elm.application.view", "See leave applications"),
    ("leave_elm.application.apply", "Submit a leave application"),
    ("leave_elm.application.approve", "Approve or reject a leave application"),
]

SYSTEM_PERMISSIONS = []

#: Employee can view and apply for leave.
_EMPLOYEE = [
    "leave_elm.application.view",
    "leave_elm.application.apply",
]

#: Leave Approver can view and approve/reject leave applications.
_APPROVER = [
    "leave_elm.application.view",
    "leave_elm.application.approve",
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "Employee": _EMPLOYEE,
    "Leave Approver": _APPROVER,
}
