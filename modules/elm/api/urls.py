from django.urls import path
from . import views

urlpatterns = [
    path("balances/", views.LeaveBalanceListView.as_view(), name="elm-balances"),
    path("applications/", views.LeaveApplicationListCreateView.as_view(), name="elm-applications"),
    path("applications/<int:pk>/", views.LeaveApplicationDetailView.as_view(), name="elm-application-detail"),
    path("applications/<int:pk>/withdraw/", views.LeaveWithdrawView.as_view(), name="elm-application-withdraw"),
    path("approvals/", views.ApprovalQueueListView.as_view(), name="elm-approvals"),
    path("approvals/<int:pk>/action/", views.ApprovalActionView.as_view(), name="elm-approval-action"),
    path("substitutes/", views.SubstituteQueueListView.as_view(), name="elm-substitutes"),
    path("substitutes/<int:pk>/action/", views.SubstituteActionView.as_view(), name="elm-substitute-action"),
    path("admin/applications/", views.LeaveAdminListView.as_view(), name="elm-admin-applications"),
]
