from django.urls import path

from modules.vms.api.host import views

urlpatterns = [
    path("host/pending", views.HostPendingListView.as_view(), name="vms-host-pending"),
    path("host/requests/<int:pk>/decision", views.HostDecisionView.as_view(),
         name="vms-host-decision"),
]
