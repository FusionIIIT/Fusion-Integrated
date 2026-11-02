"""LMS API permission classes using fusion_auth gates."""
from fusion_auth.permissions import HasModuleGrant, HasPermission

RequireLmsModule = HasModuleGrant("lms")
RequireCourseView = HasPermission("lms.course.view")
RequireCourseManage = HasPermission("lms.course.manage")
RequireMaterialView = HasPermission("lms.material.view")
RequireMaterialUpload = HasPermission("lms.material.upload")
RequireAnnouncementPost = HasPermission("lms.announcement.post")
RequireAssignmentView = HasPermission("lms.assignment.view")
RequireAssignmentCreate = HasPermission("lms.assignment.create")
RequireAssignmentSubmit = HasPermission("lms.assignment.submit")
RequireGradeView = HasPermission("lms.grade.view")
RequireGradeEvaluate = HasPermission("lms.grade.evaluate")
RequireGradeRelease = HasPermission("lms.grade.release")
RequireGradeAudit = HasPermission("lms.grade.audit")
