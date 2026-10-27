"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending â€”
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""

MODULE = {
    "code": "leave",
    "label": "Leave",
    "icon": "Calendar",
    "base_path": "/leave",
    "nav_section": "Leave",
    "sort_order": 20,
    "status": "planned",
}

NAV_ITEMS = [
    {"code": "leave.request", "label": "Leave Request",
     "icon": "PencilAlt", "to": "/leave/request",
     "required_permission": "leave.request", "sort_order": 10},
    {"code": "leave.balance", "label": "Leave Balance",
     "icon": "Clock", "to": "/leave/balance",
     "required_permission": "leave.balance.view", "sort_order": 20},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("leave.request", "Request for leave"),
    ("leave.balance.view", "View leave balance"),
]
