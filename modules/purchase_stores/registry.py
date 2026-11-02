"""PSM module registry and authorization declarations."""

MODULE = {
    "code": "purchase_stores",
    "label": "Purchase and Stores",
    "icon": "FaBoxesStacked",
    "base_path": "/purchase-stores",
    "nav_section": "Administration",
    "sort_order": 40,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "purchase_stores.indents",
        "label": "Purchase Indents",
        "icon": "FaFileInvoice",
        "to": "/purchase-stores/indents",
        "required_permission": "purchase_stores.indent.view_self",
        "sort_order": 10,
    },
    {
        "code": "purchase_stores.stock",
        "label": "Stock and Transfers",
        "icon": "FaBoxesStacked",
        "to": "/purchase-stores/stock",
        "required_permission": "purchase_stores.stock.view",
        "sort_order": 20,
    },
    {
        "code": "purchase_stores.procurement",
        "label": "Procurement",
        "icon": "FaCartShopping",
        "to": "/purchase-stores/procurement",
        "required_permission": "purchase_stores.po.view",
        "sort_order": 30,
    },
]

PERMISSIONS = [
    ("purchase_stores.indent.create", "Create and submit purchase indents"),
    ("purchase_stores.indent.view_self", "View own purchase indents"),
    ("purchase_stores.indent.view", "View department and institutional indents"),
    ("purchase_stores.indent.review", "Review, recommend, and decide indents"),
    ("purchase_stores.indent.withdraw", "Withdraw or cancel a permitted indent"),
    ("purchase_stores.stock.view", "View stock availability and reservations"),
    ("purchase_stores.stock.manage", "Manage stock, issues, and transfers"),
    ("purchase_stores.vendor.manage", "Onboard and maintain vendors"),
    ("purchase_stores.tender.manage", "Publish tenders and evaluate bids"),
    ("purchase_stores.po.view", "View purchase orders and delivery schedules"),
    ("purchase_stores.po.manage", "Create and issue purchase orders"),
    ("purchase_stores.receipt.manage", "Inspect deliveries and record GRNs"),
    ("purchase_stores.discrepancy.manage", "Manage discrepancy, return, and warranty cases"),
    ("purchase_stores.invoice.manage", "Verify invoices and process vendor payments"),
    ("purchase_stores.report.view", "View and generate purchase and stores reports"),
    ("purchase_stores.audit.view", "Review purchase and financial audit records"),
    ("purchase_stores.policy.manage", "Configure approval thresholds and SLA policy"),
]

_EMPLOYEE = [
    "purchase_stores.indent.create",
    "purchase_stores.indent.view_self",
    "purchase_stores.indent.withdraw",
]
_DEPARTMENT_ADMIN = [
    *_EMPLOYEE,
    "purchase_stores.indent.view",
    "purchase_stores.indent.review",
    "purchase_stores.stock.view",
    "purchase_stores.stock.manage",
    "purchase_stores.receipt.manage",
    "purchase_stores.discrepancy.manage",
    "purchase_stores.report.view",
]
_PROCUREMENT = [
    "purchase_stores.indent.view",
    "purchase_stores.indent.review",
    "purchase_stores.stock.view",
    "purchase_stores.stock.manage",
    "purchase_stores.vendor.manage",
    "purchase_stores.tender.manage",
    "purchase_stores.po.view",
    "purchase_stores.po.manage",
    "purchase_stores.receipt.manage",
    "purchase_stores.discrepancy.manage",
    "purchase_stores.report.view",
    "purchase_stores.policy.manage",
]
_DEPARTMENT_HEAD = [
    "purchase_stores.indent.view",
    "purchase_stores.indent.review",
    "purchase_stores.stock.view",
    "purchase_stores.receipt.manage",
    "purchase_stores.discrepancy.manage",
    "purchase_stores.report.view",
]

ROLE_GRANTS = {
    "student": _EMPLOYEE,
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "department_admin": _DEPARTMENT_ADMIN,
    "department_head": _DEPARTMENT_HEAD,
    "procurement_admin": _PROCUREMENT,
    "accounts_admin": [
        "purchase_stores.indent.view",
        "purchase_stores.po.view",
        "purchase_stores.invoice.manage",
        "purchase_stores.report.view",
        "purchase_stores.audit.view",
    ],
    "director": ["purchase_stores.indent.view", "purchase_stores.indent.review"],
    "registrar": [
        "purchase_stores.indent.view",
        "purchase_stores.indent.review",
        "purchase_stores.policy.manage",
    ],
    "procurement_committee": [
        "purchase_stores.indent.view",
        "purchase_stores.tender.manage",
    ],
    "auditor": [
        "purchase_stores.indent.view",
        "purchase_stores.po.view",
        "purchase_stores.report.view",
        "purchase_stores.audit.view",
    ],
}
