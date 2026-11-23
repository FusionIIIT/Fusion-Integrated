"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""
MODULE = {
    "code": "psm",
    "label": "Purchase & Store",
    "icon": "FaClipboardList",
    "base_path": "/psm",
    "nav_section": "Store & Purchase",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "psm.indents",
        "label": "Purchase Indents",
        "icon": "FaClipboardCheck",
        "to": "/psm/indents",
        "required_permission": "",
        "sort_order": 10,
    },
    {
        "code": "psm.stock",
        "label": "Stock Items",
        "icon": "FaThLarge",
        "to": "/psm/stock",
        "required_permission": "",
        "sort_order": 20,
    },
]

PERMISSIONS = [
    ("psm.indent.view", "View purchase indents"),
    ("psm.indent.create", "Create purchase indents"),
    ("psm.stock.view", "View stock items"),
]

SYSTEM_PERMISSIONS = []

_FACULTY = ["psm.indent.view", "psm.indent.create", "psm.stock.view"]
_STAFF = ["psm.indent.view", "psm.indent.create", "psm.stock.view"]
_STUDENT = ["psm.indent.view"]

ROLE_GRANTS = {
    "faculty": _FACULTY,
    "staff": _STAFF,
    "student": _STUDENT,
}
