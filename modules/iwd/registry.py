MODULE = {
    "code": "iwd",
    "label": "Institute Works Department",
    "icon": "briefcase",
    "base_path": "/iwd",
    "nav_section": "Facilities",
    "sort_order": 40,
    "status": "active"
}

NAV_ITEMS = [
    {"code": "requests", "label": "Requests", "icon": None, "to": "/iwd/requests", "required_permission": "iwd.request.view_self", "sort_order": 1},
    {"code": "proposals", "label": "Proposals", "icon": None, "to": "/iwd/proposals", "required_permission": "iwd.proposal.manage", "sort_order": 2},
    {"code": "work_orders", "label": "Work Orders", "icon": None, "to": "/iwd/work-orders", "required_permission": "iwd.work_order.issue", "sort_order": 3},
    {"code": "bills", "label": "Bills", "icon": None, "to": "/iwd/bills", "required_permission": "iwd.bill.view", "sort_order": 4},
    {"code": "inventory", "label": "Inventory", "icon": None, "to": "/iwd/inventory", "required_permission": "iwd.inventory.manage", "sort_order": 5}
]

PERMISSIONS = [
    ("iwd.request.create", "Create a departmental request"),
    ("iwd.request.view_self", "View own requests only"),
    ("iwd.request.view_all", "View all requests in IWD"),
    ("iwd.request.admin_approve", "Approve requests as admin"),
    ("iwd.request.hod_approve", "Approve requests as HOD"),
    ("iwd.request.director_approve", "Approve requests as Director"),
    ("iwd.proposal.manage", "Create, edit, and manage proposals"),
    ("iwd.work_order.issue", "Issue new work orders"),
    ("iwd.work.update", "Update existing works/tasks"),
    ("iwd.bill.view", "View bills"),
    ("iwd.bill.manage", "Edit and manage bill details (excluding settlement status)"),
    ("iwd.bill.audit", "Perform audit on bills"),
    ("iwd.bill.settle", "Settle/close bills after approval"),
    ("iwd.inventory.manage", "Manage inventory records (add, update, remove items)"),
    ("iwd.feedback.submit", "Submit feedback forms"),
    ("iwd.sla.view", "View service level agreement details")
]

ROLE_GRANTS = {
    "Admin IWD": ["iwd.request.create", "iwd.request.view_self", "iwd.proposal.manage", "iwd.work_order.issue", "iwd.work.update", "iwd.inventory.manage", "iwd.feedback.submit", "iwd.sla.view", "iwd.request.admin_approve"],
    "Director": ["iwd.request.view_all", "iwd.request.director_approve", "iwd.proposal.manage", "iwd.work_order.issue", "iwd.bill.view", "iwd.inventory.manage", "iwd.sla.view"],
    "HOD (CSE)": ["iwd.request.view_all", "iwd.request.hod_approve", "iwd.proposal.manage", "iwd.work_order.issue", "iwd.work.update", "iwd.inventory.manage"],
    "HOD (Design)": ["iwd.request.view_all", "iwd.request.hod_approve", "iwd.proposal.manage", "iwd.work_order.issue", "iwd.work.update", "iwd.inventory.manage"],
    "Auditor": ["iwd.bill.view", "iwd.bill.audit"],
    "Accounts Admin": ["iwd.bill.view", "iwd.bill.manage", "iwd.bill.settle"],
    "Electrical_AE": ["iwd.request.create", "iwd.request.view_self", "iwd.proposal.manage", "iwd.work_order.issue", "iwd.work.update", "iwd.inventory.manage", "iwd.feedback.submit"]
}
