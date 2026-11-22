from django.urls import path

from modules.vms.api.zones import views

urlpatterns = [
    path("zones/access-check", views.AccessCheckView.as_view(), name="vms-zone-access-check"),
    path("zones/elevations", views.ElevationListCreateView.as_view(),
         name="vms-zone-elevations"),
    path("zones/elevations/<int:pk>/revoke", views.ElevationRevokeView.as_view(),
         name="vms-zone-elevation-revoke"),
]
