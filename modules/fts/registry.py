"""Module registration and RBAC manifest for File Tracking System (FTS)."""

MODULE = {
    "code": "fts",
    "label": "File Tracking",
    "icon": "FolderNotch",
    "base_path": "/fts",
    "nav_section": "File Tracking",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "fts.inbox",
        "label": "Inbox",
        "icon": "Tray",
        "to": "/fts/inbox",
        "required_permission": "fts.file.view",
        "sort_order": 10,
    },
    {
        "code": "fts.outbox",
        "label": "Outbox",
        "icon": "PaperPlaneTilt",
        "to": "/fts/outbox",
        "required_permission": "fts.file.view",
        "sort_order": 20,
    },
    {
        "code": "fts.drafts",
        "label": "Drafts",
        "icon": "FileDotted",
        "to": "/fts/drafts",
        "required_permission": "fts.file.create",
        "sort_order": 30,
    },
    {
        "code": "fts.create",
        "label": "Create File",
        "icon": "PlusCircle",
        "to": "/fts/create",
        "required_permission": "fts.file.create",
        "sort_order": 40,
    },
    {
        "code": "fts.governance",
        "label": "Governance & Audit",
        "icon": "ShieldCheck",
        "to": "/fts/governance",
        "required_permission": "fts.governance.view",
        "sort_order": 50,
    },
]

PERMISSIONS = [
    ("fts.file.create", "Create files and manage pre-circulation drafts"),
    ("fts.file.forward", "Forward active files to other employees"),
    ("fts.file.return", "Return received active files to sender"),
    ("fts.file.archive", "Archive completed circulated files as owner"),
    ("fts.file.view", "View associated files in Inbox/Outbox and tracking history"),
    ("fts.governance.view", "View FTS system usage, security, and audit logs"),
    ("fts.integration.access", "Invoke FTS workflow-support APIs"),
    ("fts.notification.dispatch", "System notification dispatch"),
]

SYSTEM_PERMISSIONS = [
    "fts.integration.access",
    "fts.notification.dispatch",
]

_EMPLOYEE_PERMISSIONS = [
    "fts.file.create",
    "fts.file.forward",
    "fts.file.return",
    "fts.file.archive",
    "fts.file.view",
]

_ADMIN_PERMISSIONS = [
    "fts.governance.view",
]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE_PERMISSIONS,
    "staff": _EMPLOYEE_PERMISSIONS,
    "Assistant Professor": _EMPLOYEE_PERMISSIONS,
    "Associate Professor": _EMPLOYEE_PERMISSIONS,
    "Professor": _EMPLOYEE_PERMISSIONS,
    "Junior Assistant": _EMPLOYEE_PERMISSIONS,
    "Junior Superintendent": _EMPLOYEE_PERMISSIONS,
    "Registrar": _EMPLOYEE_PERMISSIONS,
    "Dean Academic": _EMPLOYEE_PERMISSIONS,
    "Director": _EMPLOYEE_PERMISSIONS,
    "admin": _ADMIN_PERMISSIONS,
    "System Administrator": _ADMIN_PERMISSIONS,
}
