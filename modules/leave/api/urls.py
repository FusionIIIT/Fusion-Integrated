from django.urls import path
from modules.leave.api import views

urlpatterns = [
    path("balances/", views.LeaveBalanceListView.as_view(), name="leave-balances"),
    path("applications/", views.LeaveApplicationListView.as_view(), name="leave-applications"),
    path("applications/<int:pk>/substitute-response/", views.SubstituteResponseView.as_view(), name="leave-substitute-response"),
    path("applications/<int:pk>/unit-head-review/", views.UnitHeadReviewView.as_view(), name="leave-unit-head-review"),
    path("applications/<int:pk>/sanction/", views.SanctionDecisionView.as_view(), name="leave-sanction"),
    path("applications/<int:pk>/withdraw/", views.WithdrawApplicationView.as_view(), name="leave-withdraw"),
]
