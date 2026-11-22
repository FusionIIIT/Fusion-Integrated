"""Visitor Management System (VMS) registry and navigation manifest."""

from __future__ import annotations

MODULE = {
    "code": "vms",
    "label": "Visitor Management",
    "icon": "UserCheck",
    "base_path": "/vms",
    "nav_section": "Operations",
    "sort_order": 35,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "vms.passes",
        "label": "Visitor Passes",
        "icon": "IdentificationCard",
        "to": "/vms/passes",
        "required_permission": "vms.visit.view",
        "sort_order": 10,
    },
    {
        "code": "vms.approvals",
        "label": "Host Approvals",
        "icon": "Checks",
        "to": "/vms/approvals",
        "required_permission": "vms.visit.decide",
        "sort_order": 20,
    },
    {
        "code": "vms.gate",
        "label": "Security Gate Scanner",
        "icon": "QrCode",
        "to": "/vms/gate",
        "required_permission": "vms.gate.validate",
        "sort_order": 30,
    },
    {
        "code": "vms.blacklist",
        "label": "Blacklist Registry",
        "icon": "ShieldWarning",
        "to": "/vms/blacklist",
        "required_permission": "vms.blacklist.manage",
        "sort_order": 40,
    },
    {
        "code": "vms.emergency",
        "label": "Emergency Muster",
        "icon": "WarningCircle",
        "to": "/vms/emergency",
        "required_permission": "vms.emergency.trigger",
        "sort_order": 50,
    },
    {
        "code": "vms.analytics",
        "label": "Visitor Analytics",
        "icon": "ChartBar",
        "to": "/vms/analytics",
        "required_permission": "vms.analytics.view",
        "sort_order": 60,
    },
]

PERMISSIONS = [
    ("vms.visit.view", "View visitor passes and status"),
    ("vms.visit.preregister", "Pre-register a visitor"),
    ("vms.visit.decide", "Approve or reject visit requests"),
    ("vms.preauth.manage", "Manage recurring visitor pre-authorizations"),
    ("vms.gate.validate", "Scan and validate visitor passes at gate"),
    ("vms.gate.override", "Authorize manual gate override"),
    ("vms.blacklist.manage", "Manage blacklist and safe-list entries"),
    ("vms.emergency.trigger", "Trigger emergency evacuation muster"),
    ("vms.emergency.rollcall", "Mark visitor roll call during muster"),
    ("vms.analytics.view", "View visitor traffic reports and analytics"),
    ("vms.policy.manage", "Version and configure access policies"),
    ("vms.bulk.manage", "Manage bulk event visitor uploads"),
]

SYSTEM_PERMISSIONS = [
    "vms.request.expire",
    "vms.visit.auto_checkout",
]

_SECURITY = [
    "vms.visit.view",
    "vms.gate.validate",
    "vms.emergency.rollcall",
]

_HOST = [
    "vms.visit.view",
    "vms.visit.decide",
    "vms.preauth.manage",
]

_ADMIN = [
    "vms.visit.view",
    "vms.visit.preregister",
    "vms.visit.decide",
    "vms.preauth.manage",
    "vms.gate.validate",
    "vms.gate.override",
    "vms.blacklist.manage",
    "vms.emergency.trigger",
    "vms.emergency.rollcall",
    "vms.analytics.view",
    "vms.policy.manage",
    "vms.bulk.manage",
]

ROLE_GRANTS = {
    "student": _HOST,
    "faculty": _HOST,
    "staff": _HOST,
    "security_personnel": _SECURITY,
    "admin": _ADMIN,
    "Super Admin": _ADMIN,
}
