"""Server-side navigation and permission declarations for FTS (ADR-0010)."""

MODULE = {
    "code": "fts",
    "label": "File Tracking",
    "icon": "FolderSimple",
    "base_path": "/fts",
    "nav_section": "Workflow",
    "sort_order": 25,
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
        "required_permission": "fts.file.view",
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
]

PERMISSIONS = [
    ("fts.file.view", "View accessible files, inbox, outbox, and tracking history"),
    ("fts.file.create", "Create new files and save drafts"),
    ("fts.file.update", "Forward, return, edit drafts, and add notes to files"),
    ("fts.file.delete", "Discard uncirculated draft files"),
    ("fts.file.manage", "Archive completed files and manage file configurations"),
    ("fts.audit.view", "View FTS system usage and security audit logs"),
]

SYSTEM_PERMISSIONS: list[str] = []

SCOPE_PERMISSIONS: list[str] = []

_EMPLOYEE = [
    "fts.file.view",
    "fts.file.create",
    "fts.file.update",
    "fts.file.delete",
    "fts.file.manage",
]

_ADMIN = [
    "fts.audit.view",
]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "admin": _ADMIN,
    "system_admin": _ADMIN,
}
