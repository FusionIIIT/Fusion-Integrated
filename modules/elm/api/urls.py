from django.urls import path
from modules.placement.api import views

urlpatterns = [
    path("applications", views.ApplicationListView.as_view(), name="placement-applications"),
    path("applications/create", views.ApplicationCreateView.as_view(), name="placement-application-create"),
    path("applications/<int:pk>", views.ApplicationDetailView.as_view(), name="placement-application-detail"),
    path("applications/<int:pk>/transition", views.ApplicationTransitionView.as_view(), name="placement-application-transition"),
]
