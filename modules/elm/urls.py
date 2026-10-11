from django.urls import path
from . import views

app_name = 'elm'

urlpatterns = [
    path('leave-requests/', views.LeaveRequestListView.as_view(), name='leave-request-list'),
    path('leave-requests/<int:pk>/', views.LeaveRequestDetailView.as_view(), name='leave-request-detail'),
]
