MODULE = {
    "code": "oap",
    "label": "Other Academic Procedures",
    "icon": "GraduationCap",
    "base_path": "/oap",
    "nav_section": "Academics",
    "sort_order": 30,
    "status": "planned",
}

NAV_ITEMS = []

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("oap.leave.submit", "Submit a leave application"),
    ("oap.leave.view_self", "See one's own leave applications"),
    ("oap.leave.decide", "Approve or reject student leave"),
    ("oap.bonafide.submit", "Request a bonafide certificate"),
    ("oap.bonafide.view_self", "See one's own bonafide requests"),
    ("oap.bonafide.decide", "Approve or reject bonafide requests"),
    ("oap.seminar.request", "Request a PG seminar"),
    ("oap.seminar.schedule", "Schedule PG seminars"),
    ("oap.seminar.view", "See the seminar schedule"),
    ("oap.assignment.manage", "Record supervisor and TA assignments"),
    ("oap.nodues.submit", "Start a no-dues clearance"),
    ("oap.nodues.view_self", "See one's own no-dues clearance"),
    ("oap.nodues.finalize", "Finalize no-dues clearances"),
    ("oap.nodues.verify_library", "Record the library no-dues result"),
    ("oap.nodues.verify_hostel", "Record the hostel no-dues result"),
    ("oap.nodues.verify_mess", "Record the mess no-dues result"),
    ("oap.nodues.verify_department", "Record the department no-dues result"),
    ("oap.nodues.verify_lab", "Record the lab no-dues result"),
    ("oap.nodues.verify_academic_section",
     "Record the academic section no-dues result"),
    ("oap.nodues.verify_student_section",
     "Record the student section no-dues result"),
    ("oap.assistantship.submit", "Submit an assistantship claim"),
    ("oap.assistantship.view_self", "See one's own assistantship claims"),
    ("oap.assistantship.verify", "Verify a supervised student's claim"),
    ("oap.assistantship.review", "Review and forward department claims"),
    ("oap.assistantship.decide", "Approve or reject assistantship claims"),
    ("oap.assistantship.process_stipend", "Process approved stipends"),
]

SYSTEM_PERMISSIONS = []

_STUDENT = [
    "oap.leave.submit",
    "oap.leave.view_self",
    "oap.bonafide.submit",
    "oap.bonafide.view_self",
    "oap.nodues.submit",
    "oap.nodues.view_self",
    "oap.seminar.request",
    "oap.seminar.view",
    "oap.assistantship.submit",
    "oap.assistantship.view_self",
]

_FACULTY = [
    "oap.assistantship.verify",
    "oap.seminar.view",
]

_HOD = [
    *_FACULTY,
    "oap.leave.decide",
    "oap.assistantship.decide",
]

_DEPARTMENT_ADMIN = [
    "oap.assignment.manage",
    "oap.assistantship.review",
    "oap.seminar.schedule",
]

_ACADEMIC_ADMIN = [
    "oap.bonafide.decide",
    "oap.nodues.finalize",
    "oap.assistantship.process_stipend",
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "student": _STUDENT,
    "faculty": _FACULTY,
    "HOD": _HOD,
    "Department Admin": _DEPARTMENT_ADMIN,
    "Academic Admin": _ACADEMIC_ADMIN,
    "Librarian": ["oap.nodues.verify_library"],
    "Hostel Warden": ["oap.nodues.verify_hostel"],
    "Mess In-charge": ["oap.nodues.verify_mess"],
    "Department Verifier": ["oap.nodues.verify_department"],
    "Lab Supervisor": ["oap.nodues.verify_lab"],
    "Academic Section Verifier": ["oap.nodues.verify_academic_section"],
    "Student Section Verifier": ["oap.nodues.verify_student_section"],
}
