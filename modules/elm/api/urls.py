from django.urls import path
from modules.elm.api import views

urlpatterns = [
    path("requests", views.MyLeaveRequestsView.as_view(), name="elm-requests"),
    path("requests/<int:pk>", views.LeaveRequestDetailView.as_view(), name="elm-request-detail"),
    path("tasks", views.MyTasksView.as_view(), name="elm-tasks"),
    path("tasks/<int:pk>/decision", views.TaskDecisionView.as_view(), name="elm-task-decision"),
    path("balance", views.MyBalanceView.as_view(), name="elm-balance"),
    path("policies", views.PolicyListView.as_view(), name="elm-policies"),
    path("calendar", views.CalendarView.as_view(), name="elm-calendar"),
    path("resumption", views.ResumptionView.as_view(), name="elm-resumption"),
]
