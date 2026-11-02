from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

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
    release_grade,
    save_draft_grade,
    submit_assignment,
)


def get_request_user_id(request) -> int | None:
    if not (request.user and request.user.is_authenticated):
        return None
    uid = getattr(request.user, "user_id", None)
    if isinstance(uid, int):
        return uid
    uid = getattr(request.user, "id", None)
    if isinstance(uid, int):
        return uid
    if uid is not None and str(uid).isdigit():
        return int(uid)
    return None


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


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        assignment = self.get_object()
        user_id = get_request_user_id(request)
        submission = submit_assignment(
            assignment_id=assignment.id,
            student_user_id=user_id,
            submission_type=request.data.get("submission_type", "file"),
            content_text=request.data.get("content_text", ""),
            file_storage_key=request.data.get("file_storage_key", ""),
            link_url=request.data.get("link_url", ""),
        )
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
        assessor_role = request.data.get("role", Role.TA)

        if grade_action == "release":
            grade = release_grade(
                submission_id=submission.id,
                assessor_user_id=user_id,
                assessor_role=assessor_role,
                points_awarded=points,
                feedback_text=feedback,
                reason=reason or "initial grade release",
            )
        else:
            grade = save_draft_grade(
                submission_id=submission.id,
                assessor_user_id=user_id,
                assessor_role=assessor_role,
                points_awarded=points,
                feedback_text=feedback,
            )
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
