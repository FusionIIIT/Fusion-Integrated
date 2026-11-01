"""URL routing for Employee Leave Management endpoints."""

from django.urls import path

from modules.elm.api import views as v

urlpatterns = [
    path("types", v.LeaveTypesView.as_view(), name="elm-types"),
    path("applications", v.ApplicationsView.as_view(), name="elm-applications"),
    path("applications/<int:pk>/events", v.ApplicationEventsView.as_view(), name="elm-events"),
    path("applications/<int:pk>/printable", v.PrintableView.as_view(), name="elm-printable"),
    path("applications/<int:pk>/withdraw", v.WithdrawView.as_view(), name="elm-withdraw"),
    path("applications/<int:pk>/cancel", v.CancelView.as_view(), name="elm-cancel"),
    path(
        "applications/<int:pk>/replace-substitute",
        v.ReplaceSubstituteView.as_view(),
        name="elm-replace-substitute",
    ),
    path("applications/<int:pk>/extend", v.ExtendView.as_view(), name="elm-extend"),
    path("applications/<int:pk>/resume", v.ResumeView.as_view(), name="elm-resume"),
    path(
        "applications/<int:pk>/review-resumption",
        v.ReviewResumptionView.as_view(),
        name="elm-review-resumption",
    ),
    path("approvals", v.ApprovalQueueView.as_view(), name="elm-approvals"),
    path("applications/<int:pk>/decide", v.DecisionView.as_view(), name="elm-decide"),
    path("balances", v.MyBalancesView.as_view(), name="elm-balances"),
    path("transactions", v.MyTransactionsView.as_view(), name="elm-transactions"),
    path("notifications", v.NotificationsView.as_view(), name="elm-notifications"),
    path("admin/profiles", v.ProfilesAdminView.as_view(), name="elm-admin-profiles"),
    path("admin/balances", v.BalancesAdminView.as_view(), name="elm-admin-balances"),
    path("admin/holidays", v.HolidaysAdminView.as_view(), name="elm-admin-holidays"),
    path("admin/offline-leave", v.OfflineLeaveAdminView.as_view(), name="elm-admin-offline-leave"),
    path("admin/year-end", v.YearEndAdminView.as_view(), name="elm-admin-year-end"),
    path("admin/sla-config", v.SlaAdminView.as_view(), name="elm-admin-sla-config"),
    path("admin/sla-process", v.SlaProcessAdminView.as_view(), name="elm-admin-sla-process"),
]
