"""URLs for ELM module."""
from django.urls import path

from modules.elm.api.views import (
    ApplicationDetailView,
    CancellationDecideView,
    CancellationRequestView,
    DirectorSelfSanctionView,
    EstablishmentRouteView,
    ExtensionRequestView,
    HolidayCalendarView,
    LeaveTypeListView,
    MyApplicationsView,
    MyBalanceView,
    OfflineSanctionView,
    PendingApprovalsView,
    ResumptionReviewView,
    ResumptionSubmitView,
    SanctionDecideView,
    SubstituteReplaceView,
    SubstituteRespondView,
    SubstituteTasksView,
    UnitHeadReviewView,
    WithdrawView,
    YearEndProcessingView,
)

urlpatterns = [
    # Types & Balances
    path("types", LeaveTypeListView.as_view(), name="elm-types"),
    path("balance", MyBalanceView.as_view(), name="elm-balance"),
    path("calendar", HolidayCalendarView.as_view(), name="elm-calendar"),

    # Applications
    path("applications", MyApplicationsView.as_view(), name="elm-applications"),
    path("applications/<int:pk>", ApplicationDetailView.as_view(), name="elm-application-detail"),
    path("applications/<int:pk>/withdraw", WithdrawView.as_view(), name="elm-applications-withdraw"),

    # Substitute workflow
    path("substitute/tasks", SubstituteTasksView.as_view(), name="elm-substitute-tasks"),
    path("applications/<int:pk>/substitute-respond", SubstituteRespondView.as_view(), name="elm-substitute-respond"),
    path("applications/<int:pk>/replace-substitute", SubstituteReplaceView.as_view(), name="elm-substitute-replace"),

    # Approval workflows
    path("approvals/pending", PendingApprovalsView.as_view(), name="elm-approvals-pending"),
    path("applications/<int:pk>/unit-head-review", UnitHeadReviewView.as_view(), name="elm-unit-head-review"),
    path("applications/<int:pk>/establishment-route", EstablishmentRouteView.as_view(), name="elm-establishment-route"),
    path("applications/<int:pk>/sanction-decide", SanctionDecideView.as_view(), name="elm-sanction-decide"),
    path("applications/<int:pk>/director-self-sanction", DirectorSelfSanctionView.as_view(), name="elm-director-self-sanction"),

    # Post-approval lifecycle: Cancellation, Extension, Resumption
    path("applications/<int:pk>/cancel-request", CancellationRequestView.as_view(), name="elm-cancellation-request"),
    path("cancellations/<int:pk>/decide", CancellationDecideView.as_view(), name="elm-cancellation-decide"),
    path("applications/<int:pk>/extend-request", ExtensionRequestView.as_view(), name="elm-extension-request"),
    path("applications/<int:pk>/resume-submit", ResumptionSubmitView.as_view(), name="elm-resumption-submit"),
    path("resumptions/<int:pk>/review", ResumptionReviewView.as_view(), name="elm-resumption-review"),

    # Admin operations
    path("admin/offline-leave", OfflineSanctionView.as_view(), name="elm-admin-offline-leave"),
    path("admin/year-end", YearEndProcessingView.as_view(), name="elm-admin-year-end"),
]
