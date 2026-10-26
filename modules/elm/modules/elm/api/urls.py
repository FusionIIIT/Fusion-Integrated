from django.urls import path
from . import views

urlpatterns = [
    path('apply/', views.LeaveApplicationCreateView.as_view(), name='leave-apply'),
    path('transitions/', views.LeaveTransitionView.as_view(), name='leave-transitions'),
    path('list/', views.LeaveApplicationListView.as_view(), name='leave-list'),
]