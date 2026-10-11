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
]
