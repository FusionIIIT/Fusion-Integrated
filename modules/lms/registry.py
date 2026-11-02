"""What the server tells the shell about the LMS (Course Management) module (ADR-0010)."""

MODULE = {
    "code": "lms",
    "label": "Course Management",
    "icon": "FaBookOpen",
    "base_path": "/lms",
    "nav_section": "Academics",
    "sort_order": 25,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "lms.courses",
        "label": "My Courses",
        "icon": "FaGraduationCap",
        "to": "/lms/courses",
        "required_permission": "lms.course.view",
        "sort_order": 10,
    },
    {
        "code": "lms.materials",
        "label": "Course Materials",
        "icon": "FaFolderOpen",
        "to": "/lms/materials",
        "required_permission": "lms.material.view",
        "sort_order": 20,
    },
    {
        "code": "lms.assignments",
        "label": "Assignments",
        "icon": "FaTasks",
        "to": "/lms/assignments",
        "required_permission": "lms.assignment.view",
        "sort_order": 30,
    },
    {
        "code": "lms.grading",
        "label": "Grading & Submissions",
        "icon": "FaCheckDouble",
        "to": "/lms/grading",
        "required_permission": "lms.grade.view",
        "sort_order": 40,
    },
]

PERMISSIONS = [
    ("lms.course.view", "View course home, syllabus, schedule, and details"),
    ("lms.course.manage", "Configure syllabus, schedule, and course settings"),
    ("lms.material.view", "View and download published course materials"),
    ("lms.material.upload", "Upload, schedule, and edit course study materials"),
    ("lms.announcement.post", "Post course-wide announcements"),
    ("lms.assignment.view", "View published assignments"),
    ("lms.assignment.create", "Create, edit, and publish course assignments"),
    ("lms.assignment.submit", "Submit assignment deliverables"),
    ("lms.grade.view", "View released grades and feedback"),
    ("lms.grade.evaluate", "Grade student submissions and enter points/feedback"),
    ("lms.grade.release", "Release draft grades to students"),
    ("lms.grade.audit", "View post-release grade modification logs"),
]

SYSTEM_PERMISSIONS: list[str] = []

_STUDENT = [
    "lms.course.view",
    "lms.material.view",
    "lms.assignment.view",
    "lms.assignment.submit",
    "lms.grade.view",
]

_TA = [
    "lms.course.view",
    "lms.material.view",
    "lms.announcement.post",
    "lms.assignment.view",
    "lms.grade.view",
    "lms.grade.evaluate",
]

_FACULTY = [
    "lms.course.view",
    "lms.course.manage",
    "lms.material.view",
    "lms.material.upload",
    "lms.announcement.post",
    "lms.assignment.view",
    "lms.assignment.create",
    "lms.grade.view",
    "lms.grade.evaluate",
    "lms.grade.release",
    "lms.grade.audit",
]

_OBSERVER = [
    "lms.course.view",
    "lms.material.view",
]

ROLE_GRANTS = {
    "student": _STUDENT,
    "ta": _TA,
    "faculty": _FACULTY,
    "observer": _OBSERVER,
    "admin": _FACULTY,
}
