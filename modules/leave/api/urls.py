from django.urls import path

from modules.leave.api.views import LeaveRequestListCreateView, LeaveRequestWithdrawView

urlpatterns = [
    path("requests", LeaveRequestListCreateView.as_view(), name="leave-requests"),
    path("requests/<int:pk>/withdraw", LeaveRequestWithdrawView.as_view(),
         name="leave-request-withdraw"),
]
