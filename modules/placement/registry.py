"""What the server tells the shell about this module (ADR-0010)."""
MODULE = {
    "code": "placement", "label": "Placement Cell", "icon": "Briefcase",
    "base_path": "/placement", "nav_section": "Placement", "sort_order": 10,
    "status": "active",
}

NAV_ITEMS = [
    # -- student: registration first, because rule 1 gates everything below ---
    {"code": "placement.registration", "label": "Season Registration",
     "icon": "Checks", "to": "/placement/registration",
     "required_permission": "placement.registration.create",
     "sort_order": 5},
    {"code": "placement.profile", "label": "My Profile",
     "icon": "IdentificationCard", "to": "/placement/profile",
     "required_permission": "placement.own_application.view", "sort_order": 7},
    {"code": "placement.postings", "label": "Opportunities",
     "icon": "ClipboardText", "to": "/placement/postings",
     "required_permission": "placement.job_posting.view", "sort_order": 10},
    {"code": "placement.mine", "label": "My Applications",
     "icon": "UserCheck", "to": "/placement/mine",
     "required_permission": "placement.own_application.view",
     "sort_order": 20},
    {"code": "placement.offers", "label": "My Offers",
     "icon": "Signature", "to": "/placement/offers",
     "required_permission": "placement.offer_response.create", "sort_order": 30},

    # -- staff (TPO / chairman) -------------------------------------------
    {"code": "placement.registrations", "label": "Registrations",
     "icon": "Checks", "to": "/placement/registration-approvals",
     "required_permission": "placement.registration.manage",
     "sort_order": 55},
    {"code": "placement.applications", "label": "Applications",
     "icon": "Users", "to": "/placement/applications",
     "required_permission": "placement.application.view", "sort_order": 50},
    {"code": "placement.companies", "label": "Companies",
     "icon": "Buildings", "to": "/placement/companies",
     "required_permission": "placement.company.manage", "sort_order": 60},
    {"code": "placement.interviews", "label": "Interviews",
     "icon": "CalendarBlank", "to": "/placement/interviews",
     "required_permission": "placement.interview.create",
     "sort_order": 70},
    {"code": "placement.announcements", "label": "Announcements",
     "icon": "Megaphone", "to": "/placement/announcements",
     "required_permission": "placement.announcement.publish",
     "sort_order": 80},
    {"code": "placement.cpi", "label": "Student CPI",
     "icon": "GraduationCap", "to": "/placement/students-cpi",
     "required_permission": "placement.academic_directory.view",
     "sort_order": 85},
    {"code": "placement.records", "label": "Placement Records",
     "icon": "Notebook", "to": "/placement/records",
     "required_permission": "placement.record.manage", "sort_order": 88},
    {"code": "placement.reports", "label": "Reports",
     "icon": "ChartBar", "to": "/placement/reports",
     "required_permission": "placement.statistic.view", "sort_order": 90},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("placement.job_posting.view", "See job postings"),
    ("placement.job_posting.manage", "Create and publish postings"),
    ("placement.application.view", "See all applications"),
    ("placement.own_application.view", "See one's own applications"),
    ("placement.application.create", "Apply to a posting"),
    ("placement.application.review", "Shortlist and reject applications"),
    ("placement.application.delete", "Withdraw an application"),
    ("placement.application.revoke", "System auto-withdrawal"),
    ("placement.interview.create", "Schedule interview rounds"),
    ("placement.offer.create", "Extend an offer"),
    ("placement.offer_response.create", "Accept or decline an offer"),
    ("placement.offer.revoke", "Revoke an issued offer"),
    ("placement.offer_expiry.create", "System offer expiry"),
    ("placement.company.manage", "Register and approve companies"),
    ("placement.announcement.publish", "Publish announcements"),
    ("placement.report.view", "See operational reports"),
    ("placement.statistic.view", "See anonymised placement statistics"),
    ("placement.sanction.manage",
     "Record conduct incidents and impose placement sanctions"),
    ("placement.registration.manage",
     "Approve late registrations and re-registrations"),
    ("placement.registration.create",
     "Register yourself for a placement season"),
    ("placement.record.manage",
     "Record off-campus placements and chase offer letters"),
    ("placement.academic_directory.view",
     "Browse every student's declared CPI"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = [
    "placement.application.revoke",
    "placement.offer_expiry.create",
]

_STUDENT = [
    "placement.registration.create",
    "placement.job_posting.view",
    "placement.own_application.view",
    "placement.application.create",
    "placement.application.delete",
    "placement.offer_response.create",
    "placement.statistic.view",
]

#: PC-BR-019: read-only statistics for mentorship and networking, nothing else.
_ALUMNI = ["placement.statistic.view"]

#: The TPO (PS 2.2; PC-UC-006, PC-UC-008 to PC-UC-011, PC-UC-020).
_OFFICER = [
    "placement.job_posting.view",
    "placement.application.view",
    "placement.application.review",
    "placement.report.view",
    "placement.statistic.view",
    "placement.academic_directory.view",
    "placement.job_posting.manage",
    "placement.interview.create",
    "placement.offer.create",
    "placement.offer.revoke",
    "placement.company.manage",
    "placement.announcement.publish",
    "placement.registration.manage",
    "placement.sanction.manage",
    "placement.record.manage",
]

#: Oversees rather than operates (PS 2.3; PC-UC-012, PC-UC-013).
_CHAIRMAN = [
    "placement.job_posting.view",
    "placement.application.view",
    "placement.report.view",
    "placement.statistic.view",
    "placement.academic_directory.view",
    "placement.announcement.publish",
]

#: Keyed by the designation name exactly as globals_designation spells it.
ROLE_GRANTS = {
    "student": _STUDENT,
    "placement officer": _OFFICER,
    "placement chairman": _CHAIRMAN,
    "alumini": _ALUMNI,
}


def readiness() -> list[str]:
    """What must exist before the module can be switched on; empty when ready."""
    from modules.placement.models import PlacementPolicy

    if not PlacementPolicy.objects.filter(is_active=True).exists():
        return [("No active placement season. Run "
                 "`manage.py open_placement_season --season 2026-27` to open one.")]
    return []
