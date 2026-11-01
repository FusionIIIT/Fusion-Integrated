"""Server-side registry declaration for the VMS module (ADR-0010)."""

MODULE = {
    "code": "vms",
    "label": "Visitor Management",
    "icon": "FaIdBadge",
    "base_path": "/vms",
    "nav_section": "Administration",
    "sort_order": 28,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "vms.register",
        "label": "Pre-Register Visit",
        "icon": "FaUserPlus",
        "to": "/vms/register",
        "required_permission": "vms.request.create",
        "sort_order": 10,
    },
    {
        "code": "vms.approvals",
        "label": "Host Approvals",
        "icon": "FaCheckCircle",
        "to": "/vms/approvals",
        "required_permission": "vms.request.approve",
        "sort_order": 20,
    },
    {
        "code": "vms.gate",
        "label": "Gate Validation",
        "icon": "FaDoorOpen",
        "to": "/vms/gate",
        "required_permission": "vms.gate.verify",
        "sort_order": 30,
    },
    {
        "code": "vms.passes",
        "label": "Active Passes & Logs",
        "icon": "FaClipboardList",
        "to": "/vms/passes",
        "required_permission": "vms.pass.view",
        "sort_order": 40,
    },
]

PERMISSIONS = [
    {"code": "vms.request.create", "label": "Pre-register and request visit"},
    {"code": "vms.request.view_self", "label": "View own visit requests"},
    {"code": "vms.request.approve", "label": "Review and decide visit requests as host"},
    {"code": "vms.gate.verify", "label": "Validate visitor passes and log check-in/check-out at gates"},
    {"code": "vms.pass.view", "label": "View active passes, logs, and visitor roster"},
    {"code": "vms.admin.manage", "label": "Manage blacklist, access policies and gates"},
]

ROLE_GRANTS = {
    "admin": [p["code"] for p in PERMISSIONS],
    "faculty": ["vms.request.create", "vms.request.view_self", "vms.request.approve"],
    "staff": ["vms.request.create", "vms.request.view_self", "vms.request.approve"],
    "security": ["vms.gate.verify", "vms.pass.view"],
    "student": ["vms.request.create", "vms.request.view_self"],
}
