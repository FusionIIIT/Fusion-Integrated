"""Fusion module metadata and grants for Employee Leave Management."""

MODULE = {
    "code": "elm",
    "label": "Employee Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/elm",
    "nav_section": "Human Resources",
    "sort_order": 20,
    # Supplied generated source includes domain/models only; APIs and screens are absent.
    "status": "planned",
}

PERMISSIONS = [
    ("elm.leave_request.approve", "Approve or reject a leave request"),
    ("elm.leave_request.create", "Create a leave request"),
    ("elm.leave_request.update", "Withdraw or request cancellation of a leave request"),
]

SYSTEM_PERMISSIONS = []

_EMPLOYEE = ["elm.leave_request.create", "elm.leave_request.update"]
_APPROVER = ["elm.leave_request.approve"]

ROLE_GRANTS = {
    "Dean": _APPROVER,
    "Deputy Registrar (Estt.)": _APPROVER,
    "Director": _APPROVER,
    "Employee": _EMPLOYEE,
    "Registrar": _APPROVER,
    "Unit Head": _APPROVER,
}
