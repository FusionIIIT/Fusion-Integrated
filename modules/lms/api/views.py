import os
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import FileResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from modules.lms.api.permissions import (
    get_course_id_from_request_or_view,
    get_request_user_id,
    get_resolved_role,
)
from modules.lms.api.serializers import (
    AnnouncementSerializer,
    AssignmentSerializer,
    CourseMaterialSerializer,
    CourseMembershipSerializer,
    CourseSerializer,
    GradeAuditLogSerializer,
    GradeSerializer,
    ModuleSectionSerializer,
    ScheduledReleaseSerializer,
    SubmissionSerializer,
)
from modules.lms.domain.constants import Role
from modules.lms.models import (
    Announcement,
    Assignment,
    Course,
    CourseMaterial,
    CourseMembership,
    Grade,
    ModuleSection,
    ScheduledRelease,
    Submission,
)
from modules.lms.selectors import (
    get_announcements_for_course,
    get_assignments_for_course,
    get_grade_audit_logs,
    get_grading_queue,
    get_sections_for_course,
    get_student_submissions,
    get_user_courses,
)
from modules.lms.services import (
    get_file_path,
    release_grade,
    save_draft_grade,
    save_uploaded_file,
    submit_assignment,
)


def is_request_staff(request) -> bool:
    if not request.user:
        return False
    if getattr(request.user, "kind", None) == "staff":
        return True
    return bool(getattr(request.user, "is_staff", False))


class CourseViewSet(viewsets.ModelViewSet):
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_id = get_request_user_id(self.request)
        if is_request_staff(self.request):
            return Course.objects.all()
        return get_user_courses(user_id) if user_id else Course.objects.none()

    @action(detail=True, methods=["get"])
    def sections(self, request, pk=None):
        course = self.get_object()
        sections = get_sections_for_course(course.id)
        return Response(ModuleSectionSerializer(sections, many=True).data)

    @action(detail=True, methods=["get"])
    def announcements(self, request, pk=None):
        course = self.get_object()
        announcements = get_announcements_for_course(course.id)
        return Response(AnnouncementSerializer(announcements, many=True).data)

    @action(detail=True, methods=["get"])
    def assignments(self, request, pk=None):
        course = self.get_object()
        assignments = get_assignments_for_course(course.id, is_staff=is_request_staff(request))
        return Response(AssignmentSerializer(assignments, many=True).data)


class CourseMembershipViewSet(viewsets.ModelViewSet):
    queryset = CourseMembership.objects.all()
    serializer_class = CourseMembershipSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        role = serializer.validated_data.get("role")
        if role == Role.STUDENT:
            raise PermissionDenied(
                "Direct student registration in LMS is prohibited. Student enrollment must originate from the institutional AcademicAdapter projection."
            )
        serializer.save()


class ModuleSectionViewSet(viewsets.ModelViewSet):
    queryset = ModuleSection.objects.all()
    serializer_class = ModuleSectionSerializer
    permission_classes = [IsAuthenticated]


class CourseMaterialViewSet(viewsets.ModelViewSet):
    queryset = CourseMaterial.objects.all()
    serializer_class = CourseMaterialSerializer
    permission_classes = [IsAuthenticated]


class AnnouncementViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        course = serializer.validated_data.get("course")
        role = get_resolved_role(self.request, course.id if course else None)
        if role != Role.INSTRUCTOR and not is_request_staff(self.request):
            raise PermissionDenied(
                "TA announcement creation is pending policy clarification (ISS-LMS-002). Only instructors can publish announcements."
            )
        serializer.save(
            author_user_id=get_request_user_id(self.request) or 1,
            author_role=Role.INSTRUCTOR,
        )


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        assignment = self.get_object()
        user_id = get_request_user_id(request)
        try:
            submission = submit_assignment(
                assignment_id=assignment.id,
                student_user_id=user_id,
                submission_type=request.data.get("submission_type", "file"),
                content_text=request.data.get("content_text", ""),
                file_storage_key=request.data.get("file_storage_key", ""),
                link_url=request.data.get("link_url", ""),
            )
        except ValidationError as e:
            msg = e.message if hasattr(e, "message") else str(e)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
        return Response(SubmissionSerializer(submission).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def submissions(self, request, pk=None):
        assignment = self.get_object()
        user_id = get_request_user_id(request)
        if is_request_staff(request):
            subs = get_grading_queue(assignment.id)
        else:
            subs = get_student_submissions(assignment.id, user_id)
        return Response(SubmissionSerializer(subs, many=True).data)


class SubmissionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"])
    def grade(self, request, pk=None):
        submission = self.get_object()
        user_id = get_request_user_id(request)
        grade_action = request.data.get("action", "draft")
        points = request.data.get("points")
        feedback = request.data.get("feedback", "")
        reason = request.data.get("reason", "")
        course_id = submission.assignment.course_id
        resolved_role = get_resolved_role(request, course_id) or request.data.get("role", Role.TA)

        try:
            if grade_action == "release":
                grade = release_grade(
                    submission_id=submission.id,
                    assessor_user_id=user_id,
                    assessor_role=resolved_role,
                    points_awarded=points,
                    feedback_text=feedback,
                    reason=reason or "initial grade release",
                )
            else:
                grade = save_draft_grade(
                    submission_id=submission.id,
                    assessor_user_id=user_id,
                    assessor_role=resolved_role,
                    points_awarded=points,
                    feedback_text=feedback,
                )
        except PermissionDenied as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        return Response(GradeSerializer(grade).data)


class GradeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Grade.objects.all()
    serializer_class = GradeSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["get"])
    def audit_logs(self, request, pk=None):
        grade = self.get_object()
        logs = get_grade_audit_logs(grade.id)
        return Response(GradeAuditLogSerializer(logs, many=True).data)


class ScheduledReleaseViewSet(viewsets.ModelViewSet):
    queryset = ScheduledRelease.objects.all()
    serializer_class = ScheduledReleaseSerializer
    permission_classes = [IsAuthenticated]


class FileViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="upload")
    def upload(self, request):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"detail": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)
        content_bytes = file_obj.read()
        storage_key = save_uploaded_file(file_obj.name, content_bytes)
        return Response(
            {
                "storage_key": storage_key,
                "filename": file_obj.name,
                "size": len(content_bytes),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"], url_path="download")
    def download(self, request):
        key = request.query_params.get("key")
        if not key:
            return Response({"detail": "Missing key parameter."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            path = get_file_path(key)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(open(path, "rb"), as_attachment=True, filename=os.path.basename(path))
