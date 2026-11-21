"""URL configuration for modules.system_admin API.

Exposes REST ViewSets and APIViews under strict authorization.
Traceability: CFR-SA-001..023, UCs (All).
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from modules.system_admin.api import views

app_name = "system_admin"

router = DefaultRouter(trailing_slash=True)
router.register(r"users", views.UserViewSet, basename="user")
router.register(r"roles", views.RoleManagementViewSet, basename="role")
router.register(r"archival", views.ArchivalViewSet, basename="archival")
router.register(r"purge", views.PurgeRequestViewSet, basename="purge")
router.register(r"audit", views.AuditLogViewSet, basename="audit")

urlpatterns = [
    path("", include(router.urls)),
    path("roles/switch/", views.ActiveRoleSwitchView.as_view(), name="role-switch"),
    path("dashboard/metrics/", views.DashboardView.as_view(), name="dashboard-metrics"),
    path("config/parameters/", views.SystemConfigView.as_view(), name="config-parameters"),
    path("config/parameters/<str:key>/", views.SystemConfigView.as_view(), name="config-parameter-detail"),
]
