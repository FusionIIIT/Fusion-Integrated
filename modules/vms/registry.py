"""What the server tells the shell about VMS (ADR-0010).

Nav items carry `required_permission` and the server filters before sending.
Icons use Phosphor icons.
"""

MODULE = {
    "code": "vms",
    "label": "Visitor Management",
    "icon": "IdentificationBadge",
    "base_path": "/vms",
    "nav_section": "Campus Operations",
    "sort_order": 15,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "vms.visits",
        "label": "My Visits",
        "icon": "Ticket",
        "to": "/vms/visits",
        "required_permission": "vms.visit.create",
        "sort_order": 10,
    },
    {
        "code": "vms.approvals",
        "label": "Approvals",
        "icon": "CheckSquare",
        "to": "/vms/approvals",
        "required_permission": "vms.visit.approve",
        "sort_order": 20,
    },
    {
        "code": "vms.gate",
        "label": "Gate Terminal",
        "icon": "QrCode",
        "to": "/vms/gate",
        "required_permission": "vms.gate.scan",
        "sort_order": 30,
    },
    {
        "code": "vms.security",
        "label": "Security & Alerts",
        "icon": "ShieldWarning",
        "to": "/vms/security",
        "required_permission": "vms.security.admin",
        "sort_order": 40,
    },
    {
        "code": "vms.muster",
        "label": "Emergency Muster",
        "icon": "UsersThree",
        "to": "/vms/muster",
        "required_permission": "vms.emergency.muster",
        "sort_order": 50,
    },
]

PERMISSIONS = [
    ("vms.visit.create", "Request or register visitor passes"),
    ("vms.visit.approve", "Approve or reject pending visit requests"),
    ("vms.gate.scan", "Scan QR codes, process check-ins and check-outs"),
    ("vms.security.admin", "Manage blacklist and view security alerts"),
    ("vms.emergency.muster", "Trigger and oversee emergency muster roll-call"),
]

SYSTEM_PERMISSIONS = [
    "vms.visit.expire",
    "vms.visit.auto_checkout",
]

_STUDENT = [
    "vms.visit.create",
]

_FACULTY_STAFF = [
    "vms.visit.create",
    "vms.visit.approve",
]

_GUARD = [
    "vms.gate.scan",
]

_SECURITY_OFFICER = [
    "vms.gate.scan",
    "vms.security.admin",
    "vms.emergency.muster",
]

_ADMIN = [
    "vms.visit.create",
    "vms.visit.approve",
    "vms.gate.scan",
    "vms.security.admin",
    "vms.emergency.muster",
]

ROLE_GRANTS = {
    "student": _STUDENT,
    "faculty": _FACULTY_STAFF,
    "staff": _FACULTY_STAFF,
    "security_guard": _GUARD,
    "security_officer": _SECURITY_OFFICER,
    "admin": _ADMIN,
    "Dean": _SECURITY_OFFICER,
}
