from django.urls import path

from modules.vms.api.monitor import views

urlpatterns = [
    path("monitor/dashboard", views.DashboardView.as_view(), name="vms-monitor-dashboard"),
    path("monitor/on-site", views.OnSiteView.as_view(), name="vms-monitor-on-site"),
    path("monitor/movements", views.MovementsView.as_view(), name="vms-monitor-movements"),
    path("monitor/out-of-bounds", views.OutOfBoundsView.as_view(),
         name="vms-monitor-out-of-bounds"),
]
