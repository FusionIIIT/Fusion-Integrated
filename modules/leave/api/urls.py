from django.urls import path

from modules.leave.api import views

urlpatterns = [
    path("mine", views.MyLeaveView.as_view(), name="leave-mine"),
    path("requests", views.RequestListView.as_view(), name="leave-requests"),
    path("requests/create", views.RequestCreateView.as_view(), name="leave-request-create"),
    path("requests/<int:pk>/review", views.RequestReviewView.as_view(),
         name="leave-request-review"),
    path("requests/<int:pk>/cancel", views.RequestCancelView.as_view(),
         name="leave-request-cancel"),
    path("configuration/types", views.LeaveTypeConfigurationView.as_view(),
         name="leave-type-configuration"),
    path("configuration/types/<int:pk>", views.LeaveTypeConfigurationDetailView.as_view(),
         name="leave-type-configuration-detail"),
    path("configuration/balances", views.LeaveBalanceConfigurationView.as_view(),
         name="leave-balance-configuration"),
    path("configuration/manager-assignments",
         views.LeaveManagerAssignmentConfigurationView.as_view(),
         name="leave-manager-assignment-configuration"),
    path("configuration/manager-assignments/<int:pk>",
         views.LeaveManagerAssignmentDeleteView.as_view(),
         name="leave-manager-assignment-delete"),
]
