"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""
MODULE = {
    "code": "placement_cell", "label": "Placement Cell", "icon": "FaBriefcase",
    "base_path": "/placement", "nav_section": "Placement", "sort_order": 10,
    "status": "active",
}

NAV_ITEMS = [
    # -- student -----------------------------------------------------------
    # First, because rule 1 makes it the gate on everything below it.
    {"code": "placement.registration", "label": "Season Registration",
     "icon": "FaClipboardCheck", "to": "/placement/registration",
     "required_permission": "placement_cell.registration.self",
     "sort_order": 5},
    {"code": "placement.postings", "label": "Opportunities",
     "icon": "FaClipboardList", "to": "/placement/postings",
     "required_permission": "placement_cell.job_posting.view", "sort_order": 10},
    {"code": "placement.mine", "label": "My Applications",
     "icon": "FaUserCheck", "to": "/placement/mine",
     "required_permission": "placement_cell.application.view_self",
     "sort_order": 20},
    {"code": "placement.offers", "label": "My Offers",
     "icon": "FaFileSignature", "to": "/placement/offers",
     "required_permission": "placement_cell.offer.respond", "sort_order": 30},
    {"code": "placement.profile", "label": "My Profile",
     "icon": "FaIdCard", "to": "/placement/profile",
     "required_permission": "placement_cell.application.view_self",
     "sort_order": 40},

    # -- staff (TPO / chairman) -------------------------------------------
    {"code": "placement.registrations", "label": "Registrations",
     "icon": "FaClipboardCheck", "to": "/placement/registration-approvals",
     "required_permission": "placement_cell.registration.manage",
     "sort_order": 55},
    {"code": "placement.applications", "label": "Applications",
     "icon": "FaUsers", "to": "/placement/applications",
     "required_permission": "placement_cell.application.view", "sort_order": 50},
    {"code": "placement.companies", "label": "Companies",
     "icon": "FaBuilding", "to": "/placement/companies",
     "required_permission": "placement_cell.company.manage", "sort_order": 60},
    {"code": "placement.interviews", "label": "Interviews",
     "icon": "FaCalendarAlt", "to": "/placement/interviews",
     "required_permission": "placement_cell.interview.schedule",
     "sort_order": 70},
    {"code": "placement.announcements", "label": "Announcements",
     "icon": "FaBullhorn", "to": "/placement/announcements",
     "required_permission": "placement_cell.announcement.publish",
     "sort_order": 80},
    {"code": "placement.cpi", "label": "Student CPI",
     "icon": "FaGraduationCap", "to": "/placement/students-cpi",
     "required_permission": "placement_cell.academic_directory.view",
     "sort_order": 85},
    {"code": "placement.reports", "label": "Reports",
     "icon": "FaChartBar", "to": "/placement/reports",
     "required_permission": "placement_cell.report.view", "sort_order": 90},
]

#: Every permission this module recognises. Seeded into the IAM and used by the
#: permission-catalogue check, so a view cannot guard on a code that nobody can
#: ever be granted — a typo there would otherwise lock an endpoint forever.
PERMISSIONS = [
    ("placement_cell.job_posting.view", "See job postings"),
    ("placement_cell.job_posting.manage", "Create and publish postings"),
    ("placement_cell.application.view", "See all applications"),
    ("placement_cell.application.view_self", "See one's own applications"),
    ("placement_cell.application.create", "Apply to a posting"),
    ("placement_cell.application.review", "Shortlist and reject applications"),
    ("placement_cell.application.delete", "Withdraw an application"),
    ("placement_cell.application.auto_withdraw", "System auto-withdrawal"),
    ("placement_cell.interview.schedule", "Schedule interview rounds"),
    ("placement_cell.offer.issue", "Extend an offer"),
    ("placement_cell.offer.respond", "Accept or decline an offer"),
    ("placement_cell.offer.revoke", "Revoke an issued offer"),
    ("placement_cell.offer.expire", "System offer expiry"),
    ("placement_cell.company.manage", "Register and approve companies"),
    ("placement_cell.announcement.publish", "Publish announcements"),
    ("placement_cell.report.view", "See operational reports"),
    ("placement_cell.registration.debar",
     "Record conduct incidents and impose placement sanctions"),
    ("placement_cell.registration.manage",
     "Approve late registrations and re-registrations"),
    ("placement_cell.registration.self",
     "Register yourself for a placement season"),
    ("placement_cell.record.manage",
     "Record off-campus placements and chase offer letters"),
    ("placement_cell.academic_directory.view",
     "Browse every student's declared CPI"),
]
