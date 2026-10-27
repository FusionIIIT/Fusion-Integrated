# Task: update modules/leave/registry.py with valid permissions and IAM designations, and add tests in modules/leave/tests/test_registry.py

Context:
See pattern in `modules/placement/registry.py`.
Leave application state machine uses permissions:
- `leave_management.application.create`
- `leave_management.application.respond`
- `leave_management.application.review`
- `leave_management.application.delete`
- `leave_management.application.view`
- `leave_management.application.view_self`
- `leave_management.application.auto_withdraw` (SYSTEM_PERMISSIONS)
- `leave_management.balance.view`
- `leave_management.balance.manage`

Real IAM designation names to use in `ROLE_GRANTS` (from docs/02-iam and globals_designation):
- "Junior Assistant" (employee / applicant)
- "faculty" (employee / applicant)
- "HOD (CSE)" (unit head approver)
- "Dean Academic" (sanctioning authority)
- "Registrar" (sanctioning authority / admin)
- "Director" (director sanctioning authority)
- "acadadmin" (establishment / leave admin)

Since client routes are not yet mounted, set `NAV_ITEMS = []` so that `ops/checks/nav_matches_routes.py` passes without errors.

## In modules/leave/registry.py:
```python
"""What the server tells the shell about this module (ADR-0010)."""

MODULE = {
    "code": "leave_management",
    "label": "Leave Management",
    "icon": "Calendar",
    "base_path": "/leave",
    "nav_section": "HR/Admin",
    "sort_order": 15,
    "status": "active",
}

NAV_ITEMS = []

PERMISSIONS = [
    ("leave_management.application.view_self", "View own leave applications"),
    ("leave_management.application.create", "Submit a leave request or cancellation"),
    ("leave_management.application.respond", "Respond to substitute nomination"),
    ("leave_management.application.view", "View all leave applications"),
    ("leave_management.application.review", "Review and sanction leave applications"),
    ("leave_management.application.delete", "Withdraw a leave application"),
    ("leave_management.application.auto_withdraw", "System auto-withdrawal"),
    ("leave_management.balance.view", "View leave balances"),
    ("leave_management.balance.manage", "Manage leave balances (Admin)"),
]

SYSTEM_PERMISSIONS = [
    "leave_management.application.auto_withdraw",
]

_EMPLOYEE_BASE = [
    "leave_management.application.view_self",
    "leave_management.application.create",
    "leave_management.application.respond",
    "leave_management.application.delete",
    "leave_management.balance.view",
]

_REVIEWER = [
    *_EMPLOYEE_BASE,
    "leave_management.application.view",
    "leave_management.application.review",
]

_ADMIN = [
    *_REVIEWER,
    "leave_management.balance.manage",
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "Junior Assistant": _EMPLOYEE_BASE,
    "faculty": _EMPLOYEE_BASE,
    "HOD (CSE)": _REVIEWER,
    "Dean Academic": _REVIEWER,
    "Registrar": _ADMIN,
    "Director": _REVIEWER,
    "acadadmin": _ADMIN,
}
```

## In modules/leave/tests/test_registry.py:
Write tests:
1. `test_module_metadata`: checks MODULE dict has code "leave_management", status "active".
2. `test_all_permissions_have_description`: every entry in PERMISSIONS is a (code, description) tuple with non-empty strings.
3. `test_every_user_permission_is_granted`: every permission in PERMISSIONS not in SYSTEM_PERMISSIONS is granted in at least one role in ROLE_GRANTS.
4. `test_all_role_grants_are_declared`: every code in ROLE_GRANTS values exists in PERMISSIONS.
5. `test_system_permissions_not_granted_to_roles`: no code in SYSTEM_PERMISSIONS appears in any role in ROLE_GRANTS.

Output COMPLETE files only. Blank lines must be completely empty (no spaces). No explanations, no placeholders, no TODOs.
