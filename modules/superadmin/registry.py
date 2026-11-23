from __future__ import annotations

MODULE = {
    "code": "superadmin",
    "label": "System Administration",
    "icon": "ShieldCheck",
    "base_path": "/superadmin",
    "nav_section": "System Admin",
    "sort_order": 99,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "superadmin.dashboard",
        "label": "Dashboard",
        "icon": "ChartPie",
        "to": "/superadmin/dashboard",
        "required_permission": "superadmin.dashboard.view",
        "sort_order": 10,
    },
    {
        "code": "superadmin.archival",
        "label": "Archival Governance",
        "icon": "Archive",
        "to": "/superadmin/archival",
        "required_permission": "superadmin.archival.view",
        "sort_order": 20,
    },
    {
        "code": "superadmin.purge",
        "label": "Purge Authorization",
        "icon": "Trash",
        "to": "/superadmin/purge",
        "required_permission": "superadmin.purge.view",
        "sort_order": 30,
    },
    {
        "code": "superadmin.policy",
        "label": "System Policies",
        "icon": "Sliders",
        "to": "/superadmin/policy",
        "required_permission": "superadmin.policy.view",
        "sort_order": 40,
    },
    {
        "code": "superadmin.audit",
        "label": "Audit Logs",
        "icon": "Scroll",
        "to": "/superadmin/audit",
        "required_permission": "superadmin.audit.view",
        "sort_order": 50,
    },
]

PERMISSIONS = [
    ("superadmin.dashboard.view", "View admin dashboard and metrics"),
    ("superadmin.archival.view", "View archived users and historical datasets"),
    ("superadmin.archival.add", "Archive users and historical datasets"),
    ("superadmin.archival.change", "Restore archived users and datasets"),
    ("superadmin.purge.view", "View permanent purge requests"),
    ("superadmin.purge.add", "Initiate and execute permanent purge"),
    ("superadmin.purge.change", "Authorize or reject dual-auth purge"),
    ("superadmin.policy.view", "View system governance policies"),
    ("superadmin.policy.change", "Supersede system governance policies"),
    ("superadmin.audit.view", "View and export compliance audit logs"),
]

SYSTEM_PERMISSIONS = [
    "superadmin.sweep_archival",
    "superadmin.sweep_purge",
    "superadmin.drain_outbox",
]

SCOPE_PERMISSIONS: dict[str, str] = {}

ROLE_GRANTS = {
    "super_admin": [
        "superadmin.dashboard.view",
        "superadmin.archival.view",
        "superadmin.archival.add",
        "superadmin.archival.change",
        "superadmin.purge.view",
        "superadmin.purge.add",
        "superadmin.policy.view",
        "superadmin.policy.change",
        "superadmin.audit.view",
    ],
    "it_head": [
        "superadmin.dashboard.view",
        "superadmin.archival.view",
        "superadmin.purge.view",
        "superadmin.purge.change",
        "superadmin.policy.view",
        "superadmin.audit.view",
    ],
}
