"""Module registry, permissions, navigation, and role grants for IWD (ADR-0010)."""

MODULE = {
    "code": "iwd",
    "label": "Institute Work Department",
    "icon": "Wrench",
    "base_path": "/iwd",
    "nav_section": "Facilities",
    "sort_order": 25,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "iwd.complaints",
        "label": "My Complaints",
        "icon": "ClipboardText",
        "to": "/iwd/complaints",
        "required_permission": "iwd.complaint.view",
        "sort_order": 10,
    },
    {
        "code": "iwd.new_complaint",
        "label": "Submit Complaint",
        "icon": "PlusCircle",
        "to": "/iwd/submit",
        "required_permission": "iwd.complaint.create",
        "sort_order": 20,
    },
    {
        "code": "iwd.approvals",
        "label": "Approvals Inbox",
        "icon": "CheckSquare",
        "to": "/iwd/approvals",
        "required_permission": "iwd.estimate.review",
        "sort_order": 30,
    },
    {
        "code": "iwd.inventory",
        "label": "Inventory & Stock",
        "icon": "Package",
        "to": "/iwd/inventory",
        "required_permission": "iwd.inventory.manage",
        "sort_order": 40,
    },
    {
        "code": "iwd.billing",
        "label": "Bills & Audit",
        "icon": "Receipt",
        "to": "/iwd/billing",
        "required_permission": "iwd.bill.review",
        "sort_order": 50,
    },
]

PERMISSIONS = [
    ("iwd.complaint.create", "Submit a maintenance complaint"),
    ("iwd.complaint.view", "View submitted or assigned maintenance complaints"),
    ("iwd.complaint.update", "Record technical assessment or execution progress"),
    ("iwd.estimate.create", "Prepare and submit repair cost estimates"),
    ("iwd.estimate.review", "Review and decide on repair estimates across approval tiers"),
    (
        "iwd.inventory.manage",
        "Check inventory levels and coordinate material issues or procurement",
    ),
    ("iwd.work.verify", "Verify completed physical repair work quality"),
    ("iwd.bill.create", "Submit final repair bills and invoices"),
    ("iwd.bill.review", "Audit and approve bills for payment settlement"),
    ("iwd.feedback.create", "Submit feedback, ratings, and post-repair incident reports"),
    ("iwd.feedback.view", "View recorded feedback for quality monitoring"),
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
    "iwd.bill.create",
    "iwd.feedback.view",
]

_IWD_ADMIN = [
    "iwd.complaint.view",
    "iwd.estimate.review",
    "iwd.inventory.manage",
    "iwd.feedback.view",
]

_DEPT_HEAD = [
    "iwd.complaint.view",
    "iwd.estimate.review",
    "iwd.work.verify",
    "iwd.feedback.view",
]

_DEAN = [
    "iwd.complaint.view",
    "iwd.feedback.view",
]

_DIRECTOR = [
    "iwd.complaint.view",
    "iwd.estimate.review",
    "iwd.bill.review",
    "iwd.feedback.view",
]

_AUDITOR = [
    "iwd.complaint.view",
    "iwd.bill.review",
    "iwd.feedback.view",
]

_ACCOUNTS = [
    "iwd.complaint.view",
    "iwd.bill.review",
]

ROLE_GRANTS = {
    "student": _EMPLOYEE,
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "iwd_engineer": _ENGINEER,
    "iwd_admin": _IWD_ADMIN,
    "iwd_department_head": _DEPT_HEAD,
    "iwd_dean": _DEAN,
    "iwd_director": _DIRECTOR,
    "iwd_auditor": _AUDITOR,
    "iwd_accounts": _ACCOUNTS,
}
