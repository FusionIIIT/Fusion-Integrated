from django.urls import path
from .views import LeaveTypeListCreateView, LeaveTypeRetrieveUpdateDestroyView, LeaveRequestListCreateView, LeaveRequestRetrieveUpdateDestroyView

urlpatterns = [
    path('leave-types/', LeaveTypeListCreateView.as_view(), name='leave-type-list-create'),
    path('leave-types/<int:pk>/', LeaveTypeRetrieveUpdateDestroyView.as_view(), name='leave-type-retrieve-update-destroy'),
    path('leave-requests/', LeaveRequestListCreateView.as_view(), name='leave-request-list-create'),
    path('leave-requests/<int:pk>/', LeaveRequestRetrieveUpdateDestroyView.as_view(), name='leave-request-retrieve-update-destroy'),
]
