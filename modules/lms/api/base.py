from rest_framework.exceptions import APIException
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import SAFE_METHODS, BasePermission

from core.api.pagination import CursorPagination
from fusion_auth.client import IamUnavailable
from fusion_auth.permissions import HasModuleGrant, HasPermission, IsAuthenticatedPrincipal
from modules.lms.models import CourseWorkspace
from modules.lms.selectors import scoping


class ActionPermission(BasePermission):
    def has_permission(self, request, view):
        code = view.permission_map.get(request.method)
        return bool(code and HasPermission(code)().has_permission(request, view))


class LmsView(GenericAPIView):
    # Schema discovery gets an empty queryset; runtime reads use scoped selectors.
    queryset = CourseWorkspace.objects.none()
    permission_classes = (IsAuthenticatedPrincipal, HasModuleGrant("lms"), ActionPermission)
    permission_map = {}
    throttle_scope = "lms_write"
    pagination_class = CursorPagination

    @property
    def scope(self):
        if not hasattr(self, "_scope"):
            self._scope = scoping.resolve_scope(self.request.principal)
        return self._scope

    def handle_exception(self, exc):
        if isinstance(exc, IamUnavailable):
            error = APIException(
                "Course authorization and information are temporarily unavailable."
            )
            error.status_code = 503
            return super().handle_exception(error)
        return super().handle_exception(exc)

    def get_throttles(self):
        if self.request.method in SAFE_METHODS:
            return []
        return super().get_throttles()

    def inputs(self, serializer, *, partial=False):
        data = serializer(data=self.request.data, partial=partial)
        data.is_valid(raise_exception=True)
        return data.validated_data

    def listing(self, rows, serializer):
        page = self.paginate_queryset(rows.order_by("-id"))
        return self.get_paginated_response(serializer(page, many=True).data)
