"""What the server tells the shell about OAP (ADR-0010).

Defines navigation items, permissions catalog, and role bindings corresponding to OAP specifications.
"""

from modules.oap.domain import permissions as p

MODULE = {
    "code": "oap",
    "label": "Other Academic Procedures",
    "icon": "GraduationCap",
    "base_path": "/oap",
    "nav_section": "Academics",
    "sort_order": 25,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "oap.leave",
        "label": "Leave Applications",
        "icon": "CalendarBlank",
        "to": "/oap/leave",
        "required_permission": p.P_STUDENT_LEAVE_VIEW,
        "sort_order": 10,
    },
    {
        "code": "oap.bonafide",
        "label": "Bonafide Certificate",
        "icon": "FileText",
        "to": "/oap/bonafide",
        "required_permission": p.P_STUDENT_BONAFIDE_VIEW,
        "sort_order": 20,
    },
    {
        "code": "oap.nodues",
        "label": "No-Dues Clearance",
        "icon": "CheckCircle",
        "to": "/oap/nodues",
        "required_permission": p.P_STUDENT_NODUES_VIEW,
        "sort_order": 30,
    },
    {
        "code": "oap.assistantship",
        "label": "PG Assistantship",
        "icon": "CurrencyInr",
        "to": "/oap/assistantship",
        "required_permission": p.P_STUDENT_ASSISTANTSHIP_VIEW,
        "sort_order": 40,
    },
    {
        "code": "oap.seminars",
        "label": "Graduate Seminars",
        "icon": "ChalkboardTeacher",
        "to": "/oap/seminars",
        "required_permission": p.P_FACULTY_SEMINAR_VIEW,
        "sort_order": 50,
    },
    {
        "code": "oap.assignments",
        "label": "Supervisor & TA Assignments",
        "icon": "Users",
        "to": "/oap/assignments",
        "required_permission": p.P_DEPT_ADMIN_ASSIGNMENT_MANAGE,
        "sort_order": 60,
    },
    {
        "code": "oap.clearance",
        "label": "Authority Clearances",
        "icon": "Stamp",
        "to": "/oap/clearances",
        "required_permission": p.P_NODUES_VERIFY,
        "sort_order": 70,
    },
]

PERMISSIONS = [
    (p.P_STUDENT_LEAVE_APPLY, "Apply for student leave"),
    (p.P_STUDENT_LEAVE_VIEW, "View own student leave applications"),
    (p.P_STUDENT_BONAFIDE_REQUEST, "Request a bonafide certificate"),
    (p.P_STUDENT_BONAFIDE_VIEW, "View own bonafide certificate requests"),
    (p.P_STUDENT_BONAFIDE_DOWNLOAD, "Download approved bonafide certificate"),
    (p.P_STUDENT_NODUES_INITIATE, "Initiate no-dues clearance request"),
    (p.P_STUDENT_NODUES_VIEW, "Track no-dues clearance progress"),
    (p.P_STUDENT_NODUES_DOWNLOAD, "Download finalized no-dues certificate"),
    (p.P_STUDENT_ASSISTANTSHIP_SUBMIT, "Submit PG assistantship claim"),
    (p.P_STUDENT_ASSISTANTSHIP_VIEW, "View and track own assistantship claims"),
    (p.P_STUDENT_SEMINAR_REQUEST, "Request graduate seminar scheduling"),
    (p.P_STUDENT_SEMINAR_VIEW, "View graduate seminar schedules"),
    (p.P_FACULTY_SEMINAR_VIEW, "View graduate seminar schedules as faculty"),
    (p.P_SUPERVISOR_VERIFY_THESIS, "Verify assistantship claim as Thesis Supervisor"),
    (p.P_SUPERVISOR_VERIFY_TA, "Verify assistantship claim as TA Supervisor"),
    (p.P_HOD_LEAVE_DECIDE, "Approve or reject student leave as HoD"),
    (p.P_HOD_LEAVE_VIEW_DEPT, "View department student leave applications as HoD"),
    (p.P_HOD_ASSISTANTSHIP_DECIDE, "Approve or reject assistantship claims as HoD"),
    (p.P_ACAD_ADMIN_BONAFIDE_DECIDE, "Verify and decide bonafide requests as Academic Administrator"),
    (p.P_ACAD_ADMIN_NODUES_FINALIZE, "Finalize no-dues clearance as Academic Administrator"),
    (p.P_ACAD_ADMIN_ASSISTANTSHIP_DISBURSE, "Process stipend disbursement as Academic Administrator"),
    (p.P_DEPT_ADMIN_ASSIGNMENT_MANAGE, "Record Thesis and TA assignments as Department Administrator"),
    (p.P_DEPT_ADMIN_SEMINAR_SCHEDULE, "Schedule graduate seminars as Department Administrator"),
    (p.P_DEPT_ADMIN_ASSISTANTSHIP_REVIEW, "Review and forward assistantship claims as Department Administrator"),
    (p.P_NODUES_VERIFY, "Record authority clearance for student no-dues request"),
    (p.P_NOTIFICATION_VIEW, "View OAP notifications and alerts"),
]

SYSTEM_PERMISSIONS = []
SCOPE_PERMISSIONS = []

_STUDENT = [
    p.P_STUDENT_LEAVE_APPLY,
    p.P_STUDENT_LEAVE_VIEW,
    p.P_STUDENT_BONAFIDE_REQUEST,
    p.P_STUDENT_BONAFIDE_VIEW,
    p.P_STUDENT_BONAFIDE_DOWNLOAD,
    p.P_STUDENT_NODUES_INITIATE,
    p.P_STUDENT_NODUES_VIEW,
    p.P_STUDENT_NODUES_DOWNLOAD,
    p.P_STUDENT_ASSISTANTSHIP_SUBMIT,
    p.P_STUDENT_ASSISTANTSHIP_VIEW,
    p.P_STUDENT_SEMINAR_REQUEST,
    p.P_STUDENT_SEMINAR_VIEW,
    p.P_NOTIFICATION_VIEW,
]

_FACULTY = [
    p.P_FACULTY_SEMINAR_VIEW,
    p.P_SUPERVISOR_VERIFY_THESIS,
    p.P_SUPERVISOR_VERIFY_TA,
    p.P_NOTIFICATION_VIEW,
]

_HOD = [
    p.P_FACULTY_SEMINAR_VIEW,
    p.P_HOD_LEAVE_DECIDE,
    p.P_HOD_LEAVE_VIEW_DEPT,
    p.P_HOD_ASSISTANTSHIP_DECIDE,
    p.P_NOTIFICATION_VIEW,
]

_ACADADMIN = [
    p.P_ACAD_ADMIN_BONAFIDE_DECIDE,
    p.P_ACAD_ADMIN_NODUES_FINALIZE,
    p.P_ACAD_ADMIN_ASSISTANTSHIP_DISBURSE,
    p.P_NOTIFICATION_VIEW,
]

_DEPT_ADMIN = [
    p.P_DEPT_ADMIN_ASSIGNMENT_MANAGE,
    p.P_DEPT_ADMIN_SEMINAR_SCHEDULE,
    p.P_DEPT_ADMIN_ASSISTANTSHIP_REVIEW,
    p.P_NOTIFICATION_VIEW,
]

_CLEARANCE_AUTHORITY = [
    p.P_NODUES_VERIFY,
    p.P_NOTIFICATION_VIEW,
]

ROLE_GRANTS = {
    "student": _STUDENT,
    "faculty": _FACULTY,
    "hod": _HOD,
    "acadadmin": _ACADADMIN,
    "dept_admin": _DEPT_ADMIN,
    "clearance_authority": _CLEARANCE_AUTHORITY,
}
