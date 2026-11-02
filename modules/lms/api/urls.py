"""URL patterns for LMS (Course Management) API."""
from django.urls import path

from .views import (
    AssignmentListCreateView,
    AssignmentPublishView,
    CourseAnnouncementListCreateView,
    CourseDetailView,
    CourseMaterialListCreateView,
    GradeAuditLogView,
    GradeSubmissionView,
    ModifyReleasedGradeView,
    ReleaseGradesView,
    StudentSubmissionView,
    UserCourseListView,
)

app_name = "lms"

urlpatterns = [
    # Courses
    path("courses/", UserCourseListView.as_view(), name="user-courses"),
    path("courses/<int:course_id>/", CourseDetailView.as_view(), name="course-detail"),
    # Materials
    path("courses/<int:course_id>/materials/", CourseMaterialListCreateView.as_view(), name="course-materials"),
    # Announcements
    path("courses/<int:course_id>/announcements/", CourseAnnouncementListCreateView.as_view(), name="course-announcements"),
    # Assignments
    path("courses/<int:course_id>/assignments/", AssignmentListCreateView.as_view(), name="course-assignments"),
    path("assignments/<int:assignment_id>/publish/", AssignmentPublishView.as_view(), name="assignment-publish"),
    # Submissions
    path("assignments/<int:assignment_id>/submissions/", StudentSubmissionView.as_view(), name="assignment-submissions"),
    # Grading
    path("submissions/<int:submission_id>/grade/", GradeSubmissionView.as_view(), name="submission-grade"),
    path("assignments/<int:assignment_id>/release-grades/", ReleaseGradesView.as_view(), name="assignment-release-grades"),
    path("grades/<int:grade_id>/modify/", ModifyReleasedGradeView.as_view(), name="grade-modify"),
    path("grades/<int:grade_id>/audit/", GradeAuditLogView.as_view(), name="grade-audit"),
]
