from django.urls import path
from modules.elm.api.views import (
    LeaveCatalogView,
    MyLeaveBalancesView,
    MyLeaveRequestsView,
    LeaveRequestDetailView,
    WithdrawLeaveView,
    CancelLeaveView,
    SubstituteTasksView,
    RespondSubstituteView,
    ReviewTasksView,
    ReviewDecisionView,
    ExtendLeaveView,
    PrintableLeaveView,
    YearEndProcessingView,
    SubmitResumptionView,
    ReviewResumptionView,
    RecordOfflineLeaveView,
)

urlpatterns = [
    path("catalog", LeaveCatalogView.as_view(), name="elm-catalog"),
    path("balances", MyLeaveBalancesView.as_view(), name="elm-my-balances"),
    path("requests", MyLeaveRequestsView.as_view(), name="elm-my-requests"),
    path("requests/<int:pk>", LeaveRequestDetailView.as_view(), name="elm-request-detail"),
    path("requests/<int:pk>/withdraw", WithdrawLeaveView.as_view(), name="elm-request-withdraw"),
    path("requests/<int:pk>/cancel", CancelLeaveView.as_view(), name="elm-request-cancel"),
    path("tasks/substitute", SubstituteTasksView.as_view(), name="elm-substitute-tasks"),
    path("tasks/substitute/<int:pk>/respond", RespondSubstituteView.as_view(), name="elm-substitute-respond"),
    path("tasks/review", ReviewTasksView.as_view(), name="elm-review-tasks"),
    path("tasks/review/<int:pk>/decision", ReviewDecisionView.as_view(), name="elm-review-decision"),
    path("requests/<int:pk>/extend", ExtendLeaveView.as_view(), name="elm-request-extend"),
    path("requests/<int:pk>/print", PrintableLeaveView.as_view(), name="elm-request-print"),
    path("requests/<int:pk>/resumption", SubmitResumptionView.as_view(), name="elm-request-resumption"),
    path("tasks/resumption/<int:pk>/review", ReviewResumptionView.as_view(), name="elm-resumption-review"),
    path("processing/year-end", YearEndProcessingView.as_view(), name="elm-year-end-processing"),
    path("admin/offline-record", RecordOfflineLeaveView.as_view(), name="elm-offline-record"),
]


