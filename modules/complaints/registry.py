"""Server-side registry declaration for Complaint Management System."""

MODULE = {
    "code": "complaints",
    "label": "Complaints",
    "icon": "FaClipboardList",
    "base_path": "/complaints",
    "nav_section": "Services",
    "sort_order": 35,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "complaints.mine",
        "label": "My Complaints",
        "icon": "FaUserCheck",
        "to": "/complaints/mine",
        "required_permission": "complaints.complaint.view_self",
        "sort_order": 10,
    },
    {
        "code": "complaints.queue",
        "label": "Complaint Queue",
        "icon": "FaClipboardList",
        "to": "/complaints/queue",
        "required_permission": "complaints.complaint.assign",
        "sort_order": 20,
    },
    {
        "code": "complaints.supervisor",
        "label": "Supervisor Oversight",
        "icon": "FaClipboardCheck",
        "to": "/complaints/supervisor",
        "required_permission": "complaints.complaint.supervise",
        "sort_order": 30,
    },
    {
        "code": "complaints.announcements",
        "label": "Announcements",
        "icon": "FaBullhorn",
        "to": "/complaints/announcements",
        "required_permission": "complaints.complaint.view_self",
        "sort_order": 40,
    },
    {
        "code": "complaints.reports",
        "label": "Reports & Analytics",
        "icon": "FaChartBar",
        "to": "/complaints/reports",
        "required_permission": "complaints.complaint.report",
        "sort_order": 50,
    },
    {
        "code": "complaints.roles",
        "label": "Role Assignment",
        "icon": "FaUsers",
        "to": "/complaints/roles",
        "required_permission": "complaints.role.manage",
        "sort_order": 60,
    },
]

PERMISSIONS = [
    ("complaints.complaint.view_self", "View own complaints"),
    ("complaints.complaint.create", "Submit a complaint"),
    ("complaints.complaint.view", "View complaints within scope"),
    ("complaints.complaint.assign", "Assign complaint category, priority, and worker"),
    ("complaints.complaint.update", "Update complaint progress and resolution"),
    ("complaints.complaint.resolve", "Resolve or reject complaint"),
    ("complaints.complaint.close", "Verify resolution and close complaint"),
    ("complaints.complaint.reopen", "Request or review complaint reopening"),
    ("complaints.complaint.feedback", "Submit or review feedback"),
    ("complaints.complaint.escalate", "Manually escalate complaint"),
    ("complaints.complaint.supervise", "Supervise escalated complaints and reopenings"),
    ("complaints.announcement.publish", "Publish complaint-related announcements"),
    ("complaints.complaint.report", "Generate operational or summary reports"),
    ("complaints.role.manage", "Assign and reassign CMS Handler and Supervisor roles"),
]

SYSTEM_PERMISSIONS = [
    "complaints.complaint.auto_escalate",
]

_COMPLAINANT = [
    "complaints.complaint.view_self",
    "complaints.complaint.create",
    "complaints.complaint.close",
    "complaints.complaint.reopen",
    "complaints.complaint.feedback",
]

_HANDLER = [
    *_COMPLAINANT,
    "complaints.complaint.view",
    "complaints.complaint.assign",
    "complaints.complaint.update",
    "complaints.complaint.resolve",
    "complaints.complaint.escalate",
    "complaints.announcement.publish",
    "complaints.complaint.report",
]

_SUPERVISOR = [
    *_COMPLAINANT,
    "complaints.complaint.view",
    "complaints.complaint.supervise",
    "complaints.announcement.publish",
    "complaints.complaint.report",
]

_ADMIN = [
    *_HANDLER,
    *_SUPERVISOR,
    "complaints.role.manage",
]

ROLE_GRANTS = {
    "student": _COMPLAINANT,
    "faculty": _COMPLAINANT,
    "staff": _COMPLAINANT,
    "complaint_handler": _HANDLER,
    "complaint_supervisor": _SUPERVISOR,
    "admin": _ADMIN,
}
