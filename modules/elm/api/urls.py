from django.urls import path
from .views import LeaveListCreateAPIView, LeaveDetailAPIView

urlpatterns = [
    path('leaves/', LeaveListCreateAPIView.as_view(), name='leave-list-create'),
    path('leaves/<int:pk>/', LeaveDetailAPIView.as_view(), name='leave-detail'),
]