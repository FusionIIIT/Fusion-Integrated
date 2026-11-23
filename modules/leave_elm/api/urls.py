from django.urls import path

from modules.leave_elm.api import views

app_name = "leave_elm"

urlpatterns = [
    path("balances/", views.LeaveBalanceListView.as_view(), name="balance-list"),
    path(
        "applications/",
        views.LeaveApplicationListCreateView.as_view(),
        name="application-list-create",
    ),
    path(
        "applications/<int:pk>/",
        views.LeaveApplicationDetailView.as_view(),
        name="application-detail",
    ),
    path(
        "applications/<int:pk>/withdraw/",
        views.LeaveWithdrawView.as_view(),
        name="application-withdraw",
    ),
    path(
        "applications/<int:pk>/substitute-respond/",
        views.SubstituteRespondView.as_view(),
        name="substitute-respond",
    ),
    path(
        "applications/<int:pk>/review/",
        views.LeaveReviewActionView.as_view(),
        name="application-review",
    ),
]
