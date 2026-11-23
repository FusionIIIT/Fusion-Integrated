"""What the IAM publishes for PMS (ADR-0010): permissions, who holds them, and the sidebar."""
MODULE = {
    "code": "pms", "label": "Patent Management", "icon": "Lightbulb",
    "base_path": "/pms", "nav_section": "Research", "sort_order": 40,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "pms.applications", "label": "My Applications", "icon": "FileText",
     "to": "/pms/applications", "required_permission": "pms.application.create",
     "sort_order": 10},
    {"code": "pms.reviews", "label": "Reviews", "icon": "Gavel",
     "to": "/pms/reviews", "required_permission": "pms.review.approve", "sort_order": 20},
    {"code": "pms.cases", "label": "Assigned Cases", "icon": "Briefcase",
     "to": "/pms/cases", "required_permission": "pms.attorney_assignment.review",
     "sort_order": 30},
    {"code": "pms.assignments", "label": "Assignments", "icon": "UserSwitch",
     "to": "/pms/assignments", "required_permission": "pms.review.assign", "sort_order": 40},
    {"code": "pms.monitoring", "label": "Deadlines & Escalations", "icon": "Alarm",
     "to": "/pms/monitoring", "required_permission": "pms.escalation.review",
     "sort_order": 50},
    {"code": "pms.oversight", "label": "Oversight", "icon": "Binoculars",
     "to": "/pms/oversight", "required_permission": "pms.workflow.view", "sort_order": 60},
    {"code": "pms.prior_art", "label": "Prior Art Search", "icon": "MagnifyingGlass",
     "to": "/pms/prior-art", "required_permission": "pms.prior_art.create", "sort_order": 70},
    {"code": "pms.licensing", "label": "Licensing", "icon": "Handshake",
     "to": "/pms/licensing", "required_permission": "pms.licensing_request.view",
     "sort_order": 80},
    {"code": "pms.reports", "label": "Reports", "icon": "ChartBar",
     "to": "/pms/reports", "required_permission": "pms.report.view", "sort_order": 90},
    {"code": "pms.audit", "label": "Audit Log", "icon": "ListMagnifyingGlass",
     "to": "/pms/audit", "required_permission": "pms.audit_log.view", "sort_order": 100},
    {"code": "pms.directors", "label": "Directors", "icon": "UsersThree",
     "to": "/pms/directors", "required_permission": "pms.director_profile.update",
     "sort_order": 110},
    {"code": "pms.attorney_panel", "label": "Attorney Panel", "icon": "Scales",
     "to": "/pms/attorney-panel", "required_permission": "pms.attorney_panel.update",
     "sort_order": 120},
    {"code": "pms.settings", "label": "Settings", "icon": "GearSix",
     "to": "/pms/settings", "required_permission": "pms.policy.publish", "sort_order": 130},
]

PERMISSIONS = [
    ("pms.application.view", "See applications within one's scope"),
    ("pms.application.create", "Draft and submit a patent application"),
    ("pms.application.update", "Edit and resubmit one's own application"),
    ("pms.inventor.update", "Maintain an application's inventors and agreements"),
    ("pms.withdrawal.create", "Withdraw one's own application"),
    ("pms.appeal.create", "Appeal a rejection"),
    ("pms.appeal.review", "Decide an appeal"),
    ("pms.review.assign", "Assign or reassign an application to a Director"),
    ("pms.review.approve", "Record a review decision on an assigned application"),
    ("pms.director_profile.update", "Maintain Directors' expertise areas"),
    ("pms.attorney_panel.update", "Maintain the approved attorney panel"),
    ("pms.attorney.assign", "Assign an attorney to an approved application"),
    ("pms.attorney_assignment.review", "Accept or decline an attorney assignment"),
    ("pms.assessment.create", "Record a patentability assessment"),
    ("pms.legal_request.create", "Ask the applicant for information or an extension"),
    ("pms.legal_advice.create", "Record legal advice"),
    ("pms.budget.create", "Propose a filing and prosecution budget"),
    ("pms.budget.approve", "Approve or reject a budget"),
    ("pms.filing.create", "Record an external patent filing"),
    ("pms.communication.create", "Record a patent-office communication"),
    ("pms.office_action_response.create", "Prepare an office-action response"),
    ("pms.office_action_response.update", "Record a response's submission or extension"),
    ("pms.office_action_response.approve", "Approve a response as the applicant"),
    ("pms.maintenance.update", "Track maintenance and record maintenance actions"),
    ("pms.renewal.approve", "Decide Renew or Do Not Renew"),
    ("pms.renewal.assign", "Reassign a renewal decision to another Director"),
    ("pms.document.view", "Read application documents within one's scope"),
    ("pms.document.create", "Upload a document or a new version"),
    ("pms.document.update", "Change a document's sensitivity level"),
    ("pms.prior_art.view", "See prior-art references within one's scope"),
    ("pms.prior_art.create", "Search prior art and attach references"),
    ("pms.licensing_request.view", "See licensing requests within one's scope"),
    ("pms.licensing_request.create", "Submit a licensing or technology-transfer request"),
    ("pms.licensing_request.review", "Route, negotiate and record licensing agreements"),
    ("pms.escalation.review", "Monitor deadlines and handle escalations"),
    ("pms.workflow.view", "See workflow oversight"),
    ("pms.report.view", "See reports within one's scope"),
    ("pms.report.export", "Export reports"),
    ("pms.report_definition.create", "Save and schedule report definitions"),
    ("pms.audit_log.view", "See audit logs within one's scope"),
    ("pms.audit_log.export", "Export audit logs"),
    ("pms.policy.publish", "Publish a new PMS settings version"),
    ("pms.deadline.manage", "Scheduled sweep: expire, alert and escalate deadlines"),
    ("pms.routing.assign", "Scheduled automatic assignment of Directors"),
]

#: Performed only by scheduled work.
SYSTEM_PERMISSIONS = [
    "pms.deadline.manage",      # expiry, alerts and escalations in one sweep
    "pms.routing.assign",       # automatic Director assignment
]
# `manage` because one sweep expires, alerts and escalates; no single verb names it.

#: Read only in selectors to narrow rows; none — every scope here follows an enforced permission.
SCOPE_PERMISSIONS: list[str] = []

_APPLICANT = [
    "pms.application.view", "pms.application.create", "pms.application.update",
    "pms.inventor.update", "pms.withdrawal.create", "pms.appeal.create",
    "pms.document.view", "pms.document.create",
    "pms.prior_art.view", "pms.prior_art.create",
    "pms.office_action_response.approve",
    "pms.licensing_request.view", "pms.licensing_request.create",
    "pms.report.view",
]
_DIRECTOR = [
    "pms.application.view", "pms.review.approve", "pms.appeal.review",
    "pms.budget.approve", "pms.renewal.approve",
    "pms.document.view", "pms.prior_art.view",
    "pms.licensing_request.view", "pms.licensing_request.review",
    "pms.workflow.view", "pms.report.view", "pms.report.export",
    "pms.report_definition.create", "pms.audit_log.view",
]
_PCC_ADMIN = [
    "pms.application.view", "pms.review.assign", "pms.attorney.assign",
    "pms.director_profile.update", "pms.attorney_panel.update",
    "pms.renewal.assign", "pms.escalation.review", "pms.workflow.view",
    "pms.document.view", "pms.document.create", "pms.document.update",
    "pms.prior_art.view",
    "pms.licensing_request.view", "pms.licensing_request.review",
    "pms.report.view", "pms.report.export", "pms.report_definition.create",
    "pms.audit_log.view", "pms.audit_log.export", "pms.policy.publish",
]
_ATTORNEY = [
    "pms.application.view", "pms.attorney_assignment.review",
    "pms.assessment.create", "pms.legal_request.create", "pms.legal_advice.create",
    "pms.budget.create", "pms.filing.create", "pms.communication.create",
    "pms.office_action_response.create", "pms.office_action_response.update",
    "pms.maintenance.update", "pms.document.view", "pms.document.create",
    "pms.prior_art.view", "pms.prior_art.create",
]

#: Keyed by designation name; the three pms_* names are new (ruling A4).
ROLE_GRANTS = {
    "student": _APPLICANT,      # PS 2.2.1, UC-PMS-001; ruling A4
    "faculty": _APPLICANT,
    "staff": _APPLICANT,
    "pms_director": _DIRECTOR,      # PS 2.2.2; UC-PMS-008, 009, 018, 023, 031, 032
    "pms_pcc_admin": _PCC_ADMIN,    # PS 2.2.3; UC-PMS-007, 010, 016, 024..028
    "pms_attorney": _ATTORNEY,      # PS 2.2.4; UC-PMS-011..015, 017, 033
}


def readiness() -> list[str]:
    """Unmet prerequisites, each a sentence saying what to do; empty means PMS can run."""
    from modules.pms.checks import upload_root_problem
    from modules.pms.services.scanning import ping

    problems = []
    if folder := upload_root_problem():
        problems.append(folder)
    if scanner := ping():
        problems.append(f"Malware scanner: {scanner}")
    return problems
