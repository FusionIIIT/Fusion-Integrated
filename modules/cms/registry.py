"""Server-driven CMS navigation and the module's permission contract."""

MODULE = {
    "code": "cms",
    "label": "Complaints",
    "icon": "FaClipboardList",
    "base_path": "/cms",
    "nav_section": "Services",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "cms.my-complaints",
        "label": "My Complaints",
        "icon": "ClipboardList",
        "to": "/cms/mine",
        "required_permission": "cms.complaint.track",
        "sort_order": 10,
    },
    {
        "code": "cms.submit",
        "label": "Submit Complaint",
        "icon": "FaClipboardCheck",
        "to": "/cms/submit",
        "required_permission": "cms.complaint.submit",
        "sort_order": 20,
    },
    {
        "code": "cms.worklist",
        "label": "Complaint Worklist",
        "icon": "FaClipboardList",
        "to": "/cms/worklist",
        "required_permission": "cms.complaint.view",
        "sort_order": 30,
    },
    {
        "code": "cms.escalations",
        "label": "Escalations",
        "icon": "FaChartBar",
        "to": "/cms/escalations",
        "required_permission": "cms.escalation.monitor",
        "sort_order": 40,
    },
    {
        "code": "cms.reopening",
        "label": "Reopening Requests",
        "icon": "FaCheckDouble",
        "to": "/cms/reopening",
        "required_permission": "cms.reopening.review",
        "sort_order": 45,
    },
    {
        "code": "cms.feedback",
        "label": "Feedback",
        "icon": "FaUsers",
        "to": "/cms/feedback",
        "required_permission": "cms.feedback.review",
        "sort_order": 50,
    },
    {
        "code": "cms.announcements",
        "label": "Announcements",
        "icon": "Megaphone",
        "to": "/cms/announcements",
        "required_permission": "cms.announcement.view",
        "sort_order": 60,
    },
    {
        "code": "cms.reports",
        "label": "Reports & Analytics",
        "icon": "ChartNoAxesCombined",
        "to": "/cms/reports",
        "required_permission": "cms.report.view",
        "sort_order": 70,
    },
    {
        "code": "cms.roles",
        "label": "CMS Roles",
        "icon": "FaCog",
        "to": "/cms/roles",
        "required_permission": "cms.role.manage",
        "sort_order": 80,
    },
]

PERMISSIONS = [
    ("cms.complaint.submit", "Submit complaints"),
    ("cms.complaint.track", "Track own complaints and history"),
    ("cms.complaint.view", "Review and manage complaints"),
    ("cms.complaint.assign", "Assign and prioritize complaints"),
    ("cms.complaint.update", "Record complaint progress"),
    ("cms.complaint.resolve", "Resolve or reject complaints"),
    ("cms.close.user", "Verify closure as complainant"),
    ("cms.close.supervisor", "Verify closure as supervisor"),
    ("cms.complaint.reopen", "Request reopening of own complaint"),
    ("cms.reopening.review", "Review reopening requests"),
    ("cms.escalation.manual", "Escalate unresolved complaints"),
    ("cms.escalation.monitor", "Monitor escalated complaints"),
    ("cms.feedback.submit", "Submit feedback"),
    ("cms.feedback.review", "Review submitted feedback"),
    ("cms.announcement.publish", "Publish complaint announcements"),
    ("cms.announcement.view", "View complaint announcements"),
    ("cms.report.view", "View CMS reports and analytics"),
    ("cms.role.manage", "Assign CMS handler and supervisor roles"),
]

_USER = [
    "cms.complaint.submit",
    "cms.complaint.track",
    "cms.complaint.reopen",
    "cms.close.user",
    "cms.feedback.submit",
    "cms.announcement.view",
]
_HANDLER = [
    "cms.complaint.view",
    "cms.complaint.assign",
    "cms.complaint.update",
    "cms.complaint.resolve",
    "cms.escalation.manual",
    "cms.feedback.review",
    "cms.announcement.publish",
    "cms.announcement.view",
    "cms.report.view",
]
_SUPERVISOR = [
    "cms.complaint.view",
    "cms.close.supervisor",
    "cms.reopening.review",
    "cms.escalation.monitor",
    "cms.feedback.review",
    "cms.announcement.publish",
    "cms.announcement.view",
    "cms.report.view",
]
_ADMIN = ["cms.role.manage", "cms.report.view"]

ROLE_GRANTS = {
    "student": _USER,
    "faculty": _USER,
    "staff": _USER,
    "complaint_handler": _HANDLER,
    "complaint_supervisor": _SUPERVISOR,
    "system_admin": _ADMIN,
}
