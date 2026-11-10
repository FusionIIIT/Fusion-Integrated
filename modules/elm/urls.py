from django.urls import path

from .views import LeaveCategoryListCreateView,
LeaveCategoryRetrieveUpdateDestroyView,
LeaveApplicationListCreateView,
LeaveApplicationRetrieveUpdateDestroyView



urlpatterns = [

    path('leave-categories/',
LeaveCategoryListCreateView.as_view(),
name='leave-category-list-create'),

    path('leave-categories/<int:pk>/',
LeaveCategoryRetrieveUpdateDestroyView.as_view(),
name='leave-category-retrieve-update-destroy'),

    path('leave-applications/',
LeaveApplicationListCreateView.as_view(),
name='leave-application-list-create'),

    path('leave-applications/<int:pk>/',
LeaveApplicationRetrieveUpdateDestroyView.as_view(),
name='leave-application-retrieve-update-destroy'),

]