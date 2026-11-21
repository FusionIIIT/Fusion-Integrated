"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""

MODULE = {
    "code": "cms",
    "label": "Complaint Management",
    "icon": "WarningCircle",
    "base_path": "/cms",
    "nav_section": "Services",
    "sort_order": 15,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "cms.my_complaints",
        "label": "My Complaints",
        "icon": "ListBullets",
        "to": "/cms",
        "required_permission": "cms.complaint.view_self",
        "sort_order": 10,
    },
    {
        "code": "cms.handler_queue",
        "label": "Handler Queue",
        "icon": "Tray",
        "to": "/cms/queue",
        "required_permission": "cms.complaint.handle",
        "sort_order": 20,
    },
    {
        "code": "cms.escalations",
        "label": "Escalations",
        "icon": "Warning",
        "to": "/cms/escalations",
        "required_permission": "cms.complaint.escalate",
        "sort_order": 30,
    },
    {
        "code": "cms.announcements",
        "label": "Announcements",
        "icon": "Megaphone",
        "to": "/cms/announcements",
        "required_permission": "cms.announcement.view",
        "sort_order": 40,
    },
    {
        "code": "cms.reports",
        "label": "Analytics & Reports",
        "icon": "ChartBar",
        "to": "/cms/reports",
        "required_permission": "cms.report.view",
        "sort_order": 50,
    },
    {
        "code": "cms.roles",
        "label": "Role Governance",
        "icon": "UsersThree",
        "to": "/cms/roles",
        "required_permission": "cms.role.manage",
        "sort_order": 60,
    },
]

PERMISSIONS = [
    ("cms.complaint.submit_self", "Submit complaints on behalf of self"),
    ("cms.complaint.view_self", "View self submitted complaints"),
    ("cms.complaint.view_all", "View all complaints across departments"),
    ("cms.complaint.handle", "Triage, update status, and investigate complaints"),
    ("cms.complaint.resolve", "Mark complaints resolved or rejected"),
    ("cms.complaint.escalate", "Escalate overdue or critical complaints"),
    ("cms.complaint.reopen", "Request or approve complaint reopening"),
    ("cms.announcement.view", "View active campus announcements"),
    ("cms.announcement.manage", "Publish and expire announcements"),
    ("cms.report.view", "View analytics and resolution SLA metrics"),
    ("cms.role.manage", "Assign and manage handler/supervisor roles"),
]

SYSTEM_PERMISSIONS = [
    ("cms.complaint.auto_escalate"),
]

_STUDENT = [
    "cms.complaint.submit_self",
    "cms.complaint.view_self",
    "cms.complaint.reopen",
    "cms.announcement.view",
]

_FACULTY = [
    "cms.complaint.submit_self",
    "cms.complaint.view_self",
    "cms.complaint.reopen",
    "cms.announcement.view",
]

_STAFF = [
    "cms.complaint.submit_self",
    "cms.complaint.view_self",
    "cms.complaint.reopen",
    "cms.announcement.view",
]

_HANDLER = [
    "cms.complaint.submit_self",
    "cms.complaint.view_self",
    "cms.complaint.handle",
    "cms.complaint.resolve",
    "cms.complaint.reopen",
    "cms.announcement.view",
]

_SUPERVISOR = [
    "cms.complaint.submit_self",
    "cms.complaint.view_self",
    "cms.complaint.view_all",
    "cms.complaint.handle",
    "cms.complaint.resolve",
    "cms.complaint.escalate",
    "cms.complaint.reopen",
    "cms.announcement.view",
    "cms.announcement.manage",
    "cms.report.view",
    "cms.role.manage",
]

ROLE_GRANTS = {
    "student": _STUDENT,
    "faculty": _FACULTY,
    "staff": _STAFF,
    "complaint_handler": _HANDLER,
    "complaint_supervisor": _SUPERVISOR,
    "Dean Academic": _SUPERVISOR,
    "placement_chairman": _SUPERVISOR,
    "acadadmin": _SUPERVISOR,
}
