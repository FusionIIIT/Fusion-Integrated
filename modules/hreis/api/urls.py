from django.urls import path

from modules.hreis.api import views

urlpatterns = [
    path("requests", views.RequestListCreateView.as_view(), name="hreis-requests"),
    path("requests/<int:pk>", views.RequestDetailView.as_view(), name="hreis-request"),
    path(
        "requests/<int:pk>/transition",
        views.RequestTransitionView.as_view(),
        name="hreis-request-transition",
    ),
    path("employees", views.EmployeeRecordsView.as_view(), name="hreis-employees"),
    path(
        "employees/<int:user_id>", views.EmployeeRecordDetailView.as_view(), name="hreis-employee"
    ),
    path("policies", views.PolicyListCreateView.as_view(), name="hreis-policies"),
    path("leave-balances", views.LeaveBalanceView.as_view(), name="hreis-leave-balances"),
    path("notifications", views.NotificationListView.as_view(), name="hreis-notifications"),
    path("audit-events", views.AuditListView.as_view(), name="hreis-audit-events"),
]
