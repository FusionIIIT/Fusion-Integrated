"""Fusion module registration for Awards and Scholarships (SPACS)."""

MODULE = {
    "code": "spacs",
    "label": "Awards and Scholarships",
    "icon": "Trophy",
    "base_path": "/spacs",
    "nav_section": "Campus",
    "sort_order": 350,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "spacs.catalogue",
        "label": "Opportunities",
        "icon": "Trophy",
        "to": "/spacs/catalogue",
        "required_permission": "spacs.scheme.view",
        "sort_order": 10,
    },
    {
        "code": "spacs.mine",
        "label": "My Applications",
        "icon": "UserCheck",
        "to": "/spacs/mine",
        "required_permission": "spacs.application.view",
        "sort_order": 20,
    },
    {
        "code": "spacs.verification",
        "label": "Verification Queue",
        "icon": "Inbox",
        "to": "/spacs/verification",
        "required_permission": "spacs.application.review",
        "sort_order": 30,
    },
    {
        "code": "spacs.decisions",
        "label": "Scholarship Decisions",
        "icon": "ClipboardCheck",
        "to": "/spacs/decisions",
        "required_permission": "spacs.application.approve",
        "sort_order": 40,
    },
    {
        "code": "spacs.awards",
        "label": "Convocation Awards",
        "icon": "Award",
        "to": "/spacs/awards",
        "required_permission": "spacs.award.publish",
        "sort_order": 50,
    },
]

PERMISSIONS = [
    ("spacs.scheme.view", "Browse scholarship and award catalogue schemes"),
    ("spacs.scheme.create", "Create scholarship and award catalogue schemes"),
    ("spacs.scheme.update", "Update scholarship and award catalogue schemes"),
    ("spacs.cycle.view", "View award cycle details and deadlines"),
    ("spacs.cycle.create", "Create and announce award cycles"),
    ("spacs.cycle.publish", "Publish award cycle announcements and outcomes"),
    ("spacs.application.create", "Submit scholarship or renewal applications"),
    ("spacs.application.view", "View visible scholarship applications"),
    ("spacs.application.update", "Amend or withdraw pending applications"),
    ("spacs.application.review", "Verify and evaluate scholarship applications"),
    ("spacs.application.approve", "Sanction or reject scholarship applications"),
    ("spacs.award.view", "View convocation and scholarship awards"),
    ("spacs.award.create", "Create award disbursement and ledger records"),
    ("spacs.award.publish", "Publish approved convocation award lists"),
    ("spacs.award.export", "Export awards and financial disbursement data"),
    ("spacs.audit.view", "View SPACS module audit trail"),
]

SYSTEM_PERMISSIONS = [
    "spacs.sla.escalate",
    "spacs.reminder.send",
]

_STUDENT = [
    "spacs.scheme.view",
    "spacs.cycle.view",
    "spacs.application.create",
    "spacs.application.view",
    "spacs.application.update",
    "spacs.award.view",
]

_ASSISTANT = [
    "spacs.scheme.view",
    "spacs.cycle.view",
    "spacs.application.view",
    "spacs.application.review",
]

_CONVENER = [
    "spacs.scheme.view",
    "spacs.scheme.create",
    "spacs.scheme.update",
    "spacs.cycle.view",
    "spacs.cycle.create",
    "spacs.cycle.publish",
    "spacs.application.view",
    "spacs.application.review",
    "spacs.application.approve",
    "spacs.award.view",
    "spacs.award.create",
    "spacs.award.publish",
    "spacs.award.export",
    "spacs.audit.view",
]

_COMMITTEE = [
    "spacs.scheme.view",
    "spacs.cycle.view",
    "spacs.application.view",
    "spacs.application.review",
    "spacs.award.view",
]

_ACCOUNTS = [
    "spacs.scheme.view",
    "spacs.award.view",
    "spacs.award.create",
    "spacs.award.export",
]

_AUDITOR = [
    "spacs.audit.view",
]

ROLE_GRANTS = {
    "student": _STUDENT,
    "spacs_assistant": _ASSISTANT,
    "spacs_convener": _CONVENER,
    "award_evaluation_committee": _COMMITTEE,
    "accounts_admin": _ACCOUNTS,
    "spacs_auditor": _AUDITOR,
}
