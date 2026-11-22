import os
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.http import FileResponse
from django.utils import timezone
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
from modules.lms.domain.constants import ContentStatus, GradeStatus, Role
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


def is_course_staff(request, course_id: int | None) -> bool:
    if is_request_staff(request):
        return True
    if not course_id:
        return False
    role = get_resolved_role(request, course_id)
    return role in (Role.INSTRUCTOR, Role.TA)


def is_course_instructor(request, course_id: int | None) -> bool:
    if is_request_staff(request):
        return True
    if not course_id:
        return False
    return get_resolved_role(request, course_id) == Role.INSTRUCTOR


class CourseViewSet(viewsets.ModelViewSet):
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_id = get_request_user_id(self.request)
        if is_request_staff(self.request):
            return Course.objects.all()
        return get_user_courses(user_id) if user_id else Course.objects.none()

    def perform_create(self, serializer):
        if not is_request_staff(self.request):
            raise PermissionDenied("Only institutional administrators can create new courses.")
        serializer.save()

    def update(self, request, *args, **kwargs):
        course = self.get_object()
        if not is_course_instructor(request, course.id):
            raise PermissionDenied("Only instructors and staff can modify course workspace details.")
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        course = self.get_object()
        if not is_course_instructor(request, course.id):
            raise PermissionDenied("Only instructors and staff can modify course workspace details.")
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        course = self.get_object()
        if not is_course_instructor(request, course.id):
            raise PermissionDenied("Only instructors and staff can delete a course.")
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["get"])
    def sections(self, request, pk=None):
        course = self.get_object()
        role = get_resolved_role(request, course.id)
        if not role and not is_request_staff(request):
            raise PermissionDenied("Access to course workspace is prohibited for unlinked users.")
        sections = get_sections_for_course(course.id)
        return Response(ModuleSectionSerializer(sections, many=True).data)

    @action(detail=True, methods=["get"])
    def announcements(self, request, pk=None):
        course = self.get_object()
        role = get_resolved_role(request, course.id)
        if not role and not is_request_staff(request):
            raise PermissionDenied("Access to course announcements is prohibited for unlinked users.")
        announcements = get_announcements_for_course(course.id)
        return Response(AnnouncementSerializer(announcements, many=True).data)

    @action(detail=True, methods=["get"])
    def assignments(self, request, pk=None):
        course = self.get_object()
        role = get_resolved_role(request, course.id)
        if not role and not is_request_staff(request):
            raise PermissionDenied("Access to course assignments is prohibited for unlinked users.")
        is_staff_user = is_request_staff(request) or role in (Role.INSTRUCTOR, Role.TA)
        assignments = get_assignments_for_course(course.id, is_staff=is_staff_user)
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
    serializer_class = ModuleSectionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_id = get_request_user_id(self.request)
        if is_request_staff(self.request):
            return ModuleSection.objects.all()
        if not user_id:
            return ModuleSection.objects.none()
        user_course_ids = CourseMembership.objects.filter(
            user_id=user_id, is_active=True
        ).values_list("course_id", flat=True)
        return ModuleSection.objects.filter(course_id__in=user_course_ids)

    def create(self, request, *args, **kwargs):
        course_id = request.data.get("course")
        if not is_course_instructor(request, course_id):
            raise PermissionDenied("Only instructors and staff can create module sections.")
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not is_course_instructor(request, instance.course_id):
            raise PermissionDenied("Only instructors and staff can modify module sections.")
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not is_course_instructor(request, instance.course_id):
            raise PermissionDenied("Only instructors and staff can modify module sections.")
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not is_course_instructor(request, instance.course_id):
            raise PermissionDenied("Only instructors and staff can delete module sections.")
        return super().destroy(request, *args, **kwargs)


class CourseMaterialViewSet(viewsets.ModelViewSet):
    serializer_class = CourseMaterialSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_id = get_request_user_id(self.request)
        if is_request_staff(self.request):
            return CourseMaterial.objects.all()
        if not user_id:
            return CourseMaterial.objects.none()

        memberships = CourseMembership.objects.filter(user_id=user_id, is_active=True)
        staff_course_ids = list(
            memberships.filter(role__in=[Role.INSTRUCTOR, Role.TA]).values_list("course_id", flat=True)
        )
        learner_course_ids = list(
            memberships.filter(role__in=[Role.STUDENT, Role.OBSERVER]).values_list("course_id", flat=True)
        )

        now = timezone.now()
        return CourseMaterial.objects.filter(
            Q(section__course_id__in=staff_course_ids)
            | (
                Q(section__course_id__in=learner_course_ids)
                & Q(status=ContentStatus.PUBLISHED)
                & (Q(release_date__isnull=True) | Q(release_date__lte=now))
            )
        )

    def create(self, request, *args, **kwargs):
        section_id = request.data.get("section")
        section = ModuleSection.objects.filter(id=section_id).first() if section_id else None
        course_id = section.course_id if section else None
        if not is_course_instructor(request, course_id):
            raise PermissionDenied("Only instructors and staff can create course materials.")
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not is_course_instructor(request, instance.section.course_id):
            raise PermissionDenied("Only instructors and staff can modify course materials.")
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not is_course_instructor(request, instance.section.course_id):
            raise PermissionDenied("Only instructors and staff can modify course materials.")
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not is_course_instructor(request, instance.section.course_id):
            raise PermissionDenied("Only instructors and staff can delete course materials.")
        return super().destroy(request, *args, **kwargs)


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
    serializer_class = AssignmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_id = get_request_user_id(self.request)
        if is_request_staff(self.request):
            return Assignment.objects.all()
        if not user_id:
            return Assignment.objects.none()

        memberships = CourseMembership.objects.filter(user_id=user_id, is_active=True)
        staff_course_ids = list(
            memberships.filter(role__in=[Role.INSTRUCTOR, Role.TA]).values_list("course_id", flat=True)
        )
        learner_course_ids = list(
            memberships.filter(role__in=[Role.STUDENT, Role.OBSERVER]).values_list("course_id", flat=True)
        )

        now = timezone.now()
        return Assignment.objects.filter(
            Q(course_id__in=staff_course_ids)
            | (
                Q(course_id__in=learner_course_ids)
                & Q(status=ContentStatus.PUBLISHED)
                & (Q(release_date__isnull=True) | Q(release_date__lte=now))
            )
        )

    def create(self, request, *args, **kwargs):
        course_id = request.data.get("course")
        if not is_course_instructor(request, course_id):
            raise PermissionDenied("Only instructors and staff can create assignments.")
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not is_course_instructor(request, instance.course_id):
            raise PermissionDenied("Only instructors and staff can modify assignments.")
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not is_course_instructor(request, instance.course_id):
            raise PermissionDenied("Only instructors and staff can modify assignments.")
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not is_course_instructor(request, instance.course_id):
            raise PermissionDenied("Only instructors and staff can delete assignments.")
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        assignment = self.get_object()
        course_id = assignment.course_id
        role = get_resolved_role(request, course_id)
        if role != Role.STUDENT:
            raise PermissionDenied("Only enrolled students can submit assignments.")
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
        course_id = assignment.course_id
        role = get_resolved_role(request, course_id)
        if role == Role.OBSERVER or not role:
            raise PermissionDenied("Observers are strictly forbidden from viewing student submissions.")
        user_id = get_request_user_id(request)
        if is_request_staff(request) or role in (Role.INSTRUCTOR, Role.TA):
            subs = get_grading_queue(assignment.id)
        elif role == Role.STUDENT:
            subs = get_student_submissions(assignment.id, user_id)
        else:
            raise PermissionDenied("You do not have permission to view submissions.")
        return Response(SubmissionSerializer(subs, many=True).data)


class SubmissionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SubmissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_id = get_request_user_id(self.request)
        if is_request_staff(self.request):
            return Submission.objects.all()
        if not user_id:
            return Submission.objects.none()

        memberships = CourseMembership.objects.filter(user_id=user_id, is_active=True)
        staff_course_ids = list(
            memberships.filter(role__in=[Role.INSTRUCTOR, Role.TA]).values_list("course_id", flat=True)
        )
        student_course_ids = list(
            memberships.filter(role=Role.STUDENT).values_list("course_id", flat=True)
        )

        return Submission.objects.filter(
            Q(assignment__course_id__in=staff_course_ids)
            | (
                Q(assignment__course_id__in=student_course_ids)
                & Q(student_user_id=user_id)
            )
        )

    def retrieve(self, request, *args, **kwargs):
        submission = self.get_object()
        course_id = submission.assignment.course_id
        role = get_resolved_role(request, course_id)
        if role == Role.OBSERVER or not role:
            raise PermissionDenied("Observers are strictly forbidden from viewing student submissions.")
        if role == Role.STUDENT and submission.student_user_id != get_request_user_id(request):
            raise PermissionDenied("Students can only view their own submissions.")
        serializer = self.get_serializer(submission)
        return Response(serializer.data)

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
    serializer_class = GradeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_id = get_request_user_id(self.request)
        if is_request_staff(self.request):
            return Grade.objects.all()
        if not user_id:
            return Grade.objects.none()

        memberships = CourseMembership.objects.filter(user_id=user_id, is_active=True)
        staff_course_ids = list(
            memberships.filter(role__in=[Role.INSTRUCTOR, Role.TA]).values_list("course_id", flat=True)
        )
        student_course_ids = list(
            memberships.filter(role=Role.STUDENT).values_list("course_id", flat=True)
        )

        qs = Grade.objects.filter(
            Q(submission__assignment__course_id__in=staff_course_ids)
            | (
                Q(submission__assignment__course_id__in=student_course_ids)
                & Q(status=GradeStatus.RELEASED)
                & Q(submission__student_user_id=user_id)
            )
        )

        submission_id = self.request.query_params.get("submission")
        if submission_id and str(submission_id).isdigit():
            qs = qs.filter(submission_id=int(submission_id))

        return qs

    def retrieve(self, request, *args, **kwargs):
        grade = self.get_object()
        course_id = grade.submission.assignment.course_id
        role = get_resolved_role(request, course_id)
        if role == Role.OBSERVER or not role:
            raise PermissionDenied("Observers are strictly forbidden from viewing student grades.")
        if role == Role.STUDENT:
            if grade.status != GradeStatus.RELEASED:
                raise PermissionDenied("Draft grades are not visible to students.")
            if grade.submission.student_user_id != get_request_user_id(request):
                raise PermissionDenied("Students can only view their own grades.")
        serializer = self.get_serializer(grade)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def audit_logs(self, request, pk=None):
        grade = self.get_object()
        course_id = grade.submission.assignment.course_id
        role = get_resolved_role(request, course_id)
        if role not in (Role.INSTRUCTOR, Role.TA) and not is_request_staff(request):
            raise PermissionDenied("Only instructors, TAs, and staff can view grade audit history.")
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
