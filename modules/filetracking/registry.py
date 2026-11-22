"""What the server tells the shell about this module (ADR-0010)."""

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

SYSTEM_PERMISSIONS = [
    "filetracking.api.integrate",
]

SCOPE_PERMISSIONS: list[str] = []

_OPERATIONAL = [
    "filetracking.file.create",
    "filetracking.file.view",
    "filetracking.file.forward",
    "filetracking.file.return",
    "filetracking.file.archive",
]

_GOVERNANCE = [
    "filetracking.governance.view",
    "filetracking.governance.manage",
]

ROLE_GRANTS = {
    "faculty": _OPERATIONAL,
    "staff": _OPERATIONAL,
    "Dean Academic": _OPERATIONAL,
    "acadadmin": _OPERATIONAL,
    "placement_officer": _OPERATIONAL,
    "placement_coordinator": _OPERATIONAL,
    "placement_chairman": _OPERATIONAL,
    "admin": _GOVERNANCE,
    "system_admin": _GOVERNANCE,
}


def readiness() -> list[str]:
    """Check whether File Tracking System is ready to operate."""
    return []
