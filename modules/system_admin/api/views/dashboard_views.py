"""System Admin dashboard view."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.system_admin.api.serializers import DashboardMetricsSerializer
from modules.system_admin.selectors.dashboard_selectors import (
    get_system_admin_dashboard_metrics,
)

MODULE = HasModuleGrant("system_admin")


class DashboardView(APIView):
    permission_classes = [MODULE, HasPermission("system_admin.user.view")]

    @extend_schema(responses={200: DashboardMetricsSerializer})
    def get(self, request):
        metrics = get_system_admin_dashboard_metrics()
        return Response(metrics)
