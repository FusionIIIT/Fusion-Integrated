from django.urls import path

from modules.elm.api.views import (
    LeaveTypeListView,
    LeaveBalanceListView,
    LeaveApplicationListView,
    LeaveApplicationCreateView,
    LeaveApplicationWithdrawView,
)

urlpatterns = [
    path("leave-types", LeaveTypeListView.as_view(), name="elm-leave-types"),
    path("balances", LeaveBalanceListView.as_view(), name="elm-balances"),
    path("applications", LeaveApplicationListView.as_view(), name="elm-applications"),
    path("applications/<int:pk>/withdraw", LeaveApplicationWithdrawView.as_view(), name="elm-application-withdraw"),
    path("applications/create", LeaveApplicationCreateView.as_view(), name="elm-application-create"),
]
