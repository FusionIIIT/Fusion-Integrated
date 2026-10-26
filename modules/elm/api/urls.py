from django.urls import path

from modules.elm.api import views as v

urlpatterns = [
    path("my-requests", v.MyLeaveRequestsView.as_view(), name="elm-my-requests"),
    path("approvals", v.ApprovalsQueueView.as_view(), name="elm-approvals"),
    path("requests/<int:pk>/decide", v.LeaveRequestDecideView.as_view(),
         name="elm-decide"),
    path("requests/<int:pk>/withdraw", v.LeaveRequestWithdrawView.as_view(),
         name="elm-withdraw"),
    path("requests/<int:pk>/cancel", v.LeaveRequestCancelView.as_view(),
         name="elm-cancel"),
    path("requests/<int:pk>/substitute-response",
         v.SubstituteResponseView.as_view(), name="elm-substitute-response"),
]
