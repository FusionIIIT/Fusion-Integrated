"""REST API Views for LMS module."""

from __future__ import annotations

import os
from urllib.parse import quote

from django.http import FileResponse
from drf_spectacular.utils import OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from core.files.validators import sanitise_filename
from modules.lms import selectors, services
from modules.lms.api.permissions import RequireLmsPermission
from modules.lms.api.serializers import (
    AssignmentSerializer,
    AssignmentSubmissionSerializer,
    CourseAnnouncementSerializer,
    CourseMaterialSerializer,
    CourseWorkspaceDetailSerializer,
    CourseWorkspaceSummarySerializer,
    CourseWorkspaceUpdateSerializer,
    GradeChangeAuditSerializer,
    PublishGradesRequestSerializer,
    PublishGradesResponseSerializer,
    SubmissionGradeSerializer,
)


class CourseWorkspaceListView(APIView):
    permission_classes = [RequireLmsPermission("lms.workspace.view")]
    serializer_class = CourseWorkspaceSummarySerializer

    @extend_schema(
        responses=CourseWorkspaceSummarySerializer(many=True),
        operation_id="lms_workspace_list",
    )
    def get(self, request):
        courses = selectors.list_user_courses(request.principal)
        return Response(CourseWorkspaceSummarySerializer(courses, many=True).data)


class CourseWorkspaceDetailView(APIView):
    serializer_class = CourseWorkspaceDetailSerializer

    def get_permissions(self):
        if self.request.method in ("PATCH", "PUT"):
            return [RequireLmsPermission("lms.workspace.update")()]
        return [RequireLmsPermission("lms.workspace.view")()]

    @extend_schema(
        responses=CourseWorkspaceDetailSerializer,
        operation_id="lms_workspace_detail",
    )
    def get(self, request, course_id: int):
        details = selectors.get_course_home_details(course_id, request.principal)
        if details is None:
            raise NotFoundError("Course workspace not found or access denied.")
        return Response(CourseWorkspaceDetailSerializer(details).data)

    @extend_schema(
        request=CourseWorkspaceUpdateSerializer,
        responses=CourseWorkspaceDetailSerializer,
        operation_id="lms_workspace_update",
    )
    def patch(self, request, course_id: int):
        serializer = CourseWorkspaceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.update_course_details(
                course_id=course_id,
                syllabus=serializer.validated_data.get("syllabus", ""),
                schedule_info=serializer.validated_data.get("schedule_info", ""),
                principal=request.principal,
            )
        except ValueError as e:
            raise BadRequestError(str(e)) from e
        details = selectors.get_course_home_details(course_id, request.principal)
        if details is None:
            raise NotFoundError("Course workspace not found or access denied.")
        return Response(CourseWorkspaceDetailSerializer(details).data)


class CourseMaterialListCreateView(APIView):
    serializer_class = CourseMaterialSerializer
    throttle_scope = "upload"

    def get_throttles(self):
        if self.request.method == "POST":
            return super().get_throttles()
        return []

    def get_permissions(self):
        if self.request.method == "POST":
            return [
                RequireLmsPermission("lms.material.create")(),
                RequireLmsPermission("lms.material.publish")(),
            ]
        return [RequireLmsPermission("lms.material.view")()]

    @extend_schema(
        responses=CourseMaterialSerializer(many=True),
        operation_id="lms_material_list",
    )
    def get(self, request):
        course_id = request.query_params.get("course_id")
        if not course_id:
            raise BadRequestError("course_id query param is required.")
        try:
            c_id = int(course_id)
        except (ValueError, TypeError) as e:
            raise BadRequestError("course_id must be an integer.") from e
        materials = selectors.list_published_materials(c_id, request.principal)
        return Response(CourseMaterialSerializer(materials, many=True).data)

    @extend_schema(
        request=CourseMaterialSerializer,
        responses=CourseMaterialSerializer,
        operation_id="lms_material_create",
    )
    def post(self, request):
        serializer = CourseMaterialSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            material = services.create_material(
                course_id=serializer.validated_data["course_id"],
                title=serializer.validated_data["title"],
                description=serializer.validated_data.get("description", ""),
                material_type=serializer.validated_data["material_type"],
                content_text=serializer.validated_data.get("content_text", ""),
                external_url=serializer.validated_data.get("external_url", ""),
                file_attachment=request.FILES.get("file_attachment"),
                section_name=serializer.validated_data.get("section_name", "General"),
                sort_order=serializer.validated_data.get("sort_order", 0),
                release_date=serializer.validated_data.get("release_date"),
                principal=request.principal,
            )
        except ValueError as e:
            raise BadRequestError(str(e)) from e
        return Response(CourseMaterialSerializer(material).data, status=status.HTTP_201_CREATED)


class CourseMaterialDetailView(APIView):
    serializer_class = CourseMaterialSerializer

    def get_permissions(self):
        if self.request.method == "DELETE":
            return [RequireLmsPermission("lms.material.delete")()]
        if self.request.method in ("PATCH", "PUT"):
            return [RequireLmsPermission("lms.material.update")()]
        return [RequireLmsPermission("lms.material.view")()]

    @extend_schema(responses=CourseMaterialSerializer, operation_id="lms_material_retrieve")
    def get(self, request, material_id: int):
        material = selectors.get_material_detail(material_id, request.principal)
        if not material:
            raise NotFoundError("Material not found or access denied.")
        return Response(CourseMaterialSerializer(material).data)

    @extend_schema(
        request=CourseMaterialSerializer,
        responses=CourseMaterialSerializer,
        operation_id="lms_material_update",
    )
    def patch(self, request, material_id: int):
        serializer = CourseMaterialSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        material = selectors.get_material_detail(material_id, request.principal)
        if not material:
            raise NotFoundError("Material not found or access denied.")
        for field, value in serializer.validated_data.items():
            setattr(material, field, value)
        material.save()
        return Response(CourseMaterialSerializer(material).data)

    @extend_schema(responses={204: None}, operation_id="lms_material_delete")
    def delete(self, request, material_id: int):
        services.delete_material(material_id, request.principal)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CourseMaterialDownloadView(APIView):
    permission_classes = [RequireLmsPermission("lms.material.view")]

    @extend_schema(
        responses={
            (200, "application/octet-stream"): OpenApiTypes.BINARY,
            404: OpenApiResponse(description="Material file not found or access denied."),
        },
        operation_id="lms_material_download",
    )
    def get(self, request, material_id: int):
        material = selectors.get_material_detail(material_id, request.principal)
        if not material or not material.file_attachment:
            raise NotFoundError("Material file not found or access denied.")
        try:
            raw_name = os.path.basename(material.file_attachment.name)
            filename = sanitise_filename(raw_name, fallback="material_download")
            file_handle = material.file_attachment.open("rb")
        except (OSError, ValueError) as e:
            raise NotFoundError("Material file could not be read.") from e

        disposition = f'attachment; filename="{filename}"; filename*=UTF-8\'\'{quote(filename)}'
        response = FileResponse(file_handle, content_type="application/octet-stream")
        response["Content-Disposition"] = disposition
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store"
        return response


class CourseAnnouncementListCreateView(APIView):
    serializer_class = CourseAnnouncementSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [RequireLmsPermission("lms.announcement.create")()]
        return [RequireLmsPermission("lms.announcement.view")()]

    @extend_schema(
        responses=CourseAnnouncementSerializer(many=True),
        operation_id="lms_announcement_list",
    )
    def get(self, request):
        course_id = request.query_params.get("course_id")
        if not course_id:
            raise BadRequestError("course_id query param is required.")
        try:
            c_id = int(course_id)
        except (ValueError, TypeError) as e:
            raise BadRequestError("course_id must be an integer.") from e
        announcements = selectors.list_announcements(c_id, request.principal)
        return Response(CourseAnnouncementSerializer(announcements, many=True).data)

    @extend_schema(
        request=CourseAnnouncementSerializer,
        responses=CourseAnnouncementSerializer,
        operation_id="lms_announcement_create",
    )
    def post(self, request):
        course_id = request.data.get("course_id")
        title = request.data.get("title")
        content = request.data.get("content")
        if not course_id or not title or not content:
            raise BadRequestError("course_id, title, and content are required.")
        try:
            announcement = services.post_announcement(
                course_id=int(course_id),
                title=title,
                content=content,
                principal=request.principal,
            )
        except ValueError as e:
            raise BadRequestError(str(e)) from e
        return Response(
            CourseAnnouncementSerializer(announcement).data,
            status=status.HTTP_201_CREATED,
        )


class CourseAnnouncementDetailView(APIView):
    serializer_class = CourseAnnouncementSerializer

    def get_permissions(self):
        if self.request.method in ("PATCH", "PUT"):
            return [RequireLmsPermission("lms.announcement.update")()]
        return [RequireLmsPermission("lms.announcement.delete")()]

    @extend_schema(
        request=CourseAnnouncementSerializer,
        responses=CourseAnnouncementSerializer,
        operation_id="lms_announcement_update",
    )
    def patch(self, request, announcement_id: int):
        from modules.lms.models import CourseAnnouncement

        ann = CourseAnnouncement.objects.filter(id=announcement_id).first()
        if not ann:
            raise NotFoundError("Announcement not found.")
        title = request.data.get("title", ann.title)
        content = request.data.get("content", ann.content)
        ann.title = title
        ann.content = content
        ann.save()
        return Response(CourseAnnouncementSerializer(ann).data)

    @extend_schema(responses={204: None}, operation_id="lms_announcement_delete")
    def delete(self, request, announcement_id: int):
        services.delete_announcement(announcement_id, request.principal)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AssignmentListCreateView(APIView):
    serializer_class = AssignmentSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [RequireLmsPermission("lms.assignment.create")()]
        return [RequireLmsPermission("lms.assignment.view")()]

    @extend_schema(responses=AssignmentSerializer(many=True), operation_id="lms_assignment_list")
    def get(self, request):
        course_id = request.query_params.get("course_id")
        if not course_id:
            raise BadRequestError("course_id query param is required.")
        try:
            c_id = int(course_id)
        except (ValueError, TypeError) as e:
            raise BadRequestError("course_id must be an integer.") from e
        assignments = selectors.list_assignments(c_id, request.principal)
        return Response(AssignmentSerializer(assignments, many=True).data)

    @extend_schema(
        request=AssignmentSerializer,
        responses=AssignmentSerializer,
        operation_id="lms_assignment_create",
    )
    def post(self, request):
        serializer = AssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            assignment = services.create_assignment(
                course_id=serializer.validated_data["course_id"],
                title=serializer.validated_data["title"],
                instructions=serializer.validated_data["instructions"],
                points_possible=serializer.validated_data["points_possible"],
                submission_type=serializer.validated_data["submission_type"],
                due_date=serializer.validated_data["due_date"],
                release_date=serializer.validated_data.get("release_date"),
                principal=request.principal,
            )
        except ValueError as e:
            raise BadRequestError(str(e)) from e
        return Response(AssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)


class AssignmentDetailView(APIView):
    serializer_class = AssignmentSerializer

    def get_permissions(self):
        if self.request.method in ("PATCH", "PUT"):
            return [RequireLmsPermission("lms.assignment.update")()]
        if self.request.method == "DELETE":
            return [RequireLmsPermission("lms.assignment.delete")()]
        return [RequireLmsPermission("lms.assignment.view")()]

    @extend_schema(responses=AssignmentSerializer, operation_id="lms_assignment_retrieve")
    def get(self, request, assignment_id: int):
        assignment = selectors.get_assignment_detail(assignment_id, request.principal)
        if not assignment:
            raise NotFoundError("Assignment not found or unreleased.")
        return Response(AssignmentSerializer(assignment).data)

    @extend_schema(
        request=AssignmentSerializer,
        responses=AssignmentSerializer,
        operation_id="lms_assignment_update",
    )
    def patch(self, request, assignment_id: int):
        serializer = AssignmentSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        assignment = selectors.get_assignment_detail(assignment_id, request.principal)
        if not assignment:
            raise NotFoundError("Assignment not found.")
        try:
            updated = services.update_assignment(
                assignment_id=assignment_id,
                title=serializer.validated_data.get("title", assignment.title),
                instructions=serializer.validated_data.get("instructions", assignment.instructions),
                points_possible=serializer.validated_data.get(
                    "points_possible", assignment.points_possible
                ),
                submission_type=serializer.validated_data.get(
                    "submission_type", assignment.submission_type
                ),
                due_date=serializer.validated_data.get("due_date", assignment.due_date),
                release_date=serializer.validated_data.get("release_date", assignment.release_date),
                principal=request.principal,
            )
        except ValueError as e:
            raise BadRequestError(str(e)) from e
        return Response(AssignmentSerializer(updated).data)

    @extend_schema(responses={204: None}, operation_id="lms_assignment_delete")
    def delete(self, request, assignment_id: int):
        services.delete_assignment(assignment_id, request.principal)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AssignmentPublishView(APIView):
    permission_classes = [RequireLmsPermission("lms.assignment.publish")]
    serializer_class = AssignmentSerializer

    @extend_schema(responses=AssignmentSerializer, operation_id="lms_assignment_publish")
    def post(self, request, assignment_id: int):
        release_date = request.data.get("release_date")
        try:
            assignment = services.publish_assignment(
                assignment_id=assignment_id,
                release_date=release_date,
                principal=request.principal,
            )
        except ValueError as e:
            raise BadRequestError(str(e)) from e
        return Response(AssignmentSerializer(assignment).data)


class SubmissionListCreateView(APIView):
    serializer_class = AssignmentSubmissionSerializer
    throttle_scope = "lms_submission"

    def get_throttles(self):
        if self.request.method == "POST":
            return super().get_throttles()
        return []

    def get_permissions(self):
        if self.request.method == "POST":
            return [RequireLmsPermission("lms.submission.create")()]
        return [RequireLmsPermission("lms.submission.view")()]

    @extend_schema(
        responses=AssignmentSubmissionSerializer(many=True),
        operation_id="lms_submission_list",
    )
    def get(self, request, assignment_id: int):
        submissions = selectors.list_course_submissions(assignment_id, request.principal)
        return Response(AssignmentSubmissionSerializer(submissions, many=True).data)

    @extend_schema(
        request=AssignmentSubmissionSerializer,
        responses=AssignmentSubmissionSerializer,
        operation_id="lms_submission_create",
    )
    def post(self, request, assignment_id: int):
        submission_type = request.data.get("submission_type")
        content_text = request.data.get("content_text")
        content_link = request.data.get("content_link")
        file_attachment = request.FILES.get("file_attachment")
        try:
            submission = services.submit_assignment(
                assignment_id=assignment_id,
                submission_type=submission_type,
                content_text=content_text,
                content_link=content_link,
                file_attachment=file_attachment,
                principal=request.principal,
            )
        except ValueError as e:
            raise BadRequestError(str(e)) from e
        return Response(
            AssignmentSubmissionSerializer(submission).data,
            status=status.HTTP_201_CREATED,
        )


class SubmissionDetailView(APIView):
    permission_classes = [RequireLmsPermission("lms.submission.view")]
    serializer_class = AssignmentSubmissionSerializer

    @extend_schema(
        responses=AssignmentSubmissionSerializer,
        operation_id="lms_submission_retrieve",
    )
    def get(self, request, submission_id: int):
        submission = selectors.get_submission_by_id(submission_id, request.principal)
        if not submission:
            raise NotFoundError("Submission not found or access denied.")
        return Response(AssignmentSubmissionSerializer(submission).data)


class AssignmentSubmissionDownloadView(APIView):
    permission_classes = [RequireLmsPermission("lms.submission.view")]

    @extend_schema(
        responses={
            (200, "application/octet-stream"): OpenApiTypes.BINARY,
            404: OpenApiResponse(description="Submission file not found or access denied."),
        },
        operation_id="lms_submission_download",
    )
    def get(self, request, submission_id: int):
        submission = selectors.get_submission_by_id(submission_id, request.principal)
        if not submission or not submission.file_attachment:
            raise NotFoundError("Submission file not found or access denied.")
        try:
            raw_name = os.path.basename(submission.file_attachment.name)
            filename = sanitise_filename(raw_name, fallback="submission_download")
            file_handle = submission.file_attachment.open("rb")
        except (OSError, ValueError) as e:
            raise NotFoundError("Submission file could not be read.") from e

        disposition = f'attachment; filename="{filename}"; filename*=UTF-8\'\'{quote(filename)}'
        response = FileResponse(file_handle, content_type="application/octet-stream")
        response["Content-Disposition"] = disposition
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store"
        return response


class GradeSubmissionView(APIView):
    serializer_class = SubmissionGradeSerializer
    throttle_scope = "lms_grade"

    def get_throttles(self):
        if self.request.method in ("POST", "PUT", "PATCH"):
            return super().get_throttles()
        return []

    def get_permissions(self):
        if self.request.method == "POST":
            return [
                RequireLmsPermission("lms.grade.create")(),
                RequireLmsPermission("lms.submission.review")(),
            ]
        if self.request.method in ("PATCH", "PUT"):
            return [
                RequireLmsPermission("lms.grade.update")(),
                RequireLmsPermission("lms.submission.review")(),
            ]
        return [RequireLmsPermission("lms.grade.view")()]

    @extend_schema(responses=SubmissionGradeSerializer, operation_id="lms_grade_retrieve")
    def get(self, request, submission_id: int):
        grade = selectors.get_submission_grade(submission_id, request.principal)
        if not grade:
            raise NotFoundError("Grade not found or unreleased.")
        return Response(SubmissionGradeSerializer(grade).data)

    @extend_schema(
        request=SubmissionGradeSerializer,
        responses=SubmissionGradeSerializer,
        operation_id="lms_grade_create",
    )
    def post(self, request, submission_id: int):
        points = request.data.get("points_awarded")
        feedback = request.data.get("feedback_text", "")
        if points is None:
            raise BadRequestError("points_awarded is required.")
        try:
            grade = services.grade_submission(
                submission_id=submission_id,
                points_awarded=points,
                feedback_text=feedback,
                principal=request.principal,
            )
        except ValueError as e:
            raise BadRequestError(str(e)) from e
        return Response(SubmissionGradeSerializer(grade).data)

    @extend_schema(
        request=SubmissionGradeSerializer,
        responses=SubmissionGradeSerializer,
        operation_id="lms_grade_update",
    )
    def patch(self, request, submission_id: int):
        points = request.data.get("points_awarded")
        feedback = request.data.get("feedback_text", "")
        reason = request.data.get("reason", "")
        if points is None:
            raise BadRequestError("points_awarded is required.")
        try:
            grade = services.update_grade(
                submission_id=submission_id,
                points_awarded=points,
                feedback_text=feedback,
                reason=reason,
                principal=request.principal,
            )
        except ValueError as e:
            raise BadRequestError(str(e)) from e
        return Response(SubmissionGradeSerializer(grade).data)


class PublishGradesView(APIView):
    permission_classes = [RequireLmsPermission("lms.grade.publish")]
    serializer_class = PublishGradesResponseSerializer

    @extend_schema(
        request=PublishGradesRequestSerializer,
        responses=PublishGradesResponseSerializer,
        operation_id="lms_grade_publish",
    )
    def post(self, request, assignment_id: int):
        submission_ids = request.data.get("submission_ids")
        try:
            count = services.publish_grades(
                assignment_id=assignment_id,
                submission_ids=submission_ids,
                principal=request.principal,
            )
        except ValueError as e:
            raise BadRequestError(str(e)) from e
        return Response({"published_count": count})


class AssignmentGradesListView(APIView):
    permission_classes = [RequireLmsPermission("lms.grade.view")]
    serializer_class = SubmissionGradeSerializer

    @extend_schema(
        responses=SubmissionGradeSerializer(many=True),
        operation_id="lms_assignment_grades_list",
    )
    def get(self, request, assignment_id: int):
        grades = selectors.list_course_grades(assignment_id, request.principal)
        return Response(SubmissionGradeSerializer(grades, many=True).data)


class SubmissionGradeDetailView(APIView):
    permission_classes = [RequireLmsPermission("lms.grade.view")]
    serializer_class = SubmissionGradeSerializer

    @extend_schema(
        responses=SubmissionGradeSerializer,
        operation_id="lms_submission_grade_detail",
    )
    def get(self, request, submission_id: int):
        grade = selectors.get_submission_grade(submission_id, request.principal)
        if not grade:
            raise NotFoundError("Grade not found or unreleased.")
        return Response(SubmissionGradeSerializer(grade).data)


class GradeAuditHistoryView(APIView):
    permission_classes = [RequireLmsPermission("lms.grade.view")]
    serializer_class = GradeChangeAuditSerializer

    @extend_schema(
        responses=GradeChangeAuditSerializer(many=True),
        operation_id="lms_grade_audit_history",
    )
    def get(self, request, submission_id: int):
        audits = selectors.get_grade_audit_history(submission_id, request.principal)
        return Response(GradeChangeAuditSerializer(audits, many=True).data)
