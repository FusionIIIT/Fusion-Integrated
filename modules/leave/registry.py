"""What the server tells the shell about this module (ADR-0010).

The permission codes are the ones the platform already reserved for `leave` in
docs/02-iam/permission-catalog.md, so the IAM seeds this module without a new
taxonomy: ELM's finer authority (Unit Head, Establishment, Dean, Registrar,
Director) is *routing*, resolved from the configured hierarchy, not a separate
permission per office. BR-EL-019 states the route is resolved from applicant,
unit, designation, category and current configuration — that is exactly where
"who may decide this one" belongs.
"""
MODULE = {
    "code": "leave", "label": "Leave Management", "icon": "FaCalendarAlt",
    "base_path": "/leave", "nav_section": "Leave", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "leave.mine", "label": "My Leave", "icon": "FaUserCheck",
     "to": "/leave/mine",
     "required_permission": "leave.request.view_self", "sort_order": 10},
    {"code": "leave.approvals", "label": "Approvals", "icon": "FaCheckDouble",
     "to": "/leave/approvals",
     "required_permission": "leave.request.approve", "sort_order": 20},
    {"code": "leave.records", "label": "Leave Records", "icon": "FaClipboardList",
     "to": "/leave/records",
     "required_permission": "leave.request.view", "sort_order": 30},
    {"code": "leave.admin", "label": "Leave Administration", "icon": "FaCog",
     "to": "/leave/admin",
     "required_permission": "leave.type.manage", "sort_order": 40},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("leave.request.view_self", "View own leave requests and balance"),
    ("leave.request.create", "Apply for, extend, resume and print own leave"),
    ("leave.request.delete", "Withdraw or cancel own request"),
    ("leave.request.view", "View leave requests, within scope"),
    ("leave.request.approve", "Decide a routed leave task"),
    ("leave.balance.update", "Adjust a leave balance or synchronise a record"),
    ("leave.type.manage",
     "Configure leave policy, hierarchy, holiday calendar and SLA thresholds"),
]

#: Performed by a task or a management command, so no designation holds them.
SYSTEM_PERMISSIONS: list[str] = []

#: Held by anyone with a leave-scoped view: visibility is narrowed, not refused.
SCOPE_PERMISSIONS: list[str] = []

_EMPLOYEE_SELF = [
    "leave.request.view_self",
    "leave.request.create",
    "leave.request.delete",
]

_APPROVER = [*_EMPLOYEE_SELF, "leave.request.view", "leave.request.approve"]

_ADMIN = [
    *_EMPLOYEE_SELF,
    "leave.request.view",
    "leave.request.approve",
    "leave.balance.update",
    "leave.type.manage",
]

#: Keyed by the designation code as it exists in globals_designation / IamRole.
ROLE_GRANTS = {
    # -- every employee manages their own leave --------------------------------
    "faculty": _EMPLOYEE_SELF,
    "staff": _EMPLOYEE_SELF,
    "Professor": _EMPLOYEE_SELF,
    "Associate Professor": _EMPLOYEE_SELF,
    "Assistant Professor": _EMPLOYEE_SELF,
    "Junior Assistant": _EMPLOYEE_SELF,
    "Senior Assistant": _EMPLOYEE_SELF,
    "Upper Division Clerk": _EMPLOYEE_SELF,

    # -- Unit Heads: final for CL/RH, recommendation for higher sanction --------
    "HOD (CSE)": _APPROVER,
    "HOD (ECE)": _APPROVER,
    "HOD (ME)": _APPROVER,
    "HOD (Design)": _APPROVER,
    "HOD (NS)": _APPROVER,
    "HOD (Liberal Arts)": _APPROVER,

    # -- Establishment, competent authorities ---------------------------------
    "Deputy Registrar": _APPROVER,
    "dracad": _APPROVER,
    "Dean Academic": _APPROVER,
    "Registrar": _APPROVER,
    "Director": _APPROVER,

    # -- Leave Administrator: the ELM configuration and record owner ----------
    "acadadmin": _ADMIN,
}
