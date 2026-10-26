```python
NAV_ITEMS = [
    {"code": "leave.apply", "label": "Apply Leave", "icon": "CalendarPlus",
     "to": "/leave/apply", "required_permission": "leave.request.create", "sort_order": 10},
    {"code": "leave.history", "label": "My Leaves & Balances", "icon": "ClockCounterClockwise",
     "to": "/leave/history", "required_permission": "leave.request.view_self", "sort_order": 20},
    {"code": "leave.substitute_tasks", "label": "Substitute Tasks", "icon": "UserSwitch",
     "to": "/leave/substitute", "required_permission": "leave.substitute.review", "sort_order": 30},
    {"code": "leave.unit_head", "label": "Unit Head Approvals", "icon": "CheckSquare",
     "to": "/leave/unit-head", "required_permission": "leave.request.review", "sort_order": 40},
    {"code": "leave.establishment", "label": "Establishment Routing", "icon": "FileSearch",
     "to": "/leave/establishment", "required_permission": "leave.request.assign", "sort_order": 50},
    {"code": "leave.sanctioning", "label": "Sanction Decisions", "icon": "Stamp",
     "to": "/leave/sanction", "required_permission": "leave.request.approve", "sort_order": 60},
    {"code": "leave.resumption_queue", "label": "Resumption Reviews", "icon": "ArrowCounterClockwise",
     "to": "/leave/resumptions", "required_permission": "leave.resumption.review", "sort_order": 70},
    {"code": "leave.admin_policy", "label": "ELM Policy & Calendars", "icon": "GearSix",
     "to": "/leave/admin/policy", "required_permission": "leave.policy.manage", "sort_order": 80},
    {"code": "leave.offline_sync", "label": "Offline Leave Sync", "icon": "Database",
     "to": "/leave/admin/offline-sync", "required_permission": "leave.record.manage", "sort_order": 90},
]

PERMISSIONS = [
    ("leave.request.create", "Apply for leave or request extension of ongoing leave"),
    ("leave.request.view_self", "View own leave history, balances, and export own applications"),
    ("leave.request.view", "View leave requests in your approval queue"),
    ("leave.request.delete", "Withdraw a pending request or request cancellation of approved leave"),
    ("leave.request.review", "Unit Head review, decision or recommendation"),
    ("leave.request.assign", "Establishment verification and routing to the sanctioning authority"),
    ("leave.request.approve", "Make final sanctioning decisions"),
    ("leave.resumption.create", "Submit duty resumption after EL, COL or VL"),
    ("leave.resumption.review", "Review duty resumption declarations"),
    ("leave.substitute.review", "Accept or decline a nominated substitute responsibility"),
    ("leave.policy.manage", "Configure leave policy, hierarchy and SLA thresholds"),
    ("leave.calendar.publish", "Maintain and publish the holiday and RH calendar"),
    ("leave.record.manage", "Record already-sanctioned offline leave and maintain leave records"),
]
```