from django.urls import path

from modules.badms.api.views import ArchivalDecisionView, ArchivalRequestListCreateView

urlpatterns = [
    path("archival-requests", ArchivalRequestListCreateView.as_view(),
         name="badms-archival-requests"),
    path("archival-requests/<int:pk>/decision", ArchivalDecisionView.as_view(),
         name="badms-archival-decision"),
]
