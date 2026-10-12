from django.urls import path

from modules.elm.api.views import LeaveBalanceView, LeaveRequestView

urlpatterns = [
    path("requests", LeaveRequestView.as_view(), name="leave-requests"),
    path("balance", LeaveBalanceView.as_view(), name="leave-balance"),
]
