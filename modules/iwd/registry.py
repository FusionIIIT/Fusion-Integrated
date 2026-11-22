MODULE = {
    "code": "iwd",
    "label": "Institute Work Department",
    "icon": "Wrench",
    "base_path": "/iwd",
    "nav_section": "Operations",
    "sort_order": 40,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "iwd.complaints",
        "label": "Maintenance Complaints",
        "icon": "ListBullets",
        "to": "/iwd/complaints",
        "required_permission": "iwd.complaint.view",
        "sort_order": 10,
    },
    {
        "code": "iwd.assigned",
        "label": "Engineer Queue",
        "icon": "ClipboardText",
        "to": "/iwd/assigned",
        "required_permission": "iwd.complaint.update",
        "sort_order": 20,
    },
    {
        "code": "iwd.approvals",
        "label": "Approvals & Estimates",
        "icon": "Checks",
        "to": "/iwd/approvals",
        "required_permission": "iwd.estimate.manage",
        "sort_order": 30,
    },
    {
        "code": "iwd.inventory",
        "label": "Inventory & Procurement",
        "icon": "Package",
        "to": "/iwd/inventory",
        "required_permission": "iwd.inventory.view",
        "sort_order": 40,
    },
    {
        "code": "iwd.verification",
        "label": "Work Verification",
        "icon": "ShieldCheck",
        "to": "/iwd/verification",
        "required_permission": "iwd.verification.manage",
        "sort_order": 50,
    },
    {
        "code": "iwd.billing",
        "label": "Audit & Settlement",
        "icon": "CurrencyInr",
        "to": "/iwd/billing",
        "required_permission": "iwd.bill.manage",
        "sort_order": 60,
    },
]

PERMISSIONS = [
    ("iwd.complaint.create", "Submit maintenance complaints"),
    ("iwd.complaint.view", "View maintenance complaints"),
    ("iwd.complaint.update", "Update and assess complaints"),
    ("iwd.estimate.create", "Submit repair estimates"),
    ("iwd.estimate.view", "View repair estimates"),
    ("iwd.estimate.update", "Update and resubmit estimates"),
    ("iwd.estimate.manage", "Approve and manage estimates"),
    ("iwd.committee_review.create", "Record committee review"),
    ("iwd.inventory.view", "View inventory stock"),
    ("iwd.inventory.update", "Issue materials"),
    ("iwd.procurement.manage", "Manage quotations and bidding"),
    ("iwd.verification.manage", "Verify completed work"),
    ("iwd.bill.create", "Submit final bills"),
    ("iwd.bill.view", "View final bills"),
    ("iwd.bill.manage", "Audit final bills"),
    ("iwd.settlement.manage", "Manage payment settlement"),
    ("iwd.feedback.create", "Submit complaint feedback"),
    ("iwd.feedback.view", "View complaint feedback"),
]

SYSTEM_PERMISSIONS = []

_EMPLOYEE = [
    "iwd.complaint.create",
    "iwd.complaint.view",
    "iwd.feedback.create",
]

_ENGINEER = [
    "iwd.complaint.view",
    "iwd.complaint.update",
    "iwd.estimate.create",
    "iwd.estimate.view",
    "iwd.estimate.update",
    "iwd.bill.create",
    "iwd.bill.view",
    "iwd.feedback.view",
]

_ADMIN = [
    "iwd.complaint.view",
    "iwd.estimate.view",
    "iwd.estimate.manage",
    "iwd.inventory.view",
    "iwd.inventory.update",
    "iwd.procurement.manage",
    "iwd.feedback.view",
]

_DEPT_HEAD = [
    "iwd.complaint.view",
    "iwd.estimate.view",
    "iwd.estimate.manage",
    "iwd.committee_review.create",
    "iwd.verification.manage",
    "iwd.feedback.view",
]

_DIRECTOR = [
    "iwd.complaint.view",
    "iwd.estimate.view",
    "iwd.estimate.manage",
    "iwd.settlement.manage",
    "iwd.feedback.view",
]

_AUDITOR = [
    "iwd.complaint.view",
    "iwd.estimate.view",
    "iwd.bill.view",
    "iwd.bill.manage",
]

_ACCOUNTS = [
    "iwd.bill.view",
    "iwd.settlement.manage",
]

_DEAN = [
    "iwd.complaint.view",
    "iwd.estimate.view",
    "iwd.feedback.view",
]

ROLE_GRANTS = {
    "student": _EMPLOYEE,
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "employee": _EMPLOYEE,
    "engineer": _ENGINEER,
    "iwd_admin": _ADMIN,
    "department_head": _DEPT_HEAD,
    "director": _DIRECTOR,
    "auditor": _AUDITOR,
    "accounts": _ACCOUNTS,
    "Dean": _DEAN,
    "dean": _DEAN,
}
