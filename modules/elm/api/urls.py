from django.urls import path
from .views import LeaveRequestListCreateView, LeaveRequestRetrieveUpdateDestroyView

urlpatterns = [
    path('leave-requests/', LeaveRequestListCreateView.as_view(), name='leave-request-list-create'),
    path('leave-requests/<int:pk>/', LeaveRequestRetrieveUpdateDestroyView.as_view(), name='leave-request-retrieve-update-destroy'),
]
