"""What the server tells the shell about ELM (ADR-0010), and who holds which
permission. The codes match the `leave` section of the permission catalogue.

`status` stays "planned" until the module is complete; see
docs/03-platform/module-authoring-guide.md, step 8.
"""
MODULE = {
    "code": "leave", "label": "Leave", "icon": "CalendarBlank",
    "base_path": "/leave", "nav_section": "Leave", "sort_order": 20,
    "status": "planned",
}

NAV_ITEMS = [
    {"code": "leave.apply", "label": "Apply for Leave", "icon": "PlusCircle",
     "to": "/leave/apply", "required_permission": "leave.request.create",
     "sort_order": 10},
    {"code": "leave.mine", "label": "My Leave", "icon": "ListBullets",
     "to": "/leave/mine", "required_permission": "leave.request.view_self",
     "sort_order": 20},
    {"code": "leave.approvals", "label": "Approvals", "icon": "Checks",
     "to": "/leave/approvals", "required_permission": "leave.request.view",
     "sort_order": 30},
]

PERMISSIONS = [
    ("leave.request.view_self", "View own leave requests and balance"),
    ("leave.request.create", "Apply for leave"),
    ("leave.request.delete", "Withdraw own pending request"),
    ("leave.request.view", "View leave requests awaiting a decision"),
    ("leave.request.review", "Recommend leave, and decide CL/RH as Unit Head"),
    ("leave.request.approve", "Sanction or reject leave as Sanctioning Authority"),
]

SYSTEM_PERMISSIONS = []

_EMPLOYEE = [
    "leave.request.view_self",
    "leave.request.create",
    "leave.request.delete",
]

#: BR-EL-016/017. A Unit Head is also an employee who applies for leave.
_UNIT_HEAD = [*_EMPLOYEE, "leave.request.view", "leave.request.review"]

#: BR-EL-018/019. Final authority for SCL, EL, COL and VL.
_SANCTIONING = [*_EMPLOYEE, "leave.request.view", "leave.request.approve"]

#: Keyed by the designation name as it exists in globals_designation. The
#: hierarchy is not configurable yet (BR-EL-019), so it is fixed here.
ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "HOD (CSE)": _UNIT_HEAD,
    "HOD (ECE)": _UNIT_HEAD,
    "HOD (ME)": _UNIT_HEAD,
    "HOD (SM)": _UNIT_HEAD,
    "HOD (Design)": _UNIT_HEAD,
    "HOD (NS)": _UNIT_HEAD,
    "Registrar": _SANCTIONING,
    "Director": _SANCTIONING,
}
