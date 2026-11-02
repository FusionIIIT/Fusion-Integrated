from django.urls import path
from .views import dashboard_view, allocate_room_view, leave_request_view

urlpatterns = [
    path('', dashboard_view, name='hostel_dashboard'),
    path('allocate/', allocate_room_view, name='allocate_room'),
    path('leave/', leave_request_view, name='leave_request'),
]
