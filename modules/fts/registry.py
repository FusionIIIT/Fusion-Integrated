"""Fusion Clean Architecture - File Tracking System permission registry."""

MODULE = {
    "code": "fts",
    "label": "File Tracking System",
    "icon": "faFolder",
    "base_path": "/fts",
    "nav_section": "Administrative",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS: list[dict] = [
    {
        "code": "fts.inbox",
        "label": "Inbox",
        "icon": "FaClipboardCheck",
        "to": "/fts/inbox",
        "sort_order": 10,
    },
    {
        "code": "fts.outbox",
        "label": "Outbox",
        "icon": "FaExternalLinkAlt",
        "to": "/fts/outbox",
        "sort_order": 20,
    },
    {
        "code": "fts.drafts",
        "label": "Drafts",
        "icon": "FaClipboardList",
        "to": "/fts/drafts",
        "sort_order": 30,
    },
    {
        "code": "fts.new",
        "label": "New File",
        "icon": "FaFileSignature",
        "to": "/fts/new",
        "sort_order": 40,
    },
]

PERMISSIONS: list[tuple[str, str]] = []

ROLE_GRANTS: dict[str, list[str]] = {}


def get_module_info() -> dict:
    """Get module information."""
    return MODULE.copy()


def get_permissions() -> list[tuple[str, str]]:
    """Get all permissions for the module."""
    return PERMISSIONS.copy()


def get_role_grants() -> dict[str, list[str]]:
    """Get role-to-permission grants mapping."""
    return ROLE_GRANTS.copy()
