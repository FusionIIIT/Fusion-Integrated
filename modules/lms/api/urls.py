"""LMS Course Workspace URL routes."""
from django.urls import path

from modules.lms.api.views import CourseListView, CourseWorkspaceDetailView

urlpatterns = [
    path("courses", CourseListView.as_view(), name="course-list"),
    path("courses/<str:code>", CourseWorkspaceDetailView.as_view(), name="course-workspace-detail"),
]
