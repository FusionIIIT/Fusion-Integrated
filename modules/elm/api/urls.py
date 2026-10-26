from django.urls import path

from . import views

app_name = "elm"

urlpatterns = [
    path(
        "applications/",
        views.LeaveApplicationListView.as_view(),
        name="applications",
    ),
    path(
        "balances/",
        views.LeaveBalanceListView.as_view(),
        name="balances",
    ),
    path(
        "submit/",
        views.LeaveApplicationCreateView.as_view(),
        name="submit",
    ),
    path(
        "applications/<int:application_id>/withdraw/",
        views.LeaveApplicationWithdrawView.as_view(),
        name="withdraw",
    ),
    path(
        "applications/<int:application_id>/substitute-response/",
        views.LeaveSubstituteResponseView.as_view(),
        name="substitute-response",
    ),
]
