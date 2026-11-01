"""Registry and permission declarations for Complaint Management System (ADR-0010)."""

MODULE = {
    "code": "complaints",
    "label": "Complaints",
    "icon": "FaTools",
    "base_path": "/complaints",
    "nav_section": "Campus",
    "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "complaints.mine",
        "label": "My Complaints",
        "icon": "FaListUl",
        "to": "/complaints/mine",
        "required_permission": "complaints.complaint.view_self",
        "sort_order": 10,
    },
    {
        "code": "complaints.queue",
        "label": "Complaint Queue",
        "icon": "FaInbox",
        "to": "/complaints/queue",
        "required_permission": "complaints.complaint.view",
        "sort_order": 20,
    },
    {
        "code": "complaints.announcements",
        "label": "Announcements",
        "icon": "FaBullhorn",
        "to": "/complaints/announcements",
        "required_permission": "complaints.announcement.view",
        "sort_order": 30,
    },
    {
        "code": "complaints.reports",
        "label": "Reports & Analytics",
        "icon": "FaChartBar",
        "to": "/complaints/reports",
        "required_permission": "complaints.report.view",
        "sort_order": 40,
    },
]

PERMISSIONS = [
    ("complaints.complaint.view_self", "View own complaints"),
    ("complaints.complaint.create", "Submit a complaint"),
    ("complaints.complaint.view", "View complaints within scope"),
    ("complaints.complaint.assign", "Assign and categorize complaint"),
    ("complaints.complaint.update", "Update complaint progress"),
    ("complaints.complaint.resolve", "Resolve complaint"),
    ("complaints.complaint.reject", "Reject complaint"),
    ("complaints.complaint.verify", "Verify resolved complaint for closure"),
    ("complaints.complaint.reopen", "Request or review complaint reopening"),
    ("complaints.complaint.escalate", "Escalate unresolved complaint"),
    ("complaints.feedback.submit", "Submit feedback for complaint"),
    ("complaints.feedback.view", "Review submitted feedback"),
    ("complaints.announcement.view", "View complaint announcements"),
    ("complaints.announcement.publish", "Publish complaint announcement"),
    ("complaints.report.view", "View CMS reports and analytics"),
    ("complaints.role.manage", "Assign and manage CMS roles"),
]

SCOPE_PERMISSIONS = [
    "complaints.complaint.view",
    "complaints.report.view",
]

SYSTEM_PERMISSIONS = [
    "complaints.complaint.sla_check",
]

_USER = [
    "complaints.complaint.view_self",
    "complaints.complaint.create",
    "complaints.complaint.verify",
    "complaints.complaint.reopen",
    "complaints.feedback.submit",
    "complaints.announcement.view",
]

_OPERATIONS = [
    *_USER,
    "complaints.complaint.view",
    "complaints.complaint.assign",
    "complaints.complaint.update",
    "complaints.complaint.resolve",
    "complaints.complaint.reject",
    "complaints.complaint.escalate",
    "complaints.feedback.view",
    "complaints.announcement.publish",
    "complaints.report.view",
]

_ADMIN = [
    *_OPERATIONS,
    "complaints.role.manage",
]

ROLE_GRANTS = {
    "student": _USER,
    "faculty": _USER,
    "staff": _USER,
    "Dean Academic": _OPERATIONS,
    "Registrar": _OPERATIONS,
    "Director": _ADMIN,
    "acadadmin": _ADMIN,
}

