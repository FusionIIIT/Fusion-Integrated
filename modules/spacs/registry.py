"""What the server tells the shell about SPACS (Awards & Scholarships).

Nav items carry required_permission and the server filters before sending.
"""

MODULE = {
    "code": "spacs",
    "label": "Awards & Scholarships",
    "icon": "FaAward",
    "base_path": "/spacs",
    "nav_section": "Academics",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    # -- Student navigation ---
    {
        "code": "spacs.catalogue",
        "label": "Opportunities",
        "icon": "FaAward",
        "to": "/spacs/catalogue",
        "required_permission": "spacs.catalogue.view",
        "sort_order": 10,
    },
    {
        "code": "spacs.mine",
        "label": "My Applications",
        "icon": "FaUserCheck",
        "to": "/spacs/mine",
        "required_permission": "spacs.application.view_self",
        "sort_order": 20,
    },
    {
        "code": "spacs.awards",
        "label": "Award Results",
        "icon": "FaTrophy",
        "to": "/spacs/awards",
        "required_permission": "spacs.award.view",
        "sort_order": 30,
    },
    # -- Staff navigation (Assistant / Convener / Committee) ---
    {
        "code": "spacs.verification_queue",
        "label": "Verification Queue",
        "icon": "FaInbox",
        "to": "/spacs/verification-queue",
        "required_permission": "spacs.application.review",
        "sort_order": 40,
    },
    {
        "code": "spacs.decision_queue",
        "label": "Decision Queue",
        "icon": "FaClipboardCheck",
        "to": "/spacs/decision-queue",
        "required_permission": "spacs.application.approve",
        "sort_order": 50,
    },
    {
        "code": "spacs.catalogue_admin",
        "label": "Catalogue Admin",
        "icon": "FaBook",
        "to": "/spacs/catalogue-admin",
        "required_permission": "spacs.catalogue.manage",
        "sort_order": 60,
    },
    {
        "code": "spacs.award_management",
        "label": "Award Cycles",
        "icon": "FaMedal",
        "to": "/spacs/award-management",
        "required_permission": "spacs.award.manage",
        "sort_order": 70,
    },
    {
        "code": "spacs.audit_trail",
        "label": "Audit Trail",
        "icon": "FaHistory",
        "to": "/spacs/audit-trail",
        "required_permission": "spacs.audit.view",
        "sort_order": 80,
    },
]

PERMISSIONS = [
    ("spacs.catalogue.view", "Browse published scholarship and award catalogue entries"),
    ("spacs.catalogue.manage", "Create, edit, publish and retire catalogue entries"),
    ("spacs.application.view_self", "View own scholarship applications and renewals"),
    ("spacs.application.create", "Submit or draft a scholarship application"),
    ("spacs.application.update", "Modify or correct a pending application"),
    ("spacs.application.delete", "Withdraw a pending application"),
    ("spacs.application.view", "View scholarship applications within assigned scope"),
    ("spacs.application.review", "Verify scholarship application completeness and evidence"),
    ("spacs.application.approve", "Approve, reject, or return scholarship applications for decision"),
    ("spacs.award.manage", "Prepare and finalize award candidate pool"),
    ("spacs.award.review", "Evaluate and shortlist award candidates"),
    ("spacs.award.approve", "Record final award outcome and approval reference"),
    ("spacs.award.publish", "Publish approved award results"),
    ("spacs.award.view", "View award candidate evaluations and published results"),
    ("spacs.export.view", "Export application or award data"),
    ("spacs.audit.view", "View SPACS audit trail"),
]

SYSTEM_PERMISSIONS = [
    "spacs.task.sla_reminder",
    "spacs.task.renewal_reminder",
    "spacs.task.reassign_roles",
]

_STUDENT = [
    "spacs.catalogue.view",
    "spacs.application.view_self",
    "spacs.application.create",
    "spacs.application.update",
    "spacs.application.delete",
    "spacs.award.view",
]

_ASSISTANT = [
    "spacs.catalogue.view",
    "spacs.application.view",
    "spacs.application.review",
    "spacs.award.view",
    "spacs.export.view",
]

_COMMITTEE = [
    "spacs.catalogue.view",
    "spacs.award.review",
    "spacs.award.view",
]

_CONVENER = [
    "spacs.catalogue.view",
    "spacs.catalogue.manage",
    "spacs.application.view",
    "spacs.application.approve",
    "spacs.award.manage",
    "spacs.award.review",
    "spacs.award.approve",
    "spacs.award.publish",
    "spacs.award.view",
    "spacs.export.view",
    "spacs.audit.view",
]

_GENERAL_USER = [
    "spacs.catalogue.view",
    "spacs.award.view",
]

ROLE_GRANTS = {
    "student": _STUDENT,
    "spacs_assistant": _ASSISTANT,
    "assistant": _ASSISTANT,
    "spacs_convener": _CONVENER,
    "convener": _CONVENER,
    "award_committee": _COMMITTEE,
    "faculty": _GENERAL_USER,
    "staff": _GENERAL_USER,
    "acadadmin": _ASSISTANT,
    "Dean Academic": _CONVENER,
}
