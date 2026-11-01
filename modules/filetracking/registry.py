"""Module registry, nav items, and permissions for File Tracking System (FTS).

Enforces BR-FTS-001, BR-FTS-009, BR-FTS-010, AFR-FTS-005..010.
"""

MODULE = {
    "code": "filetracking",
    "label": "File Tracking",
    "icon": "Folder",
    "base_path": "/filetracking",
    "nav_section": "Office",
    "sort_order": 40,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "filetracking.inbox",
        "label": "Inbox",
        "icon": "Tray",
        "to": "/filetracking/inbox",
        "required_permission": "filetracking.file.view",
        "sort_order": 10,
    },
    {
        "code": "filetracking.outbox",
        "label": "Outbox",
        "icon": "PaperPlaneTilt",
        "to": "/filetracking/outbox",
        "required_permission": "filetracking.file.view",
        "sort_order": 20,
    },
    {
        "code": "filetracking.create",
        "label": "Create File",
        "icon": "FilePlus",
        "to": "/filetracking/create",
        "required_permission": "filetracking.file.create",
        "sort_order": 30,
    },
    {
        "code": "filetracking.archive",
        "label": "Archive",
        "icon": "Archive",
        "to": "/filetracking/archive",
        "required_permission": "filetracking.file.view",
        "sort_order": 40,
    },
    {
        "code": "filetracking.governance",
        "label": "Audit Logs",
        "icon": "ShieldCheck",
        "to": "/filetracking/governance",
        "required_permission": "filetracking.governance.view",
        "sort_order": 50,
    },
]

#: All permissions recognized by FTS
PERMISSIONS = [
    ("filetracking.file.create", "Create and draft institutional files"),
    ("filetracking.file.view", "View associated files and tracking history"),
    ("filetracking.file.forward", "Send or forward files to employees"),
    ("filetracking.file.return", "Return received files to previous sender"),
    ("filetracking.file.archive", "Archive completed circulated files"),
    ("filetracking.governance.view", "View FTS governance usage and audit logs"),
    ("filetracking.governance.manage", "Administer FTS access and role context"),
    ("filetracking.api.integrate", "Invoke FTS workflow-support APIs"),
]

#: Service-only / inter-module permissions
SYSTEM_PERMISSIONS = [
    "filetracking.api.integrate",
]

_EMPLOYEE = [
    "filetracking.file.create",
    "filetracking.file.view",
    "filetracking.file.forward",
    "filetracking.file.return",
    "filetracking.file.archive",
]

#: System Admin has governance oversight only; no operational file actions (BR-FTS-001, AFR-FTS-009)
_ADMIN = [
    "filetracking.governance.view",
    "filetracking.governance.manage",
]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "Dean Academic": _EMPLOYEE,
    "placement_officer": _EMPLOYEE,
    "placement_chairman": _EMPLOYEE,
    "placement_coordinator": _EMPLOYEE,
    "acadadmin": _EMPLOYEE,
    "admin": _ADMIN,
    "system_admin": _ADMIN,
}

