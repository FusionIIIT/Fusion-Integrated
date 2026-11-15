"""What the server tells the shell about IAA. No screens yet, so no nav items."""
MODULE = {
    "code": "iaa", "label": "Institute Accounts and Audits", "icon": "Receipt",
    "base_path": "/iaa", "nav_section": "Accounts", "sort_order": 40,
    "status": "planned",
}

NAV_ITEMS = []

PERMISSIONS = [
    ("iaa.request.create", "Create and submit one's own expense/voucher requests"),
    ("iaa.request.validate", "Finance validation of submitted requests"),
    ("iaa.request.decide", "Approve or reject finance-validated requests"),
    ("iaa.request.record", "Record internal completion of approved requests"),
]

SYSTEM_PERMISSIONS = []

_BASIC_USER = ["iaa.request.create"]
_FINANCE_STAFF = ["iaa.request.validate", "iaa.request.record"]
_APPROVING_AUTHORITY = ["iaa.request.decide"]

#: Keyed by designation name. Role names follow the IAA Problem Statement section 2.
ROLE_GRANTS = {
    "faculty": _BASIC_USER,
    "staff": _BASIC_USER,
    "Finance Staff": _FINANCE_STAFF,
    "HoD": _APPROVING_AUTHORITY,
    "Dean": _APPROVING_AUTHORITY,
    "Director": _APPROVING_AUTHORITY,
}
