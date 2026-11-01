"""What the server tells the shell about this module (ADR-0010).

LMS (Course Management) Module.
"""

MODULE = {
    "code": "lms",
    "label": "LMS (Courses)",
    "icon": "GraduationCap",
    "base_path": "/lms",
    "nav_section": "Academics",
    "sort_order": 15,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "lms.courses",
        "label": "My Courses",
        "icon": "BookOpen",
        "to": "/lms/courses",
        "required_permission": "lms.course.view",
        "sort_order": 10,
    },
    {
        "code": "lms.assignments",
        "label": "Assignments",
        "icon": "ClipboardText",
        "to": "/lms/assignments",
        "required_permission": "lms.assignment.view",
        "sort_order": 20,
    },
    {
        "code": "lms.announcements",
        "label": "Announcements",
        "icon": "Megaphone",
        "to": "/lms/announcements",
        "required_permission": "lms.announcement.view",
        "sort_order": 30,
    },
    {
        "code": "lms.grades",
        "label": "Grades",
        "icon": "ChartBar",
        "to": "/lms/grades",
        "required_permission": "lms.grade.view",
        "sort_order": 40,
    },
]

PERMISSIONS = [
    ("lms.course.view", "View course workspace and details"),
    ("lms.course.manage", "Configure course details, syllabus, schedule, and settings"),
    ("lms.material.view", "View published course materials"),
    ("lms.material.manage", "Add, organize, edit, and schedule course materials"),
    ("lms.announcement.view", "View course announcements"),
    ("lms.announcement.post", "Post course announcements"),
    ("lms.assignment.view", "View published assignments"),
    ("lms.assignment.manage", "Create, edit, and publish assignments"),
    ("lms.submission.create", "Submit assignment work"),
    ("lms.submission.view_self", "View own submission history and status"),
    ("lms.submission.view_all", "View student submissions for course"),
    ("lms.grade.manage", "Grade student submissions"),
    ("lms.grade.release", "Release draft grades to students"),
    ("lms.grade.view", "Access grades view"),
    ("lms.grade.view_self", "View own released grades and feedback"),
    ("lms.grade.view_all", "View all student grades for course"),
    ("lms.audit.view", "View post-release grade change audit logs"),
]

_STUDENT = [
    "lms.course.view",
    "lms.material.view",
    "lms.announcement.view",
    "lms.assignment.view",
    "lms.submission.create",
    "lms.submission.view_self",
    "lms.grade.view",
    "lms.grade.view_self",
]

_TA = [
    "lms.course.view",
    "lms.material.view",
    "lms.announcement.view",
    "lms.announcement.post",
    "lms.assignment.view",
    "lms.submission.view_all",
    "lms.grade.view",
    "lms.grade.manage",
    "lms.grade.view_all",
]

_OBSERVER = [
    "lms.course.view",
    "lms.material.view",
    "lms.announcement.view",
]

_FACULTY = [
    "lms.course.view",
    "lms.course.manage",
    "lms.material.view",
    "lms.material.manage",
    "lms.announcement.view",
    "lms.announcement.post",
    "lms.assignment.view",
    "lms.assignment.manage",
    "lms.submission.view_all",
    "lms.grade.view",
    "lms.grade.manage",
    "lms.grade.release",
    "lms.grade.view_all",
    "lms.audit.view",
]

_ADMIN = _FACULTY + [
    "lms.submission.create",
    "lms.submission.view_self",
    "lms.grade.view_self",
]

ROLE_GRANTS = {
    "student": _STUDENT,
    "teaching_assistant": _TA,
    "ta": _TA,
    "observer": _OBSERVER,
    "faculty": _FACULTY,
    "professor": _FACULTY,
    "assistant_professor": _FACULTY,
    "associate_professor": _FACULTY,
    "instructor": _FACULTY,
    "admin": _ADMIN,
    "administrator": _ADMIN,
}
