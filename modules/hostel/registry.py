"""What the server tells the shell about this module (ADR-0010).
"""
MODULE = {
    "code": "hostel",
    "label": "Hostel Management",
    "icon": "Buildings",
    "base_path": "/hostel",
    "nav_section": "Hostel",
    "sort_order": 15,
    "status": "active",
}

NAV_ITEMS = [
    # -- Student --
    {
        "code": "hostel.accommodations",
        "label": "Accommodations",
        "icon": "House",
        "to": "/hostel/accommodations",
        "required_permission": "hostel.accommodation.view",
        "sort_order": 10,
    },
    {
        "code": "hostel.leaves",
        "label": "Leaves",
        "icon": "CalendarBlank",
        "to": "/hostel/leaves",
        "required_permission": "hostel.leave.view",
        "sort_order": 20,
    },
    {
        "code": "hostel.complaints",
        "label": "Complaints",
        "icon": "ChatCircle",
        "to": "/hostel/complaints",
        "required_permission": "hostel.complaint.view",
        "sort_order": 30,
    },
    {
        "code": "hostel.fines",
        "label": "Fines",
        "icon": "Receipt",
        "to": "/hostel/fines",
        "required_permission": "hostel.fine.view",
        "sort_order": 40,
    },
    {
        "code": "hostel.notices",
        "label": "Notices",
        "icon": "Megaphone",
        "to": "/hostel/notices",
        "required_permission": "hostel.notice.view",
        "sort_order": 50,
    },
]

PERMISSIONS = [
    ("hostel.room.view", "View hostel and room information"),
    ("hostel.room.manage", "Manage hostels and rooms"),
    ("hostel.accommodation.view", "View accommodation requests"),
    ("hostel.accommodation.create", "Submit accommodation request"),
    ("hostel.allotment.manage", "Manage batch and room allotments"),
    ("hostel.leave.view", "View leave requests"),
    ("hostel.leave.create", "Submit leave request"),
    ("hostel.leave.review", "Review and approve/reject leave requests"),
    ("hostel.complaint.view", "View hostel complaints"),
    ("hostel.complaint.create", "Submit hostel complaint"),
    ("hostel.complaint.review", "Review, escalate, or resolve complaints"),
    ("hostel.attendance.view", "View student attendance"),
    ("hostel.attendance.create", "Record student attendance"),
    ("hostel.fine.view", "View hostel fine records"),
    ("hostel.fine.create", "Impose hostel fines"),
    ("hostel.notice.view", "View hostel notices"),
    ("hostel.notice.publish", "Publish hostel notices"),
    ("hostel.inventory.manage", "Manage hostel inventory"),
    ("hostel.security.manage", "Manage security shifts"),
    ("hostel.report.view", "View operational reports"),
]

SYSTEM_PERMISSIONS = []

_STUDENT = [
    "hostel.room.view",
    "hostel.accommodation.view",
    "hostel.accommodation.create",
    "hostel.leave.view",
    "hostel.leave.create",
    "hostel.complaint.view",
    "hostel.complaint.create",
    "hostel.attendance.view",
    "hostel.fine.view",
    "hostel.notice.view",
]

_CARETAKER = [
    "hostel.room.view",
    "hostel.room.manage",
    "hostel.accommodation.view",
    "hostel.leave.view",
    "hostel.leave.review",
    "hostel.complaint.view",
    "hostel.complaint.review",
    "hostel.attendance.view",
    "hostel.attendance.create",
    "hostel.fine.view",
    "hostel.fine.create",
    "hostel.notice.view",
    "hostel.notice.publish",
    "hostel.inventory.manage",
]

_WARDEN = [
    "hostel.room.view",
    "hostel.accommodation.view",
    "hostel.leave.view",
    "hostel.complaint.view",
    "hostel.complaint.review",
    "hostel.attendance.view",
    "hostel.fine.view",
    "hostel.fine.create",
    "hostel.notice.view",
    "hostel.notice.publish",
    "hostel.security.manage",
    "hostel.report.view",
]

ROLE_GRANTS = {
    "student": _STUDENT,
    "caretaker": _CARETAKER,
    "warden": _WARDEN,
    "Super Admin": _WARDEN + _CARETAKER + ["hostel.allotment.manage"],
}
