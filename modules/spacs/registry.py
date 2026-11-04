"""What the server tells the shell about SPACS (ADR-0010).

Nav items carry `required_permission` and the server filters before sending.
Permissions are validated by permission_manifest and nav_matches_routes.
"""

MODULE = {
    "code": "spacs",
    "label": "Awards & Scholarships",
    "icon": "Award",
    "base_path": "/spacs",
    "nav_section": "Academics",
    "sort_order": 25,
    "status": "active",
}

NAV_ITEMS = [
    # -- Student screens --
    {
        "code": "spacs.catalogue",
        "label": "Scholarship Catalogue",
        "icon": "BookOpen",
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
        "code": "spacs.awards_public",
        "label": "Convocation Awards",
        "icon": "Trophy",
        "to": "/spacs/awards",
        "required_permission": "spacs.award.view",
        "sort_order": 30,
    },

    # -- Staff / Reviewer screens --
    {
        "code": "spacs.verification",
        "label": "Application Verification",
        "icon": "Checks",
        "to": "/spacs/verification",
        "required_permission": "spacs.application.verify",
        "sort_order": 40,
    },
    {
        "code": "spacs.decisions",
        "label": "Scholarship Decisions",
        "icon": "Gavel",
        "to": "/spacs/decisions",
        "required_permission": "spacs.application.decide",
        "sort_order": 50,
    },
    {
        "code": "spacs.committee_eval",
        "label": "Award Evaluation",
        "icon": "Users",
        "to": "/spacs/evaluation",
        "required_permission": "spacs.award.evaluate",
        "sort_order": 60,
    },
    {
        "code": "spacs.admin_manage",
        "label": "Catalogue Admin",
        "icon": "Sliders",
        "to": "/spacs/admin",
        "required_permission": "spacs.catalogue.manage",
        "sort_order": 70,
    },
    {
        "code": "spacs.audit_trail",
        "label": "SPACS Audit Trail",
        "icon": "ShieldCheck",
        "to": "/spacs/audit",
        "required_permission": "spacs.audit.view",
        "sort_order": 80,
    },
]

PERMISSIONS = [
    ("spacs.catalogue.view", "Browse published scholarship/award catalogue"),
    ("spacs.catalogue.manage", "Create, version, and retire catalogue entries"),
    ("spacs.application.view_self", "View own scholarship applications and status history"),
    ("spacs.application.create", "Create drafts and submit scholarship/renewal applications"),
    ("spacs.application.modify_self", "Modify editable/returned scholarship applications"),
    ("spacs.application.withdraw_self", "Withdraw own pending applications before final decision"),
    ("spacs.application.export", "Export/print own submitted scholarship applications"),
    ("spacs.application.verify", "Review applications, record findings, request corrections, flag concerns"),
    ("spacs.application.decide", "Approve, reject, or return verified applications"),
    ("spacs.application.view_all", "View all submitted applications across the institute"),
    ("spacs.award.view", "View award catalogue entries and published award results"),
    ("spacs.award.manage", "Prepare candidate pools and record institutional approvals"),
    ("spacs.award.evaluate", "Evaluate and shortlist assigned award candidates"),
    ("spacs.award.publish", "Publish officially approved convocation award results"),
    ("spacs.audit.view", "Inspect SPACS audit history and decision provenance"),
]

SYSTEM_PERMISSIONS = [
    "spacs.sla.escalate",
    "spacs.renewal.remind",
]

_STUDENT = [
    "spacs.catalogue.view",
    "spacs.application.view_self",
    "spacs.application.create",
    "spacs.application.modify_self",
    "spacs.application.withdraw_self",
    "spacs.application.export",
    "spacs.award.view",
]

# SPACS Assistant: CANNOT approve, reject, or make final sanction decisions
_ASSISTANT = [
    "spacs.catalogue.view",
    "spacs.application.verify",
    "spacs.application.export",
    "spacs.award.view",
]

# SPACS Convener: Operational admin and final scholarship sanction authority
_CONVENER = [
    "spacs.catalogue.view",
    "spacs.catalogue.manage",
    "spacs.application.verify",
    "spacs.application.decide",
    "spacs.application.view_all",
    "spacs.application.export",
    "spacs.award.view",
    "spacs.award.manage",
    "spacs.award.publish",
    "spacs.audit.view",
]

# Award Evaluation Committee: Scoped strictly to evaluating candidates
_COMMITTEE = [
    "spacs.catalogue.view",
    "spacs.award.view",
    "spacs.award.evaluate",
]

# Dean Academic: Oversight and audit access
_DEAN = [
    "spacs.catalogue.view",
    "spacs.award.view",
    "spacs.audit.view",
]

_AUDITOR = [
    "spacs.catalogue.view",
    "spacs.audit.view",
]

ROLE_GRANTS = {
    "student": _STUDENT,
    "spacs_assistant": _ASSISTANT,
    "spacs_convener": _CONVENER,
    "award_eval_committee": _COMMITTEE,
    "Dean Academic": _DEAN,
    "spacs_auditor": _AUDITOR,
}
