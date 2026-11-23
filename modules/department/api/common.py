from collections.abc import Mapping

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import APIException
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.client import IamUnavailable
from fusion_auth.permissions import HasModuleGrant
from modules.department.permissions import VIEW_ANNOUNCEMENT
from modules.department.registry import ROLE_GRANTS
from modules.department.roles import acting_role


class CheckedFields:
    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            writable = {name for name, field in self.fields.items() if not field.read_only}
            unexpected = set(data) - writable
            if unexpected:
                errors = dict.fromkeys(sorted(unexpected), "Remove this unsupported field.")
                raise serializers.ValidationError(errors)
        return super().to_internal_value(data)


class IdentityUnavailable(APIException):
    status_code = 503
    default_detail = "Department membership is temporarily unavailable."
    default_code = "identity_service_unavailable"


def active_permissions(principal):
    return principal.permissions.intersection(ROLE_GRANTS.get(acting_role(principal), ()))


class ActiveDepartmentPermission(BasePermission):
    def __init__(self, codes):
        self.codes = codes

    def has_permission(self, request, view):
        principal = getattr(request, "principal", None)
        if principal is None:
            return False
        return bool(active_permissions(principal).intersection(self.codes))


class DepartmentAccess:
    read_permission = ""
    write_permission = ""
    throttle_scope = "department_write"

    def get_throttles(self):
        if self.request.method in SAFE_METHODS:
            return []
        return super().get_throttles()

    def get_permissions(self):
        is_read = self.request.method in {"GET", "HEAD"}
        permission = self.read_permission if is_read else self.write_permission
        codes = permission if isinstance(permission, tuple) else (permission,)
        return [HasModuleGrant("department")(), ActiveDepartmentPermission(codes)]

    def handle_exception(self, exc):
        if isinstance(exc, IamUnavailable):
            exc = IdentityUnavailable()
        return super().handle_exception(exc)


class DepartmentAccessSerializer(serializers.Serializer):
    permissions = serializers.ListField(child=serializers.CharField())


class DepartmentAccessView(DepartmentAccess, APIView):
    read_permission = VIEW_ANNOUNCEMENT

    @extend_schema(responses=DepartmentAccessSerializer)
    def get(self, request):
        response = Response({"permissions": sorted(active_permissions(request.principal))})
        response["Cache-Control"] = "private, no-store"
        return response
