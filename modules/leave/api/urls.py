from django.urls import path

from modules.leave.api import views

app_name = "leave"

urlpatterns = [
    path("applications/", views.ApplicationListCreateView.as_view(), name="applications"),
    path(
        "applications/<int:pk>/", views.ApplicationDetailView.as_view(), name="application-detail"
    ),
    path(
        "applications/<int:pk>/withdraw/", views.WithdrawView.as_view(), name="withdraw-application"
    ),
    path("applications/<int:pk>/cancel/", views.CancelView.as_view(), name="cancel-approved-leave"),
    path(
        "applications/<int:pk>/substitute-response/",
        views.SubstituteResponseView.as_view(),
        name="respond-to-substitute",
    ),
    path(
        "applications/<int:pk>/replace-substitute/",
        views.ReplaceSubstituteView.as_view(),
        name="replace-substitute",
    ),
    path("applications/<int:pk>/decide/", views.DecideView.as_view(), name="decide-application"),
    path("inbox/", views.InboxView.as_view(), name="inbox"),
    path("balances/", views.BalanceView.as_view(), name="balances"),
    path(
        "reporting-lines/<int:user_id>/", views.ReportingLineView.as_view(), name="reporting-line"
    ),
]
