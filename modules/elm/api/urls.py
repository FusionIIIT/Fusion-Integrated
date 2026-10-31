from django.urls import path
from modules.elm.api.views import MyLeaveView, ApplyLeaveView, LeaveActionView, LeaveAccountsView, PendingApprovalsView, SubstituteRequestsView, LeavePolicyView
urlpatterns = [
 path("mine", MyLeaveView.as_view(), name="elm-my-leave"),
 path("apply", ApplyLeaveView.as_view(), name="elm-apply"),
 path("requests/<int:pk>/action", LeaveActionView.as_view(), name="elm-request-action"),
 path("accounts", LeaveAccountsView.as_view(), name="elm-accounts"),
 path("approvals", PendingApprovalsView.as_view(), name="elm-approvals"),
 path("substitute-requests", SubstituteRequestsView.as_view(), name="elm-substitute-requests"),
 path("policies", LeavePolicyView.as_view(), name="elm-policies"),
]
