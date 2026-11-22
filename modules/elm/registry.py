"""Permissions this module recognises."""

PERMISSIONS = [
    ("elm.leave_type.view", "List Leave Types"),
    ("elm.balance.view", "List Leave Balances"),
    ("elm.application.view", "List Leave Applications"),
    ("elm.application.create", "Create Leave Application"),
    ("elm.application.delete", "Withdraw Leave Application"),
]

SYSTEM_PERMISSIONS = []

_STAFF = ["elm.leave_type.view", "elm.balance.view", "elm.application.view", "elm.application.create", "elm.application.delete"]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "faculty": _STAFF,
    "staff": _STAFF,
}

MODULE = {
    "code": "elm",
    "label": "Employee Leave",
    "icon": "CalendarCheck",
    "base_path": "/elm",
    "nav_section": "Leave",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "elm.mine", "label": "My Leave", "icon": "CalendarCheck", "to": "/elm/mine", "required_permission": "elm.application.view", "sort_order": 10},
]
