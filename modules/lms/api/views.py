"""API views for LMS Course Workspace."""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.lms.api.serializers import (
    CourseSummarySerializer,
    CourseWorkspaceDetailSerializer,
    CourseWorkspaceUpdateSerializer,
)
from modules.lms.selectors.courses import course_workspace_details, visible_courses
from modules.lms.services import courses as course_service

MODULE = HasModuleGrant("lms")
P_VIEW = "lms.course.view"
P_MANAGE = "lms.course.manage"


class CourseListView(APIView):
    """List all course workspaces the caller is enrolled in, assigned to, or linked to."""

    permission_classes = [MODULE, HasPermission(P_VIEW)]

    @extend_schema(
        summary="List authorized course workspaces",
        tags=["lms"],
        responses=CourseSummarySerializer(many=True),
    )
    def get(self, request):
        courses = visible_courses(request.principal)
        return Response({"results": CourseSummarySerializer(courses, many=True).data})


class CourseWorkspaceDetailView(APIView):
    """View and manage course home workspace details."""

    def get_permissions(self):
        perm = P_VIEW if self.request.method == "GET" else P_MANAGE
        return [MODULE(), HasPermission(perm)()]

    @extend_schema(
        summary="Retrieve course workspace details",
        tags=["lms"],
        responses={200: CourseWorkspaceDetailSerializer},
    )
    def get(self, request, code: str):
        data = course_workspace_details(principal=request.principal, course_code=code)
        if data is None:
            raise NotFoundError(
                "Course workspace not found or you are not authorized to access it."
            )
        return Response(CourseWorkspaceDetailSerializer(data).data)

    @extend_schema(
        summary="Configure course workspace details (Faculty only)",
        tags=["lms"],
        request=CourseWorkspaceUpdateSerializer,
        responses={200: CourseWorkspaceDetailSerializer},
    )
    def patch(self, request, code: str):
        payload = CourseWorkspaceUpdateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        course_service.update_course_workspace(
            actor=request.principal,
            course_code=code,
            **payload.validated_data,
        )

        refreshed = course_workspace_details(principal=request.principal, course_code=code)
        return Response(CourseWorkspaceDetailSerializer(refreshed).data, status=status.HTTP_200_OK)
