from django.urls import path

from modules.vms.api.host import views

urlpatterns = [
    path("host/requests", views.HostRequestListView.as_view(), name="vms-host-requests"),
    path("host/requests/bulk-decision", views.HostBulkDecisionView.as_view(),
         name="vms-host-bulk-decision"),
    path("host/requests/<int:pk>/decision", views.HostDecisionView.as_view(),
         name="vms-host-decision"),
    path("host/pre-authorizations", views.PreAuthorizationListCreateView.as_view(),
         name="vms-host-preauths"),
    path("host/pre-authorizations/<int:pk>/revoke",
         views.PreAuthorizationRevokeView.as_view(), name="vms-host-preauth-revoke"),
    path("admin-requests/<int:pk>/urgent-decision", views.UrgentDecisionView.as_view(),
         name="vms-urgent-decision"),
]
