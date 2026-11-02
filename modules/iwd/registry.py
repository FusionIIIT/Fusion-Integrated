"""Registry for the Institute Works Department (IWD) module (ADR-0010)."""

MODULE = {
    "code": "iwd",
    "label": "Institute Works Department",
    "icon": "Wrench",
    "base_path": "/iwd",
    "nav_section": "Administration",
    "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "iwd.requests",
        "label": "Work Requests",
        "icon": "ClipboardText",
        "to": "/iwd/requests",
        "required_permission": "iwd.work_request.view",
        "sort_order": 10,
    },
    {
        "code": "iwd.new_request",
        "label": "Submit Request",
        "icon": "PlusCircle",
        "to": "/iwd/new-request",
        "required_permission": "iwd.work_request.create",
        "sort_order": 20,
    },
    {
        "code": "iwd.approvals",
        "label": "Approvals",
        "icon": "CheckSquare",
        "to": "/iwd/approvals",
        "required_permission": "iwd.work_request.approve",
        "sort_order": 30,
    },
    {
        "code": "iwd.contractors",
        "label": "Contractors",
        "icon": "Buildings",
        "to": "/iwd/contractors",
        "required_permission": "iwd.contractor.manage",
        "sort_order": 40,
    },
    {
        "code": "iwd.inventory",
        "label": "Inventory",
        "icon": "Package",
        "to": "/iwd/inventory",
        "required_permission": "iwd.inventory.manage",
        "sort_order": 50,
    },
    {
        "code": "iwd.reports",
        "label": "Reports",
        "icon": "ChartBar",
        "to": "/iwd/reports",
        "required_permission": "iwd.report.view",
        "sort_order": 60,
    },
]

PERMISSIONS = [
    ("iwd.work_request.view", "View work requests"),
    ("iwd.work_request.create", "Submit a new work request"),
    ("iwd.work_request.approve", "Approve or reject work requests"),
    ("iwd.work_request.assign", "Assign work requests to engineers"),
    ("iwd.work_request.close", "Close and complete work requests"),
    ("iwd.contractor.manage", "Manage contractor records"),
    ("iwd.inventory.manage", "Manage materials and inventory"),
    ("iwd.budget.view", "View budget allocations"),
    ("iwd.budget.manage", "Manage and update budgets"),
    ("iwd.report.view", "View IWD operational reports"),
]

_REQUESTER = [
    "iwd.work_request.view",
    "iwd.work_request.create",
]

_ENGINEER = [
    "iwd.work_request.view",
    "iwd.work_request.create",
    "iwd.inventory.manage",
]

_SUPERVISOR = [
    "iwd.work_request.view",
    "iwd.work_request.create",
    "iwd.work_request.approve",
    "iwd.work_request.assign",
    "iwd.contractor.manage",
    "iwd.inventory.manage",
    "iwd.budget.view",
    "iwd.report.view",
]

_DIRECTOR = [
    *_SUPERVISOR,
    "iwd.work_request.close",
    "iwd.budget.manage",
]

ROLE_GRANTS = {
    "iwd_requester": _REQUESTER,
    "iwd_engineer": _ENGINEER,
    "iwd_supervisor": _SUPERVISOR,
    "iwd_director": _DIRECTOR,
}

