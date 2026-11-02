"""API views for LMS Course Workspace and Materials."""
import os

from django.http import FileResponse
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.lms.api.serializers import (
    CourseAnnouncementCreateSerializer,
    CourseAnnouncementItemSerializer,
    CourseAnnouncementsResponseSerializer,
    CourseMaterialCreateSerializer,
    CourseMaterialItemSerializer,
    CourseMaterialsResponseSerializer,
    CourseMaterialUpdateSerializer,
    CourseSummarySerializer,
    CourseWorkspaceDetailSerializer,
    CourseWorkspaceUpdateSerializer,
)
from modules.lms.selectors.announcements import (
    get_course_announcement_detail,
    list_course_announcements,
)
from modules.lms.selectors.courses import course_workspace_details, visible_courses
from modules.lms.selectors.materials import (
    get_course_material_detail,
    get_material_for_download,
    list_course_materials,
)
from modules.lms.services import announcements as announcement_service
from modules.lms.services import courses as course_service
from modules.lms.services import materials as material_service

MODULE = HasModuleGrant("lms")
P_VIEW = "lms.course.view"
P_MANAGE = "lms.course.manage"
P_MAT_VIEW = "lms.material.view"
P_MAT_MANAGE = "lms.material.manage"
P_ANN_VIEW = "lms.announcement.view"
P_ANN_MANAGE = "lms.announcement.manage"



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


class CourseMaterialListView(APIView):
    """List and create course materials (CFR-LMS-003, CFR-LMS-004)."""

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        perm = P_MAT_VIEW if self.request.method == "GET" else P_MAT_MANAGE
        return [MODULE(), HasPermission(perm)()]

    @extend_schema(
        operation_id="v1_lms_course_materials_list",
        summary="List published/accessible course materials",
        tags=["lms"],
        responses={200: CourseMaterialsResponseSerializer},
    )
    def get(self, request, code: str):
        data = list_course_materials(principal=request.principal, course_code=code)
        if data is None:
            raise NotFoundError("Course not found or you are not authorized to access it.")
        return Response(CourseMaterialsResponseSerializer(data).data)

    @extend_schema(
        operation_id="v1_lms_course_materials_create",
        summary="Add course material as file, link, or note (Faculty only)",
        tags=["lms"],
        request=CourseMaterialCreateSerializer,
        responses={201: CourseMaterialItemSerializer},
    )
    def post(self, request, code: str):
        payload = CourseMaterialCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        material = material_service.create_course_material(
            actor=request.principal,
            course_code=code,
            **payload.validated_data,
        )

        detail = get_course_material_detail(
            principal=request.principal,
            course_code=code,
            material_id=material.id,
        )
        return Response(CourseMaterialItemSerializer(detail).data, status=status.HTTP_201_CREATED)


class CourseMaterialDetailView(APIView):
    """Retrieve, update, or delete a specific course material item."""

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        perm = P_MAT_VIEW if self.request.method == "GET" else P_MAT_MANAGE
        return [MODULE(), HasPermission(perm)()]

    @extend_schema(
        operation_id="v1_lms_course_materials_retrieve",
        summary="Retrieve course material details",
        tags=["lms"],
        responses={200: CourseMaterialItemSerializer},
    )
    def get(self, request, code: str, material_id: int):
        detail = get_course_material_detail(
            principal=request.principal,
            course_code=code,
            material_id=material_id,
        )
        if detail is None:
            raise NotFoundError("Course material not found or not published.")
        return Response(CourseMaterialItemSerializer(detail).data)

    @extend_schema(
        operation_id="v1_lms_course_materials_partial_update",
        summary="Update course material details or schedule (Faculty only)",
        tags=["lms"],
        request=CourseMaterialUpdateSerializer,
        responses={200: CourseMaterialItemSerializer},
    )
    def patch(self, request, code: str, material_id: int):
        payload = CourseMaterialUpdateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        material_service.update_course_material(
            actor=request.principal,
            course_code=code,
            material_id=material_id,
            **payload.validated_data,
        )

        refreshed = get_course_material_detail(
            principal=request.principal,
            course_code=code,
            material_id=material_id,
        )
        return Response(CourseMaterialItemSerializer(refreshed).data, status=status.HTTP_200_OK)

    @extend_schema(
        operation_id="v1_lms_course_materials_destroy",
        summary="Delete a course material item (Faculty only)",
        tags=["lms"],
        responses={204: None},
    )
    def delete(self, request, code: str, material_id: int):
        material_service.delete_course_material(
            actor=request.principal,
            course_code=code,
            material_id=material_id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class CourseMaterialDownloadView(APIView):
    """Download attached course material file with membership verification."""

    permission_classes = [MODULE, HasPermission(P_MAT_VIEW)]

    @extend_schema(
        operation_id="v1_lms_course_materials_download",
        summary="Download published course material file",
        tags=["lms"],
        responses={200: None},
    )
    def get(self, request, code: str, material_id: int):
        material = get_material_for_download(
            principal=request.principal,
            course_code=code,
            material_id=material_id,
        )
        if material is None or not material.file:
            raise NotFoundError(
                "Material file not found or you are not authorized to download it."
            )

        filename = material.file_name or os.path.basename(material.file.name)
        return FileResponse(material.file.open("rb"), as_attachment=True, filename=filename)


class CourseAnnouncementListView(APIView):
    """List and post course announcements (CFR-LMS-005, UC-LMS-005, UC-LMS-006)."""

    def get_permissions(self):
        perm = P_ANN_VIEW if self.request.method == "GET" else P_ANN_MANAGE
        return [MODULE(), HasPermission(perm)()]

    @extend_schema(
        operation_id="v1_lms_course_announcements_list",
        summary="List course announcements",
        tags=["lms"],
        responses={200: CourseAnnouncementsResponseSerializer},
    )
    def get(self, request, code: str):
        data = list_course_announcements(principal=request.principal, course_code=code)
        if data is None:
            raise NotFoundError("Course not found or you are not authorized to access it.")
        return Response(CourseAnnouncementsResponseSerializer(data).data)

    @extend_schema(
        operation_id="v1_lms_course_announcements_create",
        summary="Post a course-wide announcement (Faculty only)",
        tags=["lms"],
        request=CourseAnnouncementCreateSerializer,
        responses={201: CourseAnnouncementItemSerializer},
    )
    def post(self, request, code: str):
        payload = CourseAnnouncementCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        announcement = announcement_service.post_course_announcement(
            actor=request.principal,
            course_code=code,
            **payload.validated_data,
        )

        detail = get_course_announcement_detail(
            principal=request.principal,
            course_code=code,
            announcement_id=announcement.id,
        )
        return Response(
            CourseAnnouncementItemSerializer(detail).data,
            status=status.HTTP_201_CREATED,
        )



class CourseAnnouncementDetailView(APIView):
    """Retrieve details for a specific course announcement."""

    permission_classes = [MODULE, HasPermission(P_ANN_VIEW)]

    @extend_schema(
        operation_id="v1_lms_course_announcements_retrieve",
        summary="Retrieve course announcement details",
        tags=["lms"],
        responses={200: CourseAnnouncementItemSerializer},
    )
    def get(self, request, code: str, announcement_id: int):
        detail = get_course_announcement_detail(
            principal=request.principal,
            course_code=code,
            announcement_id=announcement_id,
        )
        if detail is None:
            raise NotFoundError("Course announcement not found.")
        return Response(CourseAnnouncementItemSerializer(detail).data)

