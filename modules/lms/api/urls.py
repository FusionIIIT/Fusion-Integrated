"""LMS Course Workspace URL routes."""
from django.urls import path

from modules.lms.api.views import (
    CourseListView,
    CourseMaterialDetailView,
    CourseMaterialDownloadView,
    CourseMaterialListView,
    CourseWorkspaceDetailView,
)

urlpatterns = [
    path("courses", CourseListView.as_view(), name="course-list"),
    path(
        "courses/<str:code>",
        CourseWorkspaceDetailView.as_view(),
        name="course-workspace-detail",
    ),
    path(
        "courses/<str:code>/materials",
        CourseMaterialListView.as_view(),
        name="course-material-list",
    ),
    path(
        "courses/<str:code>/materials/<int:material_id>",
        CourseMaterialDetailView.as_view(),
        name="course-material-detail",
    ),
    path(
        "courses/<str:code>/materials/<int:material_id>/download",
        CourseMaterialDownloadView.as_view(),
        name="course-material-download",
    ),
]
