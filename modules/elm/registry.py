"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending, so
a screen a role cannot use never reaches the browser.
"""
MODULE = {
    "code": "elm", "label": "Leave Management", "icon": "CalendarBlank",
    "base_path": "/leave", "nav_section": "Leave", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "elm.apply", "label": "Apply for Leave",
     "icon": "FilePlus", "to": "/leave/apply",
     "required_permission": "elm.application.create", "sort_order": 10},
    {"code": "elm.mine", "label": "My Leaves",
     "icon": "Suitcase", "to": "/leave/mine",
     "required_permission": "elm.application.view", "sort_order": 20},
    {"code": "elm.balance", "label": "My Balances",
     "icon": "Scales", "to": "/leave/balance",
     "required_permission": "elm.balance.view", "sort_order": 30},
    {"code": "elm.approvals", "label": "Approvals",
     "icon": "Checks", "to": "/leave/approvals",
     "required_permission": "elm.application.approve", "sort_order": 40},
    {"code": "elm.admin", "label": "Leave Setup",
     "icon": "SlidersHorizontal", "to": "/leave/admin",
     "required_permission": "elm.policy.manage", "sort_order": 90},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("elm.application.create", "Submit a leave application"),
    ("elm.balance.accrue", "Annual accrual task"),
    ("elm.application.view", "See leave applications"),
    ("elm.application.approve", "Approve or reject a leave application"),
    ("elm.application.delete", "Withdraw or cancel your own leave application"),
    ("elm.balance.view", "See leave balances"),
    ("elm.balance.manage", "Grant and adjust leave balances"),
    ("elm.policy.manage", "Configure leave types, holidays and entitlements"),
]

#: Performed by the accrual task, so no designation holds them.
SYSTEM_PERMISSIONS = [
    "elm.balance.accrue",
]

#: Enforced by narrowing a queryset rather than by refusing a request (BR-11).
SCOPE_PERMISSIONS = [
    "elm.application.view",
    "elm.balance.view",
]

_EMPLOYEE = [
    "elm.application.create",
    "elm.application.view",
    "elm.application.delete",
    "elm.balance.view",
]

_APPROVER = [
    "elm.application.view",
    "elm.application.approve",
    "elm.balance.view",
]

_ADMIN = [
    "elm.application.view",
    "elm.application.approve",
    "elm.balance.view",
    "elm.balance.manage",
    "elm.policy.manage",
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    # faculty and staff are held by definition, not assigned (Step 3.4).
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "Employee": _EMPLOYEE,
    "Leave Approver": _APPROVER,
    "Leave Administrator": _ADMIN,
}


def readiness() -> list[str]:
    """What must exist before the module can serve a first request (Step 7.5)."""
    from django.db import DatabaseError

    problems: list[str] = []
    try:
        from modules.elm.models import LeaveType
        if not LeaveType.objects.exists():
            problems.append(
                "no leave types are configured — run 'manage.py seed_leave_policy'")
    except DatabaseError:
        problems.append("the elm tables are not migrated — run 'make migrate'")
    return problems
