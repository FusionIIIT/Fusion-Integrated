"""What the server tells the shell about this module  (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""
MODULE = {
    "code": "elm",
    "label": "Employee Leave Management",
    "icon": "CalendarCheck",
    "base_path": "/elm",
    "nav_section": "HR",
    "sort_order": 10,
    "status": "active",
}

# Empty until client/src/modules/elm/routes.tsx exists; nav_matches_routes checks both.
NAV_ITEMS = []

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("elm.leave_request.view", "See leave requests"),
    ("elm.leave_request.manage", "Create, update and delete leave requests"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = []

_STAFF = [
    "elm.leave_request.view",
    "elm.leave_request.manage",
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "staff": _STAFF,
}
