from django.urls import path

from modules.elm.api.views import (
    AdminAllotBalanceView,
    AdminLeaveTypeView,
    CancelView,
    DecideView,
    LeaveTypeListView,
    MyApplicationsView,
    MyBalanceView,
    PendingApprovalsView,
    WithdrawView,
)

urlpatterns = [
    path("types", LeaveTypeListView.as_view(), name="elm-types"),
    path("applications", MyApplicationsView.as_view(), name="elm-applications"),
    path("applications/pending", PendingApprovalsView.as_view(), name="elm-applications-pending"),
    path("applications/<int:pk>/decide", DecideView.as_view(), name="elm-applications-decide"),
    path(
        "applications/<int:pk>/withdraw", WithdrawView.as_view(), name="elm-applications-withdraw"
    ),
    path("applications/<int:pk>/cancel", CancelView.as_view(), name="elm-applications-cancel"),
    path("balance", MyBalanceView.as_view(), name="elm-balance"),
    path("admin/types", AdminLeaveTypeView.as_view(), name="elm-admin-types"),
    path("admin/balances", AdminAllotBalanceView.as_view(), name="elm-admin-balances"),
]
