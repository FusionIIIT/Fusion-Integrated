from rest_framework.exceptions import APIException

from fusion_auth.client import IamUnavailable
from fusion_auth.permissions import HasModuleGrant, HasPermission


class IdentityUnavailable(APIException):
    status_code = 503
    default_detail = "Department membership is temporarily unavailable."
    default_code = "identity_service_unavailable"


class DepartmentAccess:
    read_permission = ""
    write_permission = ""

    def get_permissions(self):
        is_read = self.request.method in {"GET", "HEAD"}
        permission = self.read_permission if is_read else self.write_permission
        codes = permission if isinstance(permission, tuple) else (permission,)
        return [HasModuleGrant("department")(), HasPermission(*codes)()]

    def handle_exception(self, exc):
        if isinstance(exc, IamUnavailable):
            exc = IdentityUnavailable()
        return super().handle_exception(exc)
