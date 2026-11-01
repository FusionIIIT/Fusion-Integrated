"""Course Workspace API views (CFR-LMS-001, CFR-LMS-002)."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError, PermissionDeniedError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.courses.api import serializers as s
from modules.courses.models import CourseWorkspace
from modules.courses.permissions import MODULE_CODE, P_WORKSPACE_MANAGE, P_WORKSPACE_VIEW
from modules.courses.selectors import scoping
from modules.courses.services import workspace as workspace_svc

MODULE = HasModuleGrant(MODULE_CODE)


@extend_schema(responses=s.WorkspaceSummarySerializer(many=True))
class WorkspacesListView(APIView):
    """List course workspaces visible to the requesting actor (AFR-LMS-001.1)."""

    permission_classes = [MODULE, HasPermission(P_WORKSPACE_VIEW)]

    def get(self, request):
        qs = scoping.visible_workspaces(request.principal)
        return Response({
            "count": qs.count(),
            "results": s.WorkspaceSummarySerializer(
                qs, many=True, context={"request": request},
            ).data,
        })


class WorkspaceDetailView(APIView):
    """Retrieve or update course workspace details."""

    permission_classes = [MODULE, HasPermission(P_WORKSPACE_VIEW)]

    @extend_schema(responses=s.WorkspaceDetailSerializer)
    def get(self, request, pk: int):
        workspace = CourseWorkspace.objects.filter(pk=pk).first()
        if not workspace:
            raise NotFoundError("Course workspace not found.")

        # Course-specific access control (BR-LMS-001, AFR-LMS-001.3)
        mem = scoping.get_workspace_membership(workspace, request.principal)
        if not mem:
            raise NotFoundError("Course workspace not found.")

        return Response(
            s.WorkspaceDetailSerializer(
                workspace, context={"request": request},
            ).data
        )

    @extend_schema(
        request=s.WorkspaceUpdateSerializer,
        responses=s.WorkspaceDetailSerializer,
    )
    def patch(self, request, pk: int):
        # Fine-grained authorization check (AFR-LMS-002.1)
        if not request.principal.has_permission(P_WORKSPACE_MANAGE):
            raise PermissionDeniedError(
                "You do not have permission to configure this course workspace."
            )

        payload = s.WorkspaceUpdateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        updated = workspace_svc.update_workspace(
            workspace_id=pk,
            principal=request.principal,
            **payload.validated_data,
        )
        return Response(
            s.WorkspaceDetailSerializer(
                updated, context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )
