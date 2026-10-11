"""ELM module permissions and module-shell metadata.

The pilot exposes APIs only; NAV_ITEMS stays empty until a client route exists.
"""

MODULE = {
    "code": "elm",
    "label": "Employee Leave Management",
    "icon": "FaCalendarCheck",
    "base_path": "/elm",
    "nav_section": "Employee Leave Management",
    "sort_order": 40,
    "status": "active",
}
NAV_ITEMS = []

PERMISSIONS = [
    ("elm.request.view_self", "View own leave requests, balances and history"),
    ("elm.request.create", "Submit leave, extension and resumption requests"),
    ("elm.request.withdraw", "Withdraw own pending leave requests"),
    ("elm.substitute.respond", "Accept or decline substitute assignments"),
    ("elm.workflow.review", "Review assigned leave workflow tasks"),
    ("elm.policy.manage", "Manage current leave policy and approval routes"),
    ("elm.calendar.manage", "Manage and publish holiday calendars"),
    ("elm.account.manage", "Maintain leave accounts and authorized records"),
    ("elm.report.export", "Export a leave representation or report"),
    ("elm.sla.manage", "Configure service-level reminders and escalation"),
    ("elm.system.process", "Run scheduled year-end and SLA processing"),
]
SYSTEM_PERMISSIONS = ["elm.system.process"]

_EMPLOYEE = [
    "elm.request.view_self",
    "elm.request.create",
    "elm.request.withdraw",
    "elm.report.export",
    "elm.substitute.respond",
]
_REVIEWER = ["elm.workflow.review", "elm.request.view_self"]
_ADMIN = [
    "elm.policy.manage",
    "elm.calendar.manage",
    "elm.account.manage",
    "elm.report.export",
    "elm.sla.manage",
    "elm.workflow.review",
    "elm.request.view_self",
]
ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "employee": _EMPLOYEE,
    "unit_head": _REVIEWER,
    "establishment_officer": _REVIEWER,
    "director": [*_EMPLOYEE, *_REVIEWER],
    "elm_admin": [*_ADMIN, *_EMPLOYEE],
}
