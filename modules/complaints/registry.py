MODULE = {
    "code": "complaints", "label": "Complaints", "icon": "FaLayerGroup",
    "base_path": "/complaints", "nav_section": "Campus", "sort_order": 70,
    "status": "active",
}

NAV_ITEMS = [{
    "code": "complaints.submit", "label": "Submit a Complaint",
    "icon": "FaClipboardList", "to": "/complaints/submit",
    "required_permission": "complaints.complaint.create", "sort_order": 5,
}]

PERMISSIONS = [
    ("complaints.complaint.create", "Submit a complaint"),
]

ROLE_GRANTS = {
    "student": ["complaints.complaint.create"],
    "faculty": ["complaints.complaint.create"],
    "staff": ["complaints.complaint.create"],
}
