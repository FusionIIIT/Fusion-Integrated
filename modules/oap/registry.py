MODULE = {
    "code": "oap",
    "label": "Other Academic Procedures",
    "icon": "GraduationCap",
    "base_path": "/oap",
    "nav_section": "Academics",
    "sort_order": 25,
    "status": "active"
}

NAV_ITEMS = [
    {
        "code": "oap.dashboard",
        "label": "OAP Dashboard",
        "icon": "GraduationCap",
        "to": "/oap",
        "required_permission": "oap.view",
        "sort_order": 5
    },
    {
        "code": "oap.leave",
        "label": "Student Leave",
        "icon": "CalendarBlank",
        "to": "/oap/leave",
        "required_permission": "oap.leave.apply",
        "sort_order": 10
    },
    {
        "code": "oap.bonafide",
        "label": "Bonafide Certificate",
        "icon": "Certificate",
        "to": "/oap/bonafide",
        "required_permission": "oap.bonafide.request",
        "sort_order": 20
    },
    {
        "code": "oap.nodues",
        "label": "No-Dues Clearance",
        "icon": "Checks",
        "to": "/oap/no-dues",
        "required_permission": "oap.nodues.initiate",
        "sort_order": 30
    },
    {
        "code": "oap.assistantship",
        "label": "Assistantship Claims",
        "icon": "CurrencyDollar",
        "to": "/oap/assistantship",
        "required_permission": "oap.assistantship.submit",
        "sort_order": 40
    },
    {
        "code": "oap.seminars",
        "label": "Graduate Seminars",
        "icon": "Presentation",
        "to": "/oap/seminars",
        "required_permission": "oap.seminar.view",
        "sort_order": 50
    },
    {
        "code": "oap.assignments",
        "label": "Supervisor & TA Assignments",
        "icon": "Users",
        "to": "/oap/assignments",
        "required_permission": "oap.assignment.manage",
        "sort_order": 60
    },
]

PERMISSIONS = [
    ("oap.view", "View OAP procedures"),
    ("oap.leave.apply", "Apply for student leave"),
    ("oap.leave.review_hod", "Review and approve/reject leave as HOD"),
    ("oap.bonafide.request", "Request bonafide certificate"),
    ("oap.bonafide.decide", "Approve or reject bonafide certificate"),
    ("oap.nodues.initiate", "Initiate no-dues clearance"),
    ("oap.nodues.verify_authority", "Verify clearance for authority domain"),
    ("oap.nodues.finalize", "Finalize no-dues clearance"),
    ("oap.assistantship.submit", "Submit PG assistantship claim"),
    ("oap.assistantship.verify_supervisor", "Verify assistantship as supervisor"),
    ("oap.assistantship.review_dept", "Review assistantship at department level"),
    ("oap.assistantship.decide_hod", "HoD decision on assistantship claim"),
    ("oap.assistantship.disburse_stipend", "Disburse assistantship stipend"),
    ("oap.assignment.manage", "Assign thesis supervisors and TAs"),
    ("oap.seminar.request", "Request graduate seminar"),
    ("oap.seminar.schedule", "Schedule graduate seminar"),
    ("oap.seminar.view", "View graduate seminars"),
]

ROLE_GRANTS = {
    "student": ["oap.view", "oap.leave.apply", "oap.bonafide.request", "oap.nodues.initiate", "oap.assistantship.submit", "oap.seminar.request", "oap.seminar.view"],
    "faculty": ["oap.view", "oap.seminar.view", "oap.assistantship.verify_supervisor"],
    "HOD": ["oap.view", "oap.leave.review_hod", "oap.assistantship.decide_hod", "oap.seminar.view"],
    "Academic Administrator": ["oap.view", "oap.bonafide.decide", "oap.nodues.finalize", "oap.assistantship.disburse_stipend", "oap.seminar.view"],
    "Department Administrator": ["oap.view", "oap.assignment.manage", "oap.assistantship.review_dept", "oap.seminar.schedule", "oap.seminar.view"],
    "Librarian": ["oap.view", "oap.nodues.verify_authority"],
    "Hostel Warden": ["oap.view", "oap.nodues.verify_authority"],
    "Mess In-charge": ["oap.view", "oap.nodues.verify_authority"],
    "Lab Supervisor": ["oap.view", "oap.nodues.verify_authority"],
    "admin": ["oap.view", "oap.leave.apply", "oap.leave.review_hod", "oap.bonafide.request", "oap.bonafide.decide", "oap.nodues.initiate", "oap.nodues.verify_authority", "oap.nodues.finalize", "oap.assistantship.submit", "oap.assistantship.verify_supervisor", "oap.assistantship.review_dept", "oap.assistantship.decide_hod", "oap.assistantship.disburse_stipend", "oap.assignment.manage", "oap.seminar.request", "oap.seminar.schedule", "oap.seminar.view"],
}
