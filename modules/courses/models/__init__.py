"""Courses models package."""
from .announcements import CourseAnnouncement
from .assignments import CourseAssignment
from .grades import CourseGrade, CourseGradeAudit
from .materials import CourseMaterial, CourseMaterialSection
from .submissions import CourseSubmission
from .workspace import CourseMembership, CourseWorkspace

__all__ = [
    "CourseAnnouncement",
    "CourseAssignment",
    "CourseGrade",
    "CourseGradeAudit",
    "CourseMaterial",
    "CourseMaterialSection",
    "CourseMembership",
    "CourseSubmission",
    "CourseWorkspace",
]
