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
]
