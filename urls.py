from django.urls import path
from .views import create_leave_application, update_leave_application, get_leave_application

urlpatterns = [
    path('leave-application/', create_leave_application, name='create_leave_application'),
    path('leave-application/<int:application_id>/', update_leave_application, name='update_leave_application'),
    path('leave-application/<int:application_id>/', get_leave_application, name='get_leave_application'),
]
