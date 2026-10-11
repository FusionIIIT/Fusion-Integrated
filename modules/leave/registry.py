MODULE = {
    "code": "leave_elm",
    "label": "Leave Management",
    "icon": "FaCalendarCheck",
    "base_path": "/leave",
    "nav_section": "Leave",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "leave.applications", "label": "Leave Requests", "icon": "FaCalendarAlt", "to": "/leave/applications", "required_permission": "leave_elm.application.view", "sort_order": 10},
    {"code": "leave.approvals", "label": "Sanction Queue", "icon": "FaCheckCircle", "to": "/leave/approvals", "required_permission": "leave_elm.application.approve", "sort_order": 20},
]

PERMISSIONS = [
    ("leave_elm.application.view", "View leave requests and balances"),
    ("leave_elm.application.apply", "Submit a leave request"),
    ("leave_elm.application.approve", "Sanction or reject a leave request"),
]

ROLE_GRANTS = {
    "Employee": ["leave_elm.application.view", "leave_elm.application.apply"],
    "faculty": ["leave_elm.application.view", "leave_elm.application.apply"],
    "staff": ["leave_elm.application.view", "leave_elm.application.apply"],
    "Leave Approver": ["leave_elm.application.view", "leave_elm.application.approve"],
}
