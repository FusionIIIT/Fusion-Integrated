from django.urls import path

from modules.elm.api.views import (
    CancelLeaveRequestAPIView,
    LeaveTypeListAPIView,
    MyLeaveBalanceAPIView,
    MyLeaveRequestListCreateAPIView,
    PendingApprovalsAPIView,
    ReviewLeaveRequestAPIView,
    WithdrawLeaveRequestAPIView,
)

urlpatterns = [
    path("types", LeaveTypeListAPIView.as_view(), name="elm-leave-types"),
    path("balances", MyLeaveBalanceAPIView.as_view(), name="elm-leave-balances"),
    path("applications", MyLeaveRequestListCreateAPIView.as_view(), name="elm-applications"),
    path("approvals", PendingApprovalsAPIView.as_view(), name="elm-pending-approvals"),
    path(
        "applications/<int:pk>/decide",
        ReviewLeaveRequestAPIView.as_view(),
        name="elm-application-decide",
    ),
    path(
        "applications/<int:pk>/withdraw",
        WithdrawLeaveRequestAPIView.as_view(),
        name="elm-application-withdraw",
    ),
    path(
        "applications/<int:pk>/cancel",
        CancelLeaveRequestAPIView.as_view(),
        name="elm-application-cancel",
    ),
]
