"""What the server tells the shell about this module (ADR-0010)."""
MODULE = {
    "code": "lms", "label": "LMS (Course Management)", "icon": "BookOpen",
    "base_path": "/lms", "nav_section": "Academic", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "lms.course", "label": "Course Workspace",
     "icon": "BookOpen", "to": "/lms/courses/:id",
     "required_permission": "lms.course.view", "sort_order": 10},
    {"code": "lms.materials", "label": "Course Materials",
     "icon": "Files", "to": "/lms/courses/:id/materials",
     "required_permission": "lms.material.view", "sort_order": 20},
    {"code": "lms.announcements", "label": "Announcements",
     "icon": "Megaphone", "to": "/lms/courses/:id/announcements",
     "required_permission": "lms.announcement.view", "sort_order": 30},
    {"code": "lms.assignments", "label": "Assignments",
     "icon": "ClipboardText", "to": "/lms/courses/:id/assignments",
     "required_permission": "lms.assignment.view", "sort_order": 40},
    {"code": "lms.gradebook", "label": "Gradebook",
     "icon": "ChartBar", "to": "/lms/courses/:id/gradebook",
     "required_permission": "lms.grade.view", "sort_order": 50},
]

PERMISSIONS = [
    ("lms.course.view", "View course workspace"),
    ("lms.course.manage", "Manage course details"),
    ("lms.material.view", "View published materials"),
    ("lms.material.manage", "Create and schedule materials"),
    ("lms.announcement.view", "View announcements"),
    ("lms.announcement.create", "Post announcements"),
    ("lms.assignment.view", "View published assignments"),
    ("lms.assignment.manage", "Create and publish assignments"),
    ("lms.submission.create", "Submit assignment work"),
    ("lms.submission.view_own", "View own submission history"),
    ("lms.submission.view", "View submissions"),
    ("lms.grade.create", "Grade submissions"),
    ("lms.grade.release", "Release grades and feedback"),
    ("lms.grade.view", "View released grades"),
]

SYSTEM_PERMISSIONS = [
    "lms.scheduled_release.run",
]

_STUDENT = [
    "lms.course.view",
    "lms.material.view",
    "lms.announcement.view",
    "lms.assignment.view",
    "lms.submission.create",
    "lms.submission.view_own",
    "lms.grade.view",
]

_FACULTY = [
    "lms.course.view", "lms.course.manage",
    "lms.material.view", "lms.material.manage",
    "lms.announcement.view", "lms.announcement.create",
    "lms.assignment.view", "lms.assignment.manage",
    "lms.submission.view",
    "lms.grade.create", "lms.grade.release", "lms.grade.view",
]

_TA = [
    "lms.course.view",
    "lms.material.view",
    "lms.announcement.view", "lms.announcement.create",
    "lms.assignment.view",
    "lms.submission.view",
    "lms.grade.create",
]

_OBSERVER = [
    "lms.course.view",
    "lms.material.view",
    "lms.announcement.view",
]

ROLE_GRANTS = {
    "student": _STUDENT,
    "Professor": _FACULTY,
    "Associate Professor": _FACULTY,
    "Assistant Professor": _FACULTY,
    "Teaching Assistant": _TA,
    "Observer": _OBSERVER,
}
