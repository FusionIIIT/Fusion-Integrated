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
        "required_permission": "spacs.catalogue.view",
        "sort_order": 10,
    },
    {
        "code": "spacs.mine",
        "label": "My Applications",
        "icon": "UserCheck",
        "to": "/spacs/mine",
        "required_permission": "spacs.application.view_self",
        "sort_order": 20,
    },
    {
        "code": "spacs.verification",
        "label": "Verification Queue",
        "icon": "Inbox",
        "to": "/spacs/verification",
        "required_permission": "spacs.application.verify",
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
        "required_permission": "spacs.award.prepare",
        "sort_order": 50,
    },
]

PERMISSIONS = [
    ("spacs.catalogue.view", "Browse scholarship and award catalogue"),
    ("spacs.catalogue.manage", "Create and manage scholarship and award catalogue entries"),
    ("spacs.application.create", "Apply for scholarship or renewal"),
    ("spacs.application.view_self", "View and track own applications and status history"),
    ("spacs.application.withdraw", "Withdraw own eligible pending application"),
    ("spacs.application.verify", "Verify application completeness and evidence"),
    ("spacs.application.approve", "Make final scholarship sanction or rejection decision"),
    ("spacs.award.prepare", "Prepare and manage convocation award candidate pool"),
    ("spacs.award.evaluate", "Evaluate, shortlist, and score award candidates"),
    ("spacs.award.record_outcome", "Record final award outcomes and approval reference"),
    ("spacs.award.publish", "Publish approved convocation award results"),
    ("spacs.audit.view", "View SPACS module audit trail"),
]

SYSTEM_PERMISSIONS = [
    "spacs.sla.escalate",
    "spacs.reminder.send",
]

_STUDENT = [
    "spacs.catalogue.view",
    "spacs.application.create",
    "spacs.application.view_self",
    "spacs.application.withdraw",
]

_ASSISTANT = [
    "spacs.catalogue.view",
    "spacs.application.verify",
]

_CONVENER = [
    "spacs.catalogue.view",
    "spacs.catalogue.manage",
    "spacs.application.approve",
    "spacs.award.prepare",
    "spacs.award.record_outcome",
    "spacs.award.publish",
    "spacs.audit.view",
]

_COMMITTEE = [
    "spacs.catalogue.view",
    "spacs.award.evaluate",
]

_AUDITOR = [
    "spacs.audit.view",
]

ROLE_GRANTS = {
    "student": _STUDENT,
    "spacs_assistant": _ASSISTANT,
    "spacs_convener": _CONVENER,
    "award_evaluation_committee": _COMMITTEE,
    "spacs_auditor": _AUDITOR,
}
