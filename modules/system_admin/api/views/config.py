"""System configuration views for System Admin module."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasPermission
from modules.system_admin.api.permissions import IsSuperAdminOperator
from modules.system_admin.api.serializers import (
    UpdateSystemConfigurationSerializer,
)
from modules.system_admin.services import (
    get_all_configurations,
    update_configuration,
)


class SystemConfigView(APIView):
    def get_permissions(self):
        if self.request.method in ("PATCH", "POST", "PUT"):
            return [IsSuperAdminOperator(), HasPermission("system_admin.config.update")()]
        return [IsSuperAdminOperator(), HasPermission("system_admin.config.view")()]

    def get(self, request):
        configs = get_all_configurations()
        return Response(configs)

    def patch(self, request):
        serializer = UpdateSystemConfigurationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cfg = update_configuration(
            key=serializer.validated_data["key"],
            value=serializer.validated_data["value"],
            description=serializer.validated_data.get("description", ""),
            actor_user_id=getattr(request.principal, "erp_user_id", 0),
            actor_username=getattr(request.principal, "username", "super_admin"),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response({"key": cfg.key, "value": cfg.value, "updated_at": cfg.updated_at})
