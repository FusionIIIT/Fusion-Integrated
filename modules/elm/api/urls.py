from django.urls import path

from . import views
from .configuration import CalendarView, EmployeeConfigView, PolicyView

urlpatterns = [
    path("leaves/", views.LeaveListCreateView.as_view()),
    path("balances/", views.LeaveBalanceView.as_view()),
    path("substitute-queue/", views.SubstituteQueueView.as_view()),
    path("substitute-queue/<uuid:pk>/decision/", views.SubstituteDecisionView.as_view()),
    path("approvals/", views.ApprovalsQueueView.as_view()),
    path("approvals/<uuid:pk>/decision/", views.ApproverDecisionView.as_view()),
    path("leaves/<uuid:pk>/withdraw/", views.LeaveWithdrawView.as_view()),
    path("leaves/<uuid:pk>/replace-substitute/", views.ReplacementView.as_view()),
    path("leaves/<uuid:pk>/export/", views.ExportView.as_view()),
    path("leaves/<uuid:pk>/maintenance/", views.MaintenanceView.as_view()),
    path("leaves/<uuid:pk>/<str:kind>/", views.FollowupView.as_view()),
    path("notifications/", views.NotificationsView.as_view()),
    path("ledger/", views.LedgerView.as_view()),
    path("offline/", views.OfflineView.as_view()),
    path("admin/employees/", EmployeeConfigView.as_view()),
    path("admin/policy/", PolicyView.as_view()),
    path("admin/calendars/", CalendarView.as_view()),
]
