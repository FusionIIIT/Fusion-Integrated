"""Fusion Clean Architecture - File Tracking System permission registry."""

MODULE = {
    "code": "fts",
    "label": "File Tracking System",
    "icon": "Folder",
    "base_path": "/fts",
    "nav_section": "Administrative",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS: list[dict] = [
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
        "icon": "Folder",
        "to": "/fts/drafts",
        "required_permission": "fts.file.view",
        "sort_order": 30,
    },
    {
        "code": "fts.new",
        "label": "New File",
        "icon": "Folder",
        "to": "/fts/new",
        "required_permission": "fts.file.create",
        "sort_order": 40,
    },
]

PERMISSIONS: list[tuple[str, str]] = [
    ("fts.file.view", "View accessible files and tracking history"),
    ("fts.file.create", "Create and save draft files"),
    ("fts.file.review", "Forward and return circulating files"),
    ("fts.file.manage", "Archive completed files"),
]

SYSTEM_PERMISSIONS: list[str] = []

SCOPE_PERMISSIONS: list[str] = []

_EMPLOYEE = [
    "fts.file.view",
    "fts.file.create",
    "fts.file.review",
    "fts.file.manage",
]

ROLE_GRANTS: dict[str, list[str]] = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
}


def get_module_info() -> dict:
    """Get module information."""
    return MODULE.copy()


def get_permissions() -> list[tuple[str, str]]:
    """Get all permissions for the module."""
    return PERMISSIONS.copy()


def get_role_grants() -> dict[str, list[str]]:
    """Get role-to-permission grants mapping."""
    return ROLE_GRANTS.copy()

