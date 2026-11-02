from fusion_auth.permissions import HasModuleGrant, HasPermission

MODULE = HasModuleGrant("lms")
P_COURSE = "lms.course.view"
P_COURSE_MANAGE = "lms.course.manage"
P_MATERIAL = "lms.material.view"
P_MATERIAL_MANAGE = "lms.material.manage"
P_ANNOUNCEMENT = "lms.announcement.view"
P_ANNOUNCEMENT_CREATE = "lms.announcement.create"
P_ASSIGNMENT = "lms.assignment.view"
P_ASSIGNMENT_MANAGE = "lms.assignment.manage"
P_ASSIGNMENT_PUBLISH = "lms.assignment.publish"
P_SUBMIT = "lms.submission.create"
P_SUBMISSION_SELF = "lms.submission.view_self"
P_SUBMISSION = "lms.submission.view"
P_GRADE_SELF = "lms.grade.view_self"
P_GRADE_MANAGE = "lms.grade.manage"
P_GRADE_RELEASE = "lms.grade.release"


def allow(permission: str):
    return [MODULE, HasPermission(permission)]
