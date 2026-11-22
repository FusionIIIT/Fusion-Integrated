from django.urls import path

from modules.vms.api.extensions import views

urlpatterns = [
    path("extensions", views.ExtensionListCreateView.as_view(), name="vms-extensions"),
    path("extensions/<int:pk>", views.ExtensionDetailView.as_view(), name="vms-extension"),
    path("extensions/<int:pk>/decision", views.ExtensionDecisionView.as_view(),
         name="vms-extension-decision"),
]
