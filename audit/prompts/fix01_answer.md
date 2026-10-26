```python
"""Registry for ELM module in Fusion platform (ADR-0010 compliant).
Model: Qwen 2.5 Coder 14B implementation.
"""
MODULE = {
    "code": "leave",
    "label": "Leave Management (ELM)",
    "icon": "CalendarBlank",
    "base_path": "/leave",
    "nav_section": "Human Resources",
    "sort_order": 15,
    "status": "active",
}

NAV_ITEMS = [
    # Employee self-service (EL-UC-001, 007, 008, 009, 010, 012, 013)
    {"code": "leave.apply", "label": "Apply Leave", "icon": "CalendarPlus",[15D[K
"CalendarPlus",
     "to": "/leave/apply", "required_permission": "leave.req[10D[K
"leave.request.create", "sort_order": 10},
    {"code": "leave.history", "label": "My Leaves & Balances", "icon": "Clo[4D[K
"ClockCounterClockwise",
     "to": "/leave/history", "required_permission": "leave.request.view_sel[23D[K
"leave.request.view_self", "sort_order": 20},
    {"code": "leave.substitute_tasks", "label": "Substitute Tasks", "icon":[7D[K
"icon": "UserSwitch",
     "to": "/leave/substitute", "required_permission": "leave.substitute.re[20D[K
"leave.substitute.review", "sort_order": 30},

    # Reviewer / Authority Work queues (EL-UC-003, 004, 005, 011)
    {"code": "leave.unit_head", "label": "Unit Head Approvals", "icon": "Ch[3D[K
"CheckSquare",
     "to": "/leave/unit-head", "required_permission": "leave.request.review[21D[K
"leave.request.review", "sort_order": 40},
    {"code": "leave.establishment", "label": "Establishment Routing", "icon[5D[K
"icon": "FileSearch",
     "to": "/leave/establishment", "required_permission": "leave.request.as[17D[K
"leave.request.assign", "sort_order": 50},
    {"code": "leave.sanctioning", "label": "Sanction Decisions", "icon": "S[2D[K
"Stamp",
     "to": "/leave/sanction", "required_permission": "leave.request.approve[22D[K
"leave.request.approve", "sort_order": 60},
    {"code": "leave.resumption_queue", "label": "Resumption Reviews", "icon[5D[K
"icon": "ArrowCounterClockwise",
     "to": "/leave/resumptions", "required_permission": "leave.resumption.r[19D[K
"leave.resumption.review", "sort_order": 70},

    # Administration (EL-UC-014, 015, 016, 017, 018)
    {"code": "leave.admin_policy", "label": "ELM Policy & Calendars", "icon[5D[K
"icon": "GearSix",
     "to": "/leave/admin/policy", "required_permission": "leave.policy.mana[18D[K
"leave.policy.manage", "sort_order": 80},
    {"code": "leave.offline_sync", "label": "Offline Leave Sync", "icon": "[1D[K
"Database",
     "to": "/leave/admin/offline-sync", "required_permission": "leave.recor[12D[K
"leave.record.manage", "sort_order": 90},
]

PERMISSIONS = [
    ("leave.request.create", "Apply for leave or request extension of ongoi[5D[K
ongoing leave"),
    ("leave.request.view_self", "View own leave history, balances, and expo[4D[K
export own applications"),
    ("leave.request.view", "View leave requests in your approval queue"),
    ("leave.request.delete", "Withdraw a pending request or request cancell[7D[K
cancellation of approved leave"),
    ("leave.request.review", "Unit Head review, decision or recommendation"[15D[K
recommendation"),
    ("leave.request.assign", "Establishment verification and routing to the[3D[K
the sanctioning authority"),
    ("leave.request.approve", "Make final sanctioning decisions"),
    ("leave.resumption.create", "Submit duty resumption after EL, COL or VL[2D[K
VL"),
    ("leave.resumption.review", "Review duty resumption declarations"),
    ("leave.substitute.review", "Accept or decline a nominated substitute r[1D[K
responsibility"),
    ("leave.policy.manage", "Configure leave policy, hierarchy and SLA thre[4D[K
thresholds"),
    ("leave.calendar.publish", "Maintain and publish the holiday and RH cal[3D[K
calendar"),
    ("leave.record.manage", "Record already-sanctioned offline leave and ma[2D[K
maintain leave records"),
]

_EMPLOYEE_BASE = [
    "leave.request.create", "leave.request.view_self", "leave.request.delet[20D[K
"leave.request.delete",
    "leave.resumption.create", "leave.substitute.review",
]

_UNIT_HEAD_PERMS = [*_EMPLOYEE_BASE, "leave.request.review"]
_ESTABLISHMENT_PERMS = [*_EMPLOYEE_BASE, "leave.request.assign", "leave.rec[10D[K
"leave.record.manage"]
_SANCTION_PERMS = [*_EMPLOYEE_BASE, "leave.request.approve", "leave.resumpt[14D[K
"leave.resumption.review"]
_ADMIN_PERMS = [
    "leave.request.view_self", "leave.request.view", "leave.policy.manage",[22D[K
"leave.policy.manage",
    "leave.calendar.publish", "leave.record.manage"
]

ROLE_GRANTS = {
