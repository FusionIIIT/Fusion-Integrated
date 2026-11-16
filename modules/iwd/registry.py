MODULE = {
    "code": "iwd", "label": "Infrastructure and Works", "icon": "Building",
    "base_path": "/iwd", "nav_section": "Institute Services",
    "sort_order": 25, "status": "active",
}

NAV_ITEMS = [
    {"code": "iwd.complaints", "label": "IWD", "icon": "Building",
     "to": "/iwd", "required_permission": "iwd.complaint.view", "sort_order": 10},
    {"code": "iwd.tasks", "label": "IWD Tasks", "icon": "Checklist",
     "to": "/iwd/tasks", "required_permission": "iwd.workflow.review", "sort_order": 20},
]

PERMISSIONS = [
    ("iwd.complaint.view", "View IWD complaints"),
    ("iwd.complaint.submit", "Submit maintenance complaint"),
    ("iwd.complaint.assess", "Assess assigned complaint"),
    ("iwd.estimate.submit", "Prepare and submit estimate"),
    ("iwd.workflow.review", "Review IWD approval tasks"),
]

ROLE_GRANTS = {
    "Institute Employee": ["iwd.complaint.view", "iwd.complaint.submit"],
    "Engineer": ["iwd.complaint.view", "iwd.complaint.assess", "iwd.estimate.submit"],
    "IWD Admin": [code for code, _ in PERMISSIONS],
    "Review Committee": ["iwd.complaint.view", "iwd.workflow.review"],
    "Department Head": ["iwd.complaint.view", "iwd.workflow.review"],
    "Dean": ["iwd.complaint.view"],
    "Director": ["iwd.complaint.view", "iwd.workflow.review"],
}
