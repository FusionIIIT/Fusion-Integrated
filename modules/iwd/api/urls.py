from django.urls import path

from modules.iwd.api import views

urlpatterns = [
    path("complaints", views.ComplaintListCreateView.as_view()),
    path("complaints/<int:pk>", views.ComplaintDetailView.as_view()),
    path("complaints/<int:pk>/<str:action>", views.ComplaintActionView.as_view()),
    path("complaints/<int:pk>/audit", views.AuditListView.as_view()),
]
