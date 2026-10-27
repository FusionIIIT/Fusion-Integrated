"""Leave API URL routing."""
from django.urls import path

from modules.leave.api import views

app_name = "leave"

urlpatterns = [
    path("requests/", views.LeaveListView.as_view(), name="leave-list"),
    path("requests/<int:pk>/", views.LeaveDetailView.as_view(), name="leave-detail"),
    path("requests/apply/", views.LeaveApplyView.as_view(), name="leave-apply"),
    path(
        "requests/<int:pk>/transition/",
        views.LeaveTransitionView.as_view(),
        name="leave-transition",
    ),
    path(
        "requests/<int:pk>/substitute-action/",
        views.SubstituteActionView.as_view(),
        name="leave-substitute-action",
    ),
    path("balances/", views.LeaveBalanceListView.as_view(), name="leave-balances"),
]
