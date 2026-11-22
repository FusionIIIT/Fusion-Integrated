"""CMS role, permission and navigation manifest source."""

MODULE = {
    "code": "complaints",
    "label": "Complaints",
    "icon": "ChatCircleDots",
    "base_path": "/complaints",
    "nav_section": "Campus",
    "sort_order": 25,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "complaints.mine",
        "label": "My Complaints",
        "icon": "ChatCircleDots",
        "to": "/complaints/mine",
        "required_permission": "complaints.complaint.view",
        "sort_order": 10,
    },
    {
        "code": "complaints.announcements",
        "label": "Announcements",
        "icon": "Megaphone",
        "to": "/complaints/announcements",
        "required_permission": "complaints.announcement.view",
        "sort_order": 20,
    },
    {
        "code": "complaints.feedback",
        "label": "Feedback Review",
        "icon": "ChatText",
        "to": "/complaints/feedback",
        "required_permission": "complaints.feedback.review",
        "sort_order": 30,
    },
    {
        "code": "complaints.work-queue",
        "label": "Handler Work Queue",
        "icon": "ClipboardText",
        "to": "/complaints/work-queue",
        "required_permission": "complaints.complaint.update",
        "sort_order": 35,
    },
    {
        "code": "complaints.assignment-queue",
        "label": "Complaint Assignment",
        "icon": "UserSwitch",
        "to": "/complaints/assignment-queue",
        "required_permission": "complaints.complaint.assign",
        "sort_order": 38,
    },
    {
        "code": "complaints.supervision",
        "label": "Supervisor Queue",
        "icon": "ShieldCheck",
        "to": "/complaints/supervision",
        "required_permission": "complaints.complaint.approve",
        "sort_order": 40,
    },
    {
        "code": "complaints.reports",
        "label": "Reports",
        "icon": "ChartBar",
        "to": "/complaints/reports",
        "required_permission": "complaints.report.view",
        "sort_order": 50,
    },
]

PERMISSIONS = [
    ("complaints.complaint.create", "Submit a complaint"),
    ("complaints.complaint.view", "View complaints within assigned scope"),
    ("complaints.complaint.assign", "Assign active complaints to handlers"),
    ("complaints.complaint.update", "Record handler progress and outcomes"),
    ("complaints.complaint.approve", "Verify closure and decide reopening requests"),
    ("complaints.feedback.create", "Submit complaint feedback"),
    ("complaints.feedback.review", "Review complaint feedback"),
    ("complaints.announcement.view", "View complaint announcements"),
    ("complaints.announcement.publish", "Publish complaint announcements"),
    ("complaints.escalation.view", "Monitor escalated complaints"),
    ("complaints.report.view", "View complaint reports and summaries"),
]

SYSTEM_PERMISSIONS = []

_COMPLAINANT = [
    "complaints.complaint.create",
    "complaints.complaint.view",
    "complaints.feedback.create",
    "complaints.announcement.view",
]
_HANDLER = [
    "complaints.complaint.view",
    "complaints.complaint.assign",
    "complaints.feedback.review",
    "complaints.announcement.view",
    "complaints.complaint.update",
    "complaints.announcement.publish",
    "complaints.report.view",
]
_SUPERVISOR = [
    "complaints.complaint.view",
    "complaints.complaint.approve",
    "complaints.feedback.review",
    "complaints.announcement.view",
    "complaints.announcement.publish",
    "complaints.escalation.view",
    "complaints.report.view",
]
_ADMIN = [
    "complaints.report.view",
    "complaints.announcement.view",
]

ROLE_GRANTS = {
    "student": _COMPLAINANT,
    "faculty": _COMPLAINANT,
    "staff": _COMPLAINANT,
    "System Admin": _ADMIN,
    "Complaint Handler": _HANDLER,
    "Complaint Supervisor": _SUPERVISOR,
}
