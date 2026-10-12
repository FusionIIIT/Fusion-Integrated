from django.urls import path

from modules.elm.api.views import (
    LeaveApplicationDetailView,
    LeaveApplicationListCreateView,
    LeaveCategoryListView,
)

app_name = "elm"

urlpatterns = [
    path(
        "categories/",
        LeaveCategoryListView.as_view(),
        name="leave-category-list",
    ),
    path(
        "applications/",
        LeaveApplicationListCreateView.as_view(),
        name="leave-application-list-create",
    ),
    path(
        "applications/<int:pk>/",
        LeaveApplicationDetailView.as_view(),
        name="leave-application-detail",
    ),
]