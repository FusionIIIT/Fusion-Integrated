"""System configuration parameters views."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.system_admin.api.serializers import SystemParametersSerializer
from modules.system_admin.domain.exceptions import DomainValidationError
from modules.system_admin.selectors.audit_selectors import get_system_parameters
from modules.system_admin.services.configuration_service import update_system_parameters

MODULE = HasModuleGrant("system_admin")


def _actor_id(request) -> int:
    principal = getattr(request, "principal", None)
    return getattr(principal, "user_id", 1) or 1


def _ip(request) -> str | None:
    return request.META.get("REMOTE_ADDR")


class ConfigView(APIView):
    permission_classes = [MODULE, HasPermission("system_admin.config.change")]

    @extend_schema(responses={200: SystemParametersSerializer})
    def get(self, request):
        params = get_system_parameters()
        return Response({"parameters": params})

    @extend_schema(request=SystemParametersSerializer, responses={200: SystemParametersSerializer})
    def patch(self, request):
        serializer = SystemParametersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw_params = serializer.validated_data["parameters"]

        try:
            updated = update_system_parameters(
                params=raw_params,
                actor_id=_actor_id(request),
                ip_address=_ip(request),
            )
        except DomainValidationError as e:
            raise BadRequestError(str(e)) from e

        return Response({"parameters": updated})
