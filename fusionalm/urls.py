from django.urls import path
from . import views

urlpatterns = [
    path('leave/', views.leave_list, name='leave_list'),
    path('leave/request/', views.leave_request_list, name='leave_request_list'),
    path('leave/create/', views.create_leave, name='create_leave'),
    path('leave/request/create/', views.create_leave_request, name='create_leave_request'),
]
