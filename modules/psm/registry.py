MODULE = {
    "code": "psm",
    "label": "Purchase & Stores",
    "icon": "Package",
    "base_path": "/psm",
    "nav_section": "Administration",
    "sort_order": 40,
    "status": "active",
}
NAV_ITEMS = [
    {
        "code": "psm.workspace",
        "label": "Purchase & Stores",
        "icon": "Package",
        "to": "/psm",
        "required_permission": "psm.workspace.view",
        "sort_order": 10,
    },
]
PERMISSIONS = [
    ("psm.workspace.view", "Open the scoped purchase and stores workspace"),
    ("psm.workflow.manage", "Act within the assigned PSM role and department"),
    ("psm.report.view", "Generate reports within assigned PSM scope"),
    ("psm.report.schedule", "Schedule authorized purchase and stores reports"),
]

_ROLES = (
    "employee",
    "department_admin",
    "department_head",
    "ps_admin",
    "accounts",
    "final_authority",
    "committee",
    "vendor",
    "auditor",
)
_BASE_PERMISSIONS = [code for code, _ in PERMISSIONS]
PERMISSIONS += [(f"psm.{role}.manage", f"Act within the {role} PSM role") for role in _ROLES]
ROLE_GRANTS = {f"psm_{role}": [*_BASE_PERMISSIONS, f"psm.{role}.manage"] for role in _ROLES}
