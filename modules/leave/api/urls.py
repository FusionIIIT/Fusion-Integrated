from django.urls import path

from modules.leave.api.views import LeaveApprovalView, MyLeaveRequestsView

urlpatterns = [
    path("requests", MyLeaveRequestsView.as_view(), name="leave-requests"),
    path("requests/<int:request_id>", MyLeaveRequestsView.as_view(),
         name="leave-request-cancel"),
    path("approvals", LeaveApprovalView.as_view(), name="leave-approvals"),
    path("approvals/<int:request_id>", LeaveApprovalView.as_view(), name="leave-approval"),
]
