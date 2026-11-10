"""Fusion module and permission declarations; operational roles remain distinct."""

from modules.iaa.domain.rules import Role

MODULE = {
    "code": "institute_accounts_audits",
    "label": "Institute Accounts and Audits",
    "icon": "Bank",
    "base_path": "/iaa",
    "nav_section": "Institute Accounts",
    "sort_order": 30,
    "status": "active",
}
NAV_ITEMS = [
    {
        "code": "iaa.workspace",
        "label": "Accounts and Audits",
        "icon": "Bank",
        "to": "/iaa/workspace",
        "required_permission": "institute_accounts_audits.workspace.access",
        "sort_order": 10,
    }
]
PERMISSIONS = [
    (
        "institute_accounts_audits.workspace.access",
        "Open IAA; actions require an assigned active IAA role",
    )
]
ROLE_GRANTS = {role.value: ["institute_accounts_audits.workspace.access"] for role in Role}
SYSTEM_PERMISSIONS = []
SCOPE_PERMISSIONS = []
