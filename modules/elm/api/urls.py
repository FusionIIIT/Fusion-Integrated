"""URL routes for ELM's supported API surface."""

from django.urls import path

from modules.elm.api import views

urlpatterns = [
    path("categories", views.LeaveCategoryListView.as_view(), name="elm-categories"),
    path("applications", views.LeaveApplicationListView.as_view(), name="elm-applications"),
    path(
        "applications/<int:pk>",
        views.LeaveApplicationDetailView.as_view(),
        name="elm-application-detail",
    ),
    path(
        "applications/<int:pk>/transition",
        views.LeaveApplicationTransitionView.as_view(),
        name="elm-application-transition",
    ),
    path(
        "applications/<int:pk>/withdraw",
        views.LeaveApplicationWithdrawView.as_view(),
        name="elm-application-withdraw",
    ),
    path(
        "applications/<int:pk>/history",
        views.LeaveApplicationHistoryView.as_view(),
        name="elm-application-history",
    ),
    path("balance", views.EmployeeLeaveBalanceListView.as_view(), name="elm-balance"),
    path("history", views.LeaveHistoryListView.as_view(), name="elm-history"),
]
