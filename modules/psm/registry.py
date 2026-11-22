"""PSM module shell integration and IAM registration descriptor (ADR-0010)."""

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
        "label": "My Indents",
        "icon": "FileText",
        "to": "/psm/indents",
        "required_permission": "psm.indent.view",
        "sort_order": 10,
    },
    {
        "code": "psm.indents.new",
        "label": "Raise Indent",
        "icon": "PlusCircle",
        "to": "/psm/indents/new",
        "required_permission": "psm.indent.create",
        "sort_order": 20,
    },
    {
        "code": "psm.approvals",
        "label": "Approval Queue",
        "icon": "CheckSquare",
        "to": "/psm/approvals",
        "required_permission": "psm.indent.approve_dept",
        "sort_order": 30,
    },
    {
        "code": "psm.purchase_orders",
        "label": "Purchase Orders",
        "icon": "Receipt",
        "to": "/psm/purchase-orders",
        "required_permission": "psm.po.view",
        "sort_order": 40,
    },
    {
        "code": "psm.goods_receipts",
        "label": "Goods Receipts",
        "icon": "Package",
        "to": "/psm/goods-receipts",
        "required_permission": "psm.grn.view",
        "sort_order": 50,
    },
    {
        "code": "psm.inventory",
        "label": "Stores Inventory",
        "icon": "Archive",
        "to": "/psm/inventory",
        "required_permission": "psm.stock.view",
        "sort_order": 60,
    },
    {
        "code": "psm.vendors",
        "label": "Vendor Directory",
        "icon": "Users",
        "to": "/psm/vendors",
        "required_permission": "psm.vendor.view",
        "sort_order": 70,
    },
    {
        "code": "psm.discrepancies",
        "label": "Discrepancy Reports",
        "icon": "AlertTriangle",
        "to": "/psm/discrepancies",
        "required_permission": "psm.discrepancy.manage",
        "sort_order": 80,
    },
]

PERMISSIONS = [
    ("psm.indent.create", "Raise new purchase indents"),
    ("psm.indent.view", "View indents within user or departmental scope"),
    ("psm.indent.approve_dept", "Department-level indent verification and HOD approval"),
    ("psm.indent.approve_ps", "Procurement & Stores admin indent evaluation and routing"),
    ("psm.indent.approve_director", "Director / Registrar high-value indent approval"),
    ("psm.stock.view", "View store inventory and ledger entries"),
    ("psm.stock.manage", "Issue departmental stock and manage adjustments"),
    ("psm.vendor.view", "View vendor master records"),
    ("psm.vendor.manage", "Onboard, vet, verify and update vendor master data"),
    ("psm.po.create", "Generate and issue Purchase Orders"),
    ("psm.po.view", "Inspect Purchase Orders and delivery status"),
    ("psm.grn.create", "Log Goods Receipt Notes upon delivery"),
    ("psm.grn.view", "View Goods Receipt Notes"),
    ("psm.grn.acknowledge", "Indentor goods delivery acknowledgement"),
    ("psm.discrepancy.manage", "Log and resolve discrepancy reports"),
    ("psm.invoice.match", "Perform 3-way invoice matching and payment authorization"),
]

SYSTEM_PERMISSIONS = [
    "psm.indent.auto_escalate",
    "psm.stock.low_stock_sync",
]

_REQUESTOR_PERMS = [
    "psm.indent.create",
    "psm.indent.view",
    "psm.grn.view",
    "psm.grn.acknowledge",
]

ROLE_GRANTS = {
    "staff": _REQUESTOR_PERMS,
    "faculty": _REQUESTOR_PERMS,
    "dept_admin": [
        "psm.indent.view",
        "psm.indent.approve_dept",
        "psm.stock.view",
        "psm.stock.manage",
    ],
    "head_of_department": [
        "psm.indent.view",
        "psm.indent.approve_dept",
        "psm.stock.view",
    ],
    "purchase_officer": [
        "psm.indent.view",
        "psm.indent.approve_ps",
        "psm.vendor.view",
        "psm.vendor.manage",
        "psm.po.create",
        "psm.po.view",
        "psm.grn.view",
        "psm.discrepancy.manage",
    ],
    "store_keeper": [
        "psm.stock.view",
        "psm.stock.manage",
        "psm.po.view",
        "psm.grn.create",
        "psm.grn.view",
        "psm.discrepancy.manage",
    ],
    "accounts_admin": [
        "psm.po.view",
        "psm.grn.view",
        "psm.invoice.match",
    ],
    "director": [
        "psm.indent.view",
        "psm.indent.approve_director",
        "psm.po.view",
    ],
}
