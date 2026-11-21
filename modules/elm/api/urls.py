"""API routes owned by ELM."""

from django.urls import path

from modules.elm.api import views

urlpatterns = [
    path("balances", views.MyLeaveBalancesView.as_view(), name="elm-my-balances"),
    path(
        "applications",
        views.MyLeaveApplicationsView.as_view(),
        name="elm-my-applications",
    ),
    path(
        "applications/<int:pk>/actions",
        views.LeaveApplicationActionView.as_view(),
        name="elm-application-actions",
    ),
]
