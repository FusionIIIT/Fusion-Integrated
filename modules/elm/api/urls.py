from django.urls import path
from .views import LeaveRequestListView, LeaveRequestDetailView

urlpatterns = [
    path('leave-requests/', LeaveRequestListView.as_view(), name='leave-request-list'),
    path('leave-requests/<int:pk>/', LeaveRequestDetailView.as_view(), name='leave-request-detail'),
]
