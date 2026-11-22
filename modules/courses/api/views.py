"""Course Workspace and Materials API views (CFR-LMS-001, CFR-LMS-002, CFR-LMS-003, CFR-LMS-004)."""
from __future__ import annotations

from urllib.parse import quote

from django.http import FileResponse
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError, PermissionDeniedError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.courses.api import serializers as s
from modules.courses.models import CourseAssignment, CourseWorkspace
from modules.courses.domain.grades import GradeDomainError
from modules.courses.permissions import MODULE_CODE, P_WORKSPACE_MANAGE, P_WORKSPACE_VIEW
from modules.courses.selectors import announcements as announcements_selectors
from modules.courses.selectors import assignments as assignments_selectors
from modules.courses.selectors import grades as grades_selectors
from modules.courses.selectors import materials as materials_selectors
from modules.courses.selectors import scoping
from modules.courses.selectors import submissions as submissions_selectors
from modules.courses.services import announcements as announcements_svc
from modules.courses.services import assignments as assignments_svc
from modules.courses.services import grades as grades_svc
from modules.courses.services import materials as materials_svc
from modules.courses.services import submissions as submissions_svc
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


class CourseSubmissionsView(APIView):
    """List submissions or submit assignment work for a course assignment (UC-LMS-010)."""

    permission_classes = [MODULE, HasPermission(P_WORKSPACE_VIEW)]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(responses=s.CourseSubmissionSerializer(many=True))
    def get(self, request, workspace_id: int, assignment_id: int):
        workspace = CourseWorkspace.objects.filter(pk=workspace_id).first()
        if not workspace:
            raise NotFoundError("Course workspace not found.")
        mem = scoping.get_workspace_membership(workspace, request.principal)
        if not mem:
            raise NotFoundError("Course workspace not found.")

        if mem.role == "observer":
            raise PermissionDeniedError("Observers are not permitted to view student submissions (BR-LMS-003).")

        assignment = CourseAssignment.objects.filter(pk=assignment_id, workspace=workspace).first()
        if not assignment:
            raise NotFoundError("Course assignment not found.")

        qs = submissions_selectors.visible_submissions(workspace, assignment, request.principal)
        return Response({
            "count": qs.count(),
            "results": s.CourseSubmissionSerializer(
                qs, many=True, context={"request": request, "viewer_role": mem.role}
            ).data,
        })

    @extend_schema(
        request=s.CourseSubmissionCreateSerializer,
        responses=s.CourseSubmissionSerializer,
    )
    def post(self, request, workspace_id: int, assignment_id: int):
        workspace = CourseWorkspace.objects.filter(pk=workspace_id).first()
        if not workspace:
            raise NotFoundError("Course workspace not found.")
        mem = scoping.get_workspace_membership(workspace, request.principal)
        if not mem:
            raise NotFoundError("Course workspace not found.")

        if mem.role != "student":
            raise PermissionDeniedError("Only enrolled students may submit assignment work.")

        payload = s.CourseSubmissionCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        uploaded_file = request.FILES.get("file")
        submission = submissions_svc.submit_assignment(
            workspace_id=workspace_id,
            assignment_id=assignment_id,
            principal=request.principal,
            submission_type=payload.validated_data.get("submission_type", "file"),
            content=payload.validated_data.get("content", ""),
            link_url=payload.validated_data.get("link_url", ""),
            file=uploaded_file,
        )
        return Response(
            s.CourseSubmissionSerializer(submission, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class CourseMySubmissionView(APIView):
    """Retrieve the calling student's own submission for an assignment (BR-LMS-014)."""

    permission_classes = [MODULE, HasPermission(P_WORKSPACE_VIEW)]

    @extend_schema(responses=s.CourseSubmissionSerializer)
    def get(self, request, workspace_id: int, assignment_id: int):
        workspace = CourseWorkspace.objects.filter(pk=workspace_id).first()
        if not workspace:
            raise NotFoundError("Course workspace not found.")
        mem = scoping.get_workspace_membership(workspace, request.principal)
        if not mem:
            raise NotFoundError("Course workspace not found.")

        if mem.role == "observer":
            raise PermissionDeniedError("Observers are not permitted to view student submissions (BR-LMS-003).")

        assignment = CourseAssignment.objects.filter(pk=assignment_id, workspace=workspace).first()
        if not assignment:
            raise NotFoundError("Course assignment not found.")

        submission = submissions_selectors.get_student_submission(workspace, assignment, request.principal)
        if not submission:
            return Response(None, status=status.HTTP_200_OK)

        return Response(s.CourseSubmissionSerializer(submission, context={"request": request, "viewer_role": mem.role}).data)


class CourseSubmissionDetailView(APIView):
    """Retrieve details for a specific submission (enforces observer restriction and student privacy)."""

    permission_classes = [MODULE, HasPermission(P_WORKSPACE_VIEW)]

    @extend_schema(responses=s.CourseSubmissionSerializer)
    def get(self, request, workspace_id: int, assignment_id: int, pk: int):
        workspace = CourseWorkspace.objects.filter(pk=workspace_id).first()
        if not workspace:
            raise NotFoundError("Course workspace not found.")
        mem = scoping.get_workspace_membership(workspace, request.principal)
        if not mem:
            raise NotFoundError("Course workspace not found.")

        if mem.role == "observer":
            raise PermissionDeniedError("Observers are not permitted to view student submissions (BR-LMS-003).")

        submission = submissions_selectors.get_submission_for_actor(
            workspace_id=workspace_id,
            assignment_id=assignment_id,
            submission_id=pk,
            principal=request.principal,
        )
        if not submission:
            # If a student tried to guess another student's submission id in the same course,
            # or an unrelated workspace
            raise NotFoundError("Course submission not found.")

        return Response(s.CourseSubmissionSerializer(submission, context={"request": request, "viewer_role": mem.role}).data)


class CourseSubmissionDownloadView(APIView):
    """Download the submitted file securely (BR-LMS-003, BR-LMS-004, BR-LMS-014)."""

    permission_classes = [MODULE, HasPermission(P_WORKSPACE_VIEW)]

    @extend_schema(responses={(200, "application/octet-stream"): bytes})
    def get(self, request, workspace_id: int, assignment_id: int, pk: int):
        workspace = CourseWorkspace.objects.filter(pk=workspace_id).first()
        if not workspace:
            raise NotFoundError("Course workspace not found.")
        mem = scoping.get_workspace_membership(workspace, request.principal)
        if not mem:
            raise NotFoundError("Course workspace not found.")

        if mem.role == "observer":
            raise PermissionDeniedError("Observers are not permitted to download student submissions (BR-LMS-003).")

        submission = submissions_selectors.get_submission_for_actor(
            workspace_id=workspace_id,
            assignment_id=assignment_id,
            submission_id=pk,
            principal=request.principal,
        )
        if not submission:
            raise NotFoundError("Course submission not found.")

        if submission.submission_type != "file" or not submission.file:
            raise NotFoundError("Submission file not found.")

        try:
            stream = submission.file.open("rb")
        except (OSError, FileNotFoundError) as exc:
            raise NotFoundError("Physical file not found.") from exc

        filename = submission.filename or "submission"
        disposition = f'attachment; filename="{filename}"; filename*=UTF-8\'\'{quote(filename)}'
        response = FileResponse(stream, content_type=submission.mime_type or "application/octet-stream")
        response["Content-Disposition"] = disposition
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store"
        return response


class CourseSubmissionGradeView(APIView):
    """Grade or update marks and feedback for a student submission (UC-LMS-012, BR-LMS-015, BR-LMS-019)."""

    permission_classes = [MODULE, HasPermission(P_WORKSPACE_VIEW)]

    @extend_schema(
        request=s.CourseGradeInputSerializer,
        responses=s.CourseGradeSerializer,
    )
    def post(self, request, workspace_id: int, assignment_id: int, pk: int):
        workspace = CourseWorkspace.objects.filter(pk=workspace_id).first()
        if not workspace:
            raise NotFoundError("Course workspace not found.")
        mem = scoping.get_workspace_membership(workspace, request.principal)
        if not mem:
            raise NotFoundError("Course workspace not found.")

        if mem.role not in ("instructor", "ta"):
            raise PermissionDeniedError("Only faculty and teaching assistants may grade submissions (BR-LMS-015).")

        payload = s.CourseGradeInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        try:
            grade = grades_svc.record_or_update_grade(
                workspace=workspace,
                submission_id=pk,
                grader_id=request.principal.user_id,
                grader_role=mem.role,
                score=payload.validated_data["score"],
                feedback=payload.validated_data.get("feedback", ""),
            )
        except GradeDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(s.CourseGradeSerializer(grade, context={"request": request}).data, status=status.HTTP_200_OK)


class CourseAssignmentReleaseGradesView(APIView):
    """Release draft grades to students for an assignment (UC-LMS-013, BR-LMS-017)."""

    permission_classes = [MODULE, HasPermission(P_WORKSPACE_VIEW)]

    @extend_schema(
        request=s.CourseGradeReleaseSerializer,
        responses=s.CourseGradeReleaseResponseSerializer,
    )
    def post(self, request, workspace_id: int, assignment_id: int):
        workspace = CourseWorkspace.objects.filter(pk=workspace_id).first()
        if not workspace:
            raise NotFoundError("Course workspace not found.")
        mem = scoping.get_workspace_membership(workspace, request.principal)
        if not mem:
            raise NotFoundError("Course workspace not found.")

        if mem.role != "instructor":
            raise PermissionDeniedError("Only faculty members are authorized to release grades (BR-LMS-017).")

        submission_id = request.data.get("submission_id") if isinstance(request.data, dict) else None

        try:
            released = grades_svc.release_assignment_grades(
                workspace=workspace,
                assignment_id=assignment_id,
                actor_id=request.principal.user_id,
                actor_role=mem.role,
                submission_id=submission_id,
            )
        except GradeDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "released_count": len(released),
                "results": s.CourseGradeSerializer(released, many=True, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class CourseGradeAuditView(APIView):
    """Retrieve audit history for a submission's grade (BR-LMS-019). Faculty and TA only."""

    permission_classes = [MODULE, HasPermission(P_WORKSPACE_VIEW)]

    @extend_schema(responses=s.CourseGradeAuditSerializer(many=True))
    def get(self, request, workspace_id: int, assignment_id: int, pk: int):
        workspace = CourseWorkspace.objects.filter(pk=workspace_id).first()
        if not workspace:
            raise NotFoundError("Course workspace not found.")
        mem = scoping.get_workspace_membership(workspace, request.principal)
        if not mem:
            raise NotFoundError("Course workspace not found.")

        if mem.role not in ("instructor", "ta"):
            raise PermissionDeniedError("Access to grade audit logs is restricted to faculty and teaching assistants (BR-LMS-019).")

        try:
            from modules.courses.models import CourseGrade, CourseSubmission
            submission = CourseSubmission.objects.get(pk=pk, workspace=workspace, assignment_id=assignment_id)
            grade = submission.grade
        except (CourseSubmission.DoesNotExist, CourseGrade.DoesNotExist):
            raise NotFoundError("Grade record not found.")

        logs = grades_selectors.get_grade_audit_logs(
            workspace=workspace,
            grade_id=grade.id,
            actor_role=mem.role,
        )
        return Response(s.CourseGradeAuditSerializer(logs, many=True, context={"request": request}).data)



