"""SPACS-owned module registration and permission catalogue."""

MODULE = {
    "code": "spacs",
    "label": "Scholarships and Awards",
    "icon": "GraduationCap",
    "base_path": "/spacs",
    "nav_section": "Student Services",
    "sort_order": 30,
    "status": "active",
}

PERMISSIONS = [
    ("spacs.catalogue.view", "View published scholarships and awards"),
    ("spacs.catalogue.manage", "Create and maintain catalogue versions"),
    ("spacs.catalogue.publish", "Publish or retire catalogue versions"),
    ("spacs.application.create", "Create and submit own applications"),
    ("spacs.application.view_self", "View own applications and history"),
    ("spacs.application.view", "View assigned scholarship applications"),
    ("spacs.application.verify", "Record application verification findings"),
    ("spacs.application.decide", "Record scholarship and renewal decisions"),
    ("spacs.application.export", "Export authorized application records"),
    ("spacs.award.view", "View award cycles and published results"),
    ("spacs.award.manage", "Prepare award candidate pools"),
    ("spacs.award.evaluate", "Record award committee evaluations"),
    ("spacs.award.publish", "Record approval and publish award results"),
    ("spacs.audit.view", "View SPACS audit history"),
]

SYSTEM_PERMISSIONS = []

NAV_ITEMS = [
    {
        "code": "spacs.catalogue",
        "label": "Scholarships and Awards",
        "icon": "GraduationCap",
        "to": "/spacs/catalogue",
        "required_permission": "spacs.catalogue.view",
        "sort_order": 10,
    },
    {
        "code": "spacs.applications",
        "label": "My Applications",
        "icon": "FileText",
        "to": "/spacs/applications",
        "required_permission": "spacs.application.view_self",
        "sort_order": 20,
    },
    {
        "code": "spacs.review",
        "label": "Application Review",
        "icon": "ClipboardCheck",
        "to": "/spacs/review",
        "required_permission": "spacs.application.view",
        "sort_order": 30,
    },
    {
        "code": "spacs.awards",
        "label": "Award Cycles",
        "icon": "Trophy",
        "to": "/spacs/awards",
        "required_permission": "spacs.award.view",
        "sort_order": 40,
    },
]

# The specification names actors but does not establish their IAM designation
# keys. Do not populate ROLE_GRANTS until that mapping is supplied.
ROLE_GRANTS = {}
