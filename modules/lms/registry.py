"""Real IAM designations and permissions for the acting role only."""

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
    },
    {
        "code": "lms.teaching",
        "label": "Teaching",
        "icon": "PencilSimple",
        "to": "/lms/teaching",
        "required_permission": "lms.course.update",
        "sort_order": 20,
    },
    {
        "code": "lms.grading",
        "label": "Grading",
        "icon": "Exam",
        "to": "/lms/grading",
        "required_permission": "lms.grade.update",
        "sort_order": 30,
    },
]
PERMISSIONS = [
    (f"lms.{resource}.{action}", label)
    for resource, action, label in (
        ("course", "view", "Read linked course workspaces"),
        ("course", "update", "Configure assigned courses"),
        ("course_policy", "view", "Read course announcement policy"),
        ("course_policy", "update", "Append course policy versions"),
        ("section", "create", "Create material sections"),
        ("section", "update", "Organize material sections"),
        ("material", "view", "Read published materials"),
        ("material", "create", "Create course materials"),
        ("material", "update", "Edit course materials"),
        ("material", "publish", "Publish or schedule course materials"),
        ("assignment", "view", "Read available assignments"),
        ("assignment", "create", "Create assignments"),
        ("assignment", "update", "Edit assignments"),
        ("assignment", "publish", "Publish or schedule assignments"),
        ("announcement", "view", "Read course announcements"),
        ("announcement", "create", "Post course announcements"),
        ("submission", "view", "Read scoped submissions"),
        ("submission", "create", "Submit own assignment work"),
        ("grade", "view", "Read scoped grades and feedback"),
        ("grade", "create", "Record draft grades"),
        ("grade", "update", "Update scoped grades"),
        ("grade", "publish", "Release grades and feedback"),
        ("content", "publish", "System scheduled release"),
    )
]
SYSTEM_PERMISSIONS = ["lms.content.publish"]
_COMMON = ["lms.course.view", "lms.material.view", "lms.announcement.view"]
ROLE_GRANTS = {
    "student": [
        *_COMMON,
        "lms.assignment.view",
        "lms.submission.view",
        "lms.submission.create",
        "lms.grade.view",
    ],
    "faculty": [
        code
        for code, _ in PERMISSIONS
        if code not in (*SYSTEM_PERMISSIONS, "lms.submission.create")
    ],
    "lms_ta": [
        *_COMMON,
        "lms.assignment.view",
        "lms.announcement.create",
        "lms.submission.view",
        "lms.grade.view",
        "lms.grade.create",
        "lms.grade.update",
    ],
    "lms_observer": _COMMON,
}
SCOPE_PERMISSIONS = ("lms.course.view",)


def readiness():
    from modules.lms.services.setup import unmet_prerequisites

    return unmet_prerequisites()
