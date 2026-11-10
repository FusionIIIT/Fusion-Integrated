"""Course Workspace and Materials API views (CFR-LMS-001, CFR-LMS-002, CFR-LMS-003, CFR-LMS-004)."""
from __future__ import annotations

from urllib.parse import quote

from django.http import FileResponse
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError, PermissionDeniedError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.courses.api import serializers as s
from modules.courses.models import CourseWorkspace
from modules.courses.permissions import MODULE_CODE, P_WORKSPACE_MANAGE, P_WORKSPACE_VIEW
from modules.courses.selectors import announcements as announcements_selectors
from modules.courses.selectors import assignments as assignments_selectors
from modules.courses.selectors import materials as materials_selectors
from modules.courses.selectors import scoping
from modules.courses.services import announcements as announcements_svc
from modules.courses.services import assignments as assignments_svc
from modules.courses.services import materials as materials_svc
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


class CourseSectionsView(APIView):
    """List or create sections / modules for a course workspace (AFR-LMS-003.2)."""

    permission_classes = [MODULE, HasPermission(P_WORKSPACE_VIEW)]

    @extend_schema(responses=s.CourseMaterialSectionSerializer(many=True))
    def get(self, request, workspace_id: int):
        workspace = CourseWorkspace.objects.filter(pk=workspace_id).first()
        if not workspace:
            raise NotFoundError("Course workspace not found.")
        mem = scoping.get_workspace_membership(workspace, request.principal)
        if not mem:
            raise NotFoundError("Course workspace not found.")

        sections = materials_selectors.visible_sections(workspace, request.principal)
        return Response(s.CourseMaterialSectionSerializer(sections, many=True).data)

    @extend_schema(
        request=s.CourseMaterialSectionCreateUpdateSerializer,
        responses=s.CourseMaterialSectionSerializer,
    )
    def post(self, request, workspace_id: int):
        if not request.principal.has_permission(P_WORKSPACE_MANAGE):
            raise PermissionDeniedError("You do not have permission to manage course sections.")
        payload = s.CourseMaterialSectionCreateUpdateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        section = materials_svc.create_section(
            workspace_id=workspace_id,
            principal=request.principal,
            **payload.validated_data,
        )
        return Response(
            s.CourseMaterialSectionSerializer(section).data,
            status=status.HTTP_201_CREATED,
        )


class CourseSectionDetailView(APIView):
    """Update or delete a section in a course workspace."""

    permission_classes = [MODULE, HasPermission(P_WORKSPACE_VIEW)]

    @extend_schema(
        request=s.CourseMaterialSectionCreateUpdateSerializer,
        responses=s.CourseMaterialSectionSerializer,
    )
    def patch(self, request, workspace_id: int, pk: int):
        if not request.principal.has_permission(P_WORKSPACE_MANAGE):
            raise PermissionDeniedError("You do not have permission to manage course sections.")
        payload = s.CourseMaterialSectionCreateUpdateSerializer(data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        section = materials_svc.update_section(
            workspace_id=workspace_id,
            section_id=pk,
            principal=request.principal,
            **payload.validated_data,
        )
        return Response(s.CourseMaterialSectionSerializer(section).data)

    @extend_schema(responses={204: None})
    def delete(self, request, workspace_id: int, pk: int):
        if not request.principal.has_permission(P_WORKSPACE_MANAGE):
            raise PermissionDeniedError("You do not have permission to manage course sections.")
        materials_svc.delete_section(
            workspace_id=workspace_id,
            section_id=pk,
            principal=request.principal,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class CourseMaterialsView(APIView):
    """List or create materials for a course workspace (CFR-LMS-003, CFR-LMS-004)."""

    permission_classes = [MODULE, HasPermission(P_WORKSPACE_VIEW)]

    @extend_schema(responses=s.CourseMaterialSerializer(many=True))
    def get(self, request, workspace_id: int):
        workspace = CourseWorkspace.objects.filter(pk=workspace_id).first()
        if not workspace:
            raise NotFoundError("Course workspace not found.")
        mem = scoping.get_workspace_membership(workspace, request.principal)
        if not mem:
            raise NotFoundError("Course workspace not found.")

        qs = materials_selectors.visible_materials(workspace, request.principal)
        section_id = request.query_params.get("section_id")
        if section_id is not None and section_id.strip():
            try:
                qs = qs.filter(section_id=int(section_id))
            except (ValueError, TypeError):
                pass
        return Response({
            "count": qs.count(),
            "results": s.CourseMaterialSerializer(
                qs, many=True, context={"request": request}
            ).data,
        })

    @extend_schema(
        request=s.CourseMaterialCreateSerializer,
        responses=s.CourseMaterialSerializer,
    )
    def post(self, request, workspace_id: int):
        if not request.principal.has_permission(P_WORKSPACE_MANAGE):
            raise PermissionDeniedError("You do not have permission to manage course materials.")
        payload = s.CourseMaterialCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        material = materials_svc.create_material(
            workspace_id=workspace_id,
            principal=request.principal,
            **payload.validated_data,
        )
        return Response(
            s.CourseMaterialSerializer(material, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class CourseMaterialDetailView(APIView):
    """Retrieve, update, or delete a specific course material item."""

    permission_classes = [MODULE, HasPermission(P_WORKSPACE_VIEW)]

    @extend_schema(responses=s.CourseMaterialSerializer)
    def get(self, request, workspace_id: int, pk: int):
        material = materials_selectors.get_material_for_actor(
            workspace_id=workspace_id,
            material_id=pk,
            principal=request.principal,
        )
        if not material:
            raise NotFoundError("Course material not found.")
        return Response(s.CourseMaterialSerializer(material, context={"request": request}).data)

    @extend_schema(
        request=s.CourseMaterialUpdateSerializer,
        responses=s.CourseMaterialSerializer,
    )
    def patch(self, request, workspace_id: int, pk: int):
        if not request.principal.has_permission(P_WORKSPACE_MANAGE):
            raise PermissionDeniedError("You do not have permission to manage course materials.")
        payload = s.CourseMaterialUpdateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        material = materials_svc.update_material(
            workspace_id=workspace_id,
            material_id=pk,
            principal=request.principal,
            **payload.validated_data,
        )
        return Response(s.CourseMaterialSerializer(material, context={"request": request}).data)

    @extend_schema(responses={204: None})
    def delete(self, request, workspace_id: int, pk: int):
        if not request.principal.has_permission(P_WORKSPACE_MANAGE):
            raise PermissionDeniedError("You do not have permission to manage course materials.")
        materials_svc.delete_material(
            workspace_id=workspace_id,
            material_id=pk,
            principal=request.principal,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class CourseMaterialDownloadView(APIView):
    """Download the attached file of a course material securely (CFR-LMS-004)."""

    permission_classes = [MODULE, HasPermission(P_WORKSPACE_VIEW)]

    @extend_schema(responses={(200, "application/octet-stream"): bytes})
    def get(self, request, workspace_id: int, pk: int):
        material = materials_selectors.get_material_for_actor(
            workspace_id=workspace_id,
            material_id=pk,
            principal=request.principal,
        )
        if not material:
            raise NotFoundError("Course material not found.")

        if material.material_type != "file" or not material.file:
            raise NotFoundError("Material file not found.")

        try:
            stream = material.file.open("rb")
        except (OSError, FileNotFoundError) as exc:
            raise NotFoundError("Physical file not found.") from exc

        filename = material.filename or "download"
        disposition = f'attachment; filename="{filename}"; filename*=UTF-8\'\'{quote(filename)}'
        response = FileResponse(stream, content_type=material.mime_type or "application/octet-stream")
        response["Content-Disposition"] = disposition
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store"
        return response


class CourseAnnouncementsView(APIView):
    """List or create announcements for a course workspace (CFR-LMS-005)."""

    permission_classes = [MODULE, HasPermission(P_WORKSPACE_VIEW)]

    @extend_schema(responses=s.CourseAnnouncementSerializer(many=True))
    def get(self, request, workspace_id: int):
        workspace = CourseWorkspace.objects.filter(pk=workspace_id).first()
        if not workspace:
            raise NotFoundError("Course workspace not found.")
        mem = scoping.get_workspace_membership(workspace, request.principal)
        if not mem:
            raise NotFoundError("Course workspace not found.")

        qs = announcements_selectors.visible_announcements(workspace, request.principal)
        return Response({
            "count": qs.count(),
            "results": s.CourseAnnouncementSerializer(
                qs, many=True, context={"request": request}
            ).data,
        })

    @extend_schema(
        request=s.CourseAnnouncementCreateSerializer,
        responses=s.CourseAnnouncementSerializer,
    )
    def post(self, request, workspace_id: int):
        if not request.principal.has_permission(P_WORKSPACE_MANAGE):
            raise PermissionDeniedError("You do not have permission to manage course announcements.")
        payload = s.CourseAnnouncementCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        announcement = announcements_svc.create_announcement(
            workspace_id=workspace_id,
            principal=request.principal,
            **payload.validated_data,
        )
        return Response(
            s.CourseAnnouncementSerializer(announcement, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class CourseAnnouncementDetailView(APIView):
    """Retrieve, update, or delete a specific course announcement."""

    permission_classes = [MODULE, HasPermission(P_WORKSPACE_VIEW)]

    @extend_schema(responses=s.CourseAnnouncementSerializer)
    def get(self, request, workspace_id: int, pk: int):
        announcement = announcements_selectors.get_announcement_for_actor(
            workspace_id=workspace_id,
            announcement_id=pk,
            principal=request.principal,
        )
        if not announcement:
            raise NotFoundError("Course announcement not found.")
        return Response(s.CourseAnnouncementSerializer(announcement, context={"request": request}).data)

    @extend_schema(
        request=s.CourseAnnouncementUpdateSerializer,
        responses=s.CourseAnnouncementSerializer,
    )
    def patch(self, request, workspace_id: int, pk: int):
        if not request.principal.has_permission(P_WORKSPACE_MANAGE):
            raise PermissionDeniedError("You do not have permission to manage course announcements.")
        payload = s.CourseAnnouncementUpdateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        announcement = announcements_svc.update_announcement(
            workspace_id=workspace_id,
            announcement_id=pk,
            principal=request.principal,
            **payload.validated_data,
        )
        return Response(s.CourseAnnouncementSerializer(announcement, context={"request": request}).data)

    @extend_schema(responses={204: None})
    def delete(self, request, workspace_id: int, pk: int):
        if not request.principal.has_permission(P_WORKSPACE_MANAGE):
            raise PermissionDeniedError("You do not have permission to manage course announcements.")
        announcements_svc.delete_announcement(
            workspace_id=workspace_id,
            announcement_id=pk,
            principal=request.principal,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class CourseAssignmentsView(APIView):
    """List or create assignments for a course workspace (CFR-LMS-006)."""

    permission_classes = [MODULE, HasPermission(P_WORKSPACE_VIEW)]

    @extend_schema(responses=s.CourseAssignmentSerializer(many=True))
    def get(self, request, workspace_id: int):
        workspace = CourseWorkspace.objects.filter(pk=workspace_id).first()
        if not workspace:
            raise NotFoundError("Course workspace not found.")
        mem = scoping.get_workspace_membership(workspace, request.principal)
        if not mem:
            raise NotFoundError("Course workspace not found.")

        qs = assignments_selectors.visible_assignments(workspace, request.principal)
        return Response({
            "count": qs.count(),
            "results": s.CourseAssignmentSerializer(
                qs, many=True, context={"request": request}
            ).data,
        })

    @extend_schema(
        request=s.CourseAssignmentCreateSerializer,
        responses=s.CourseAssignmentSerializer,
    )
    def post(self, request, workspace_id: int):
        if not request.principal.has_permission(P_WORKSPACE_MANAGE):
            raise PermissionDeniedError("You do not have permission to manage course assignments.")
        payload = s.CourseAssignmentCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        assignment = assignments_svc.create_assignment(
            workspace_id=workspace_id,
            principal=request.principal,
            **payload.validated_data,
        )
        return Response(
            s.CourseAssignmentSerializer(assignment, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class CourseAssignmentDetailView(APIView):
    """Retrieve, update, or delete a specific course assignment."""

    permission_classes = [MODULE, HasPermission(P_WORKSPACE_VIEW)]

    @extend_schema(responses=s.CourseAssignmentSerializer)
    def get(self, request, workspace_id: int, pk: int):
        assignment = assignments_selectors.get_assignment_for_actor(
            workspace_id=workspace_id,
            assignment_id=pk,
            principal=request.principal,
        )
        if not assignment:
            raise NotFoundError("Course assignment not found.")
        return Response(s.CourseAssignmentSerializer(assignment, context={"request": request}).data)

    @extend_schema(
        request=s.CourseAssignmentUpdateSerializer,
        responses=s.CourseAssignmentSerializer,
    )
    def patch(self, request, workspace_id: int, pk: int):
        if not request.principal.has_permission(P_WORKSPACE_MANAGE):
            raise PermissionDeniedError("You do not have permission to manage course assignments.")
        payload = s.CourseAssignmentUpdateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        assignment = assignments_svc.update_assignment(
            workspace_id=workspace_id,
            assignment_id=pk,
            principal=request.principal,
            **payload.validated_data,
        )
        return Response(s.CourseAssignmentSerializer(assignment, context={"request": request}).data)

    @extend_schema(responses={204: None})
    def delete(self, request, workspace_id: int, pk: int):
        if not request.principal.has_permission(P_WORKSPACE_MANAGE):
            raise PermissionDeniedError("You do not have permission to manage course assignments.")
        assignments_svc.delete_assignment(
            workspace_id=workspace_id,
            assignment_id=pk,
            principal=request.principal,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


