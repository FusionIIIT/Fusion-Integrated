"""URL routing for the Course Management API."""
from django.urls import path

from modules.courses.api import views

app_name = "courses"

urlpatterns = [
    path("workspaces", views.WorkspacesListView.as_view(), name="workspaces-list"),
    path(
        "workspaces/<int:pk>",
        views.WorkspaceDetailView.as_view(),
        name="workspace-detail",
    ),
    path(
        "workspaces/<int:workspace_id>/sections",
        views.CourseSectionsView.as_view(),
        name="workspace-sections",
    ),
    path(
        "workspaces/<int:workspace_id>/sections/<int:pk>",
        views.CourseSectionDetailView.as_view(),
        name="workspace-section-detail",
    ),
    path(
        "workspaces/<int:workspace_id>/materials",
        views.CourseMaterialsView.as_view(),
        name="workspace-materials",
    ),
    path(
        "workspaces/<int:workspace_id>/materials/<int:pk>",
        views.CourseMaterialDetailView.as_view(),
        name="workspace-material-detail",
    ),
    path(
        "workspaces/<int:workspace_id>/materials/<int:pk>/download",
        views.CourseMaterialDownloadView.as_view(),
        name="workspace-material-download",
    ),
    path(
        "workspaces/<int:workspace_id>/announcements",
        views.CourseAnnouncementsView.as_view(),
        name="workspace-announcements",
    ),
    path(
        "workspaces/<int:workspace_id>/announcements/<int:pk>",
        views.CourseAnnouncementDetailView.as_view(),
        name="workspace-announcement-detail",
    ),
    path(
        "workspaces/<int:workspace_id>/assignments",
        views.CourseAssignmentsView.as_view(),
        name="workspace-assignments",
    ),
    path(
        "workspaces/<int:workspace_id>/assignments/<int:pk>",
        views.CourseAssignmentDetailView.as_view(),
        name="workspace-assignment-detail",
    ),
]
