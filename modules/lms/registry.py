MODULE = {
    "code": "lms",
    "label": "Course Management",
    "icon": "BookOpen",
    "base_path": "/lms",
    "nav_section": "Learning",
    "sort_order": 20,
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
    }
]
PERMISSIONS = [
    ("lms.course.view", "View authorized course workspaces"),
    ("lms.course.manage", "Maintain assigned course details"),
    ("lms.material.manage", "Maintain assigned course materials"),
    ("lms.announcement.create", "Post authorized course announcements"),
    ("lms.assignment.manage", "Create, edit and publish assigned course assignments"),
    ("lms.submission.create", "Submit own work for a registered course"),
    ("lms.submission.review", "Grade submissions for assigned courses"),
    ("lms.grade.publish", "Release grades for assigned courses"),
]
_STUDENT = ["lms.course.view", "lms.submission.create"]
_FACULTY = [code for code, label in PERMISSIONS if code != "lms.submission.create"]
_TA = ["lms.course.view", "lms.announcement.create", "lms.submission.review"]
ROLE_GRANTS = {
    "student": _STUDENT,
    "Student": _STUDENT,
    "faculty": _FACULTY,
    "Course Faculty": _FACULTY,
    "Teaching Assistant": _TA,
    "TA": _TA,
    "Observer": ["lms.course.view"],
}
