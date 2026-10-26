"""URL routing for Employee Leave Management endpoints."""

from django.urls import path

from modules.elm.api import views as v

urlpatterns = [
    path("types", v.LeaveTypesView.as_view(), name="elm-types"),
    path("applications", v.ApplicationsView.as_view(), name="elm-applications"),
    path("applications/<int:pk>/events", v.ApplicationEventsView.as_view(), name="elm-events"),
    path("applications/<int:pk>/withdraw", v.WithdrawView.as_view(), name="elm-withdraw"),
    path("applications/<int:pk>/cancel", v.CancelView.as_view(), name="elm-cancel"),
    path(
        "applications/<int:pk>/substitute",
        v.ReplaceSubstituteView.as_view(),
        name="elm-substitute",
    ),
    path("applications/<int:pk>/extend", v.ExtensionView.as_view(), name="elm-extend"),
    path("applications/<int:pk>/resume", v.ResumptionView.as_view(), name="elm-resume"),
    path("approvals", v.ApprovalQueueView.as_view(), name="elm-approvals"),
    path("applications/<int:pk>/decide", v.DecisionView.as_view(), name="elm-decide"),
    path("balances", v.MyBalancesView.as_view(), name="elm-balances"),
    path("admin/profiles", v.ProfilesAdminView.as_view(), name="elm-admin-profiles"),
    path("admin/balances", v.BalancesAdminView.as_view(), name="elm-admin-balances"),
    path("admin/holidays", v.HolidaysAdminView.as_view(), name="elm-admin-holidays"),
    path("admin/rollover", v.RolloverView.as_view(), name="elm-admin-rollover"),
    path("admin/offline-leave", v.OfflineLeaveView.as_view(), name="elm-admin-offline-leave"),
]
