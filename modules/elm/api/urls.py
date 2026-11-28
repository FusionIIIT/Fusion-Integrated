from django.urls import path
from modules.elm.api.views import LeaveTypeListView, MyApplicationsView, PendingApprovalsView, DecideView, WithdrawView, CancelView, MyBalanceView

urlpatterns = [
    path("types", LeaveTypeListView.as_view(), name="elm-types"),
    path("applications", MyApplicationsView.as_view(), name="elm-applications"),
    path("applications/pending", PendingApprovalsView.as_view(), name="elm-applications-pending"),
    path("applications/<int:pk>/decide", DecideView.as_view(), name="elm-applications-decide"),
    path("applications/<int:pk>/withdraw", WithdrawView.as_view(), name="elm-applications-withdraw"),
    path("applications/<int:pk>/cancel", CancelView.as_view(), name="elm-applications-cancel"),
    path("balance", MyBalanceView.as_view(), name="elm-balance"),
]
