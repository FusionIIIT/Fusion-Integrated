"""Registry and role definitions for Purchase and Stores Management (PSM)."""

MODULE = {
    "code": "psm",
    "label": "Purchase and Stores Management",
    "icon": "ShoppingCart",
    "base_path": "/psm",
    "nav_section": "Administration",
    "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = []

PERMISSIONS = [
    ("psm.indent.create", "Create and submit purchase indents"),
    ("psm.indent.view", "View accessible indents and tracking"),
    ("psm.indent.approve", "Review, recommend, or approve indents"),
    ("psm.stock.manage", "Check, reserve, issue, and transfer stock"),
    ("psm.po.manage", "Create, issue, and manage purchase orders and vendors"),
    ("psm.invoice.manage", "Verify invoices and perform 3-way matching"),
    ("psm.payment.manage", "Process and release vendor payments"),
]

SYSTEM_PERMISSIONS = []

_REQUESTOR = [
    "psm.indent.create",
    "psm.indent.view",
]

_ADMIN = [
    "psm.indent.create",
    "psm.indent.view",
    "psm.indent.approve",
    "psm.stock.manage",
    "psm.po.manage",
    "psm.invoice.manage",
    "psm.payment.manage",
]

ROLE_GRANTS = {
    "student": _REQUESTOR,
    "faculty": _REQUESTOR,
    "staff": _REQUESTOR,
    "Department Admin": _ADMIN,
    "Department Head": _ADMIN,
    "Procurement Admin": _ADMIN,
    "Accounts Admin": _ADMIN,
    "Director": _ADMIN,
    "Registrar": _ADMIN,
}
