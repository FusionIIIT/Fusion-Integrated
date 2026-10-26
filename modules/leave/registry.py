"""What the server tells the shell about this module (ADR-0010)."""
MODULE = {
    "code": "leave_cell", "label": "Leave Management", "icon": "Calendar",
    "base_path": "/leave", "nav_section": "HR", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "leave_cell.balances", "label": "Leave Balances",
     "icon": "ClipboardList", "to": "/leave/balances",
     "required_permission": "leave_cell.balances.view", "sort_order": 5},
    {"code": "leave_cell.requests", "label": "Leave Requests",
     "icon": "CalendarCheck", "to": "/leave/requests",
     "required_permission": "leave_cell.requests.manage", "sort_order": 10},
]

PERMISSIONS = [
    ("leave_cell.balances.view", "View leave balances"),
    ("leave_cell.requests.manage", "Create and manage leave requests"),
    # Dedicated HR permissions for viewing all employees' data
    ("leave_cell.balances.view_all", "View all employees' leave balances"),
    ("leave_cell.requests.view_all", "View all employees' leave requests"),
    ("leave_cell.requests.sanction", "Sanction, approve, or reject leave requests"),
]

ROLE_GRANTS = {
    "employee": ["leave_cell.balances.view", "leave_cell.requests.manage"],
    "unit_head": [
        "leave_cell.balances.view",
        "leave_cell.requests.manage",
        "leave_cell.requests.view_all",
        "leave_cell.requests.sanction",
    ],
    "sanctioning_authority": [
        "leave_cell.balances.view",
        "leave_cell.requests.manage",
        "leave_cell.requests.view_all",
        "leave_cell.requests.sanction",
    ],
    "hr": [
        "leave_cell.balances.view",
        "leave_cell.requests.manage",
        "leave_cell.balances.view_all",
        "leave_cell.requests.view_all",
        "leave_cell.requests.sanction",
    ],
}
