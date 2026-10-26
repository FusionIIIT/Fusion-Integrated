"""What the server tells the shell about ELM (ADR-0010).

Authority to decide a request is NOT a permission here: it comes from holding an
open WorkflowTask (see services.applications._take_task), because approvers are
resolved per applicant by the published hierarchy. Permissions only gate which
screens and endpoints a person may reach.
"""
MODULE = {
    "code": "elm", "label": "Employee Leave", "icon": "CalendarCheck",
    "base_path": "/elm", "nav_section": "Leave", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    # -- every employee -----------------------------------------------------
    {"code": "elm.apply", "label": "Apply for Leave", "icon": "PencilSimple",
     "to": "/elm/apply", "required_permission": "elm.request.create",
     "sort_order": 5},
    {"code": "elm.mine", "label": "My Leave", "icon": "ClipboardText",
     "to": "/elm/mine", "required_permission": "elm.request.view_self",
     "sort_order": 10},
    {"code": "elm.balance", "label": "Balance and History", "icon": "ChartBar",
     "to": "/elm/balance", "required_permission": "elm.account.view_self",
     "sort_order": 20},
    {"code": "elm.inbox", "label": "Inbox", "icon": "Tray",
     "to": "/elm/inbox", "required_permission": "elm.task.view",
     "sort_order": 30},

    # -- Leave Administrator ------------------------------------------------
    {"code": "elm.policy", "label": "Leave Policy", "icon": "Gear",
     "to": "/elm/admin/policy", "required_permission": "elm.policy.manage",
     "sort_order": 60},
    {"code": "elm.hierarchy", "label": "Approval Hierarchy", "icon": "TreeStructure",
     "to": "/elm/admin/hierarchy", "required_permission": "elm.hierarchy.manage",
     "sort_order": 65},
    {"code": "elm.calendar", "label": "Holiday Calendar", "icon": "CalendarBlank",
     "to": "/elm/admin/calendar", "required_permission": "elm.calendar.manage",
     "sort_order": 70},
    {"code": "elm.offline", "label": "Record Offline Leave", "icon": "Signature",
     "to": "/elm/admin/offline", "required_permission": "elm.offline.record",
     "sort_order": 80},
]

PERMISSIONS = [
    ("elm.request.create", "Apply for, modify, withdraw, cancel, extend and resume own leave"),
    ("elm.request.view_self", "See and print own leave applications"),
    ("elm.account.view_self", "See own leave balances and account history"),
    ("elm.task.view", "See and act on workflow tasks assigned to you"),
    ("elm.policy.manage", "Create, revise and publish leave policy"),
    ("elm.hierarchy.manage", "Create, revise and publish the approval hierarchy"),
    ("elm.calendar.manage", "Create, revise and publish the holiday and RH calendar"),
    ("elm.offline.record", "Record offline-sanctioned leave"),
    ("elm.year_end.run", "Year-end processing"),
    ("elm.sla.run", "SLA reminders and escalation"),
]

#: Performed by the scheduled management commands, so no designation holds them.
SYSTEM_PERMISSIONS = ["elm.year_end.run", "elm.sla.run"]

#: Every employee, whether faculty or staff.
_EMPLOYEE = [
    "elm.request.create",
    "elm.request.view_self",
    "elm.account.view_self",
    "elm.task.view",
]

_LEAVE_ADMIN = [
    "elm.policy.manage",
    "elm.hierarchy.manage",
    "elm.calendar.manage",
    "elm.offline.record",
]

#: Keyed by the designation name as it exists in globals_designation.
#: TODO: filled in once the real designation names are confirmed.
ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "Leave Administrator": [*_EMPLOYEE, *_LEAVE_ADMIN],

}
