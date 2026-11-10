"""
What the server tells the shell about the PSM module (ADR-0010).
Navigation items carry required_permission and are filtered server-side.
"""

MODULE_CODE = "psm"

MODULE = {
    "code": "psm",
    "label": "Purchase & Stores",
    "icon": "ShoppingCart",
    "base_path": "/psm",
    "nav_section": "Administration",
    "sort_order": 25,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "psm.indents",
        "label": "Purchase Indents",
        "icon": "FileText",
        "to": "/psm/indents",
        "required_permission": "psm.indent.view",
        "sort_order": 10,
    },
    {
        "code": "psm.vendors",
        "label": "Vendor Management",
        "icon": "Buildings",
        "to": "/psm/vendors",
        "required_permission": "psm.vendor.view",
        "sort_order": 20,
    },
    {
        "code": "psm.purchase_orders",
        "label": "Purchase Orders",
        "icon": "Receipt",
        "to": "/psm/purchase-orders",
        "required_permission": "psm.po.view",
        "sort_order": 30,
    },
    {
        "code": "psm.stock",
        "label": "Stock & Inventory",
        "icon": "Package",
        "to": "/psm/stock",
        "required_permission": "psm.stock.view",
        "sort_order": 40,
    },
]

PERMISSION_CATALOGUE = [
    ("psm.indent.view", "View accessible purchase indents"),
    ("psm.indent.create", "Create and submit purchase indents"),
    ("psm.indent.manage", "Review, recommend, and approve indents"),
    ("psm.indent.view_all", "View all institute indents across departments"),
    ("psm.vendor.view", "View vendor directory"),
    ("psm.vendor.manage", "Register and verify vendors"),
    ("psm.po.view", "View purchase orders and GRNs"),
    ("psm.po.create", "Issue purchase orders and record GRNs"),
    ("psm.stock.view", "View inventory and stock levels"),
    ("psm.stock.manage", "Manage inventory and initiate transfers"),
]

PERMISSIONS = PERMISSION_CATALOGUE

_STANDARD_USER = [
    "psm.indent.view",
    "psm.indent.create",
    "psm.vendor.view",
    "psm.stock.view",
]

_STORE_OFFICER = [
    "psm.indent.view",
    "psm.indent.view_all",
    "psm.indent.create",
    "psm.indent.manage",
    "psm.vendor.view",
    "psm.vendor.manage",
    "psm.po.view",
    "psm.po.create",
    "psm.stock.view",
    "psm.stock.manage",
]

_PS_ADMIN = list(dict(PERMISSION_CATALOGUE).keys())

ROLE_GRANTS = {
    "student": _STANDARD_USER,
    "faculty": _STANDARD_USER,
    "staff": _STANDARD_USER,
    "store_officer": _STORE_OFFICER,
    "purchase_officer": _STORE_OFFICER,
    "ps_admin": _PS_ADMIN,
    "admin": _PS_ADMIN,
    "Director": _PS_ADMIN,
    "Dean": _STORE_OFFICER,
}
