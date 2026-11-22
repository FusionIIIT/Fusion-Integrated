"""URL routes for LMS API."""

from django.urls import path

from modules.lms.api.views import (
    AssignmentDetailView,
    AssignmentGradesListView,
    AssignmentListCreateView,
    AssignmentPublishView,
    AssignmentSubmissionDownloadView,
    CourseAnnouncementDetailView,
    CourseAnnouncementListCreateView,
    CourseMaterialDetailView,
    CourseMaterialDownloadView,
    CourseMaterialListCreateView,
    CourseWorkspaceDetailView,
    CourseWorkspaceListView,
    GradeAuditHistoryView,
    GradeSubmissionView,
    PublishGradesView,
    SubmissionDetailView,
    SubmissionGradeDetailView,
    SubmissionListCreateView,
)

urlpatterns = [
    # Workspaces
    path("courses/", CourseWorkspaceListView.as_view(), name="course-list"),
    path("courses/<int:course_id>/", CourseWorkspaceDetailView.as_view(), name="course-detail"),
    # Materials
    path("materials/", CourseMaterialListCreateView.as_view(), name="material-list"),
    path(
        "materials/<int:material_id>/",
        CourseMaterialDetailView.as_view(),
        name="material-detail",
    ),
    path(
        "materials/<int:material_id>/download/",
        CourseMaterialDownloadView.as_view(),
        name="material-download",
    ),
    # Announcements
    path(
        "announcements/",
        CourseAnnouncementListCreateView.as_view(),
        name="announcement-list",
    ),
    path(
        "announcements/<int:announcement_id>/",
        CourseAnnouncementDetailView.as_view(),
        name="announcement-detail",
    ),
    # Assignments
    path("assignments/", AssignmentListCreateView.as_view(), name="assignment-list"),
    path(
        "assignments/<int:assignment_id>/",
        AssignmentDetailView.as_view(),
        name="assignment-detail",
    ),
    path(
        "assignments/<int:assignment_id>/publish/",
        AssignmentPublishView.as_view(),
        name="assignment-publish",
    ),
    path(
        "assignments/<int:assignment_id>/submissions/",
        SubmissionListCreateView.as_view(),
        name="assignment-submissions",
    ),
    path(
        "assignments/<int:assignment_id>/publish-grades/",
        PublishGradesView.as_view(),
        name="assignment-publish-grades",
    ),
    path(
        "assignments/<int:assignment_id>/grades/",
        AssignmentGradesListView.as_view(),
        name="assignment-grades",
    ),
    # Submissions & Grading
    path(
        "submissions/<int:submission_id>/",
        SubmissionDetailView.as_view(),
        name="submission-detail",
    ),
    path(
        "submissions/<int:submission_id>/download/",
        AssignmentSubmissionDownloadView.as_view(),
        name="submission-download",
    ),
    path(
        "submissions/<int:submission_id>/grade/",
        GradeSubmissionView.as_view(),
        name="submission-grade",
    ),
    path(
        "submissions/<int:submission_id>/grade-detail/",
        SubmissionGradeDetailView.as_view(),
        name="submission-grade-detail",
    ),
    path(
        "submissions/<int:submission_id>/grade-audit/",
        GradeAuditHistoryView.as_view(),
        name="submission-grade-audit",
    ),
]
