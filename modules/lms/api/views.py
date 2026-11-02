from __future__ import annotations

from django.db.models import Q
from django.http import FileResponse
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import DomainError, NotFoundError
from modules.lms.api import permissions as p
from modules.lms.api import serializers as s
from modules.lms.integrations.registration import RegistrationSourceUnavailable
from modules.lms.models import (
    Assignment,
    AssignmentSubmission,
    CourseMaterial,
    SubmissionGrade,
)
from modules.lms.selectors import content as selectors
from modules.lms.services import access, content


class CourseSourceUnavailable(DomainError):
    code = "course_registration_unavailable"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    message = "Course registration data is temporarily unavailable."


def _course(actor, course_id):
    try:
        return access.course_context(actor, course_id)
    except RegistrationSourceUnavailable as exc:
        raise CourseSourceUnavailable(str(exc)) from exc


def _actor(request):
    return request.principal


@extend_schema(responses=s.CourseSerializer(many=True))
class CourseListView(APIView):
    permission_classes = p.allow(p.P_COURSE)

    def get(self, request):
        try:
            rows = access.visible_courses(_actor(request))
        except RegistrationSourceUnavailable as exc:
            raise CourseSourceUnavailable(str(exc)) from exc
        return Response({"results": s.CourseSerializer(rows, many=True).data})


@extend_schema(responses=s.CourseSerializer)
class CourseDetailView(APIView):
    permission_classes = p.allow(p.P_COURSE)

    def get(self, request, course_id):
        ref, course = _course(_actor(request), course_id)
        return Response(s.CourseSerializer(access._course_data(ref, course)).data)


@extend_schema(request=s.CourseDetailsWriteSerializer, responses=s.CourseSerializer)
class CourseDetailsView(APIView):
    permission_classes = p.allow(p.P_COURSE_MANAGE)

    def patch(self, request, course_id):
        ref, course = _course(_actor(request), course_id)
        payload = s.CourseDetailsWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        content.update_course(course=course, ref=ref, **payload.validated_data)
        return Response(s.CourseSerializer(access._course_data(ref, course)).data)


@extend_schema(request=s.SectionWriteSerializer, responses=s.SectionSerializer(many=True))
class SectionListCreateView(APIView):
    def get_permissions(self):
        code = p.P_COURSE if self.request.method == "GET" else p.P_COURSE_MANAGE
        return [permission() for permission in p.allow(code)]

    def get(self, request, course_id):
        _ref, course = _course(_actor(request), course_id)
        return Response({"results": s.SectionSerializer(
            selectors.sections(course.pk), many=True).data})

    def post(self, request, course_id):
        ref, course = _course(_actor(request), course_id)
        payload = s.SectionWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = content.create_section(course=course, ref=ref, **payload.validated_data)
        return Response(s.SectionSerializer(row).data, status=status.HTTP_201_CREATED)


class MaterialListCreateView(APIView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_permissions(self):
        code = p.P_MATERIAL if self.request.method == "GET" else p.P_MATERIAL_MANAGE
        return [permission() for permission in p.allow(code)]

    @extend_schema(responses=s.MaterialSerializer(many=True))
    def get(self, request, course_id):
        ref, course = _course(_actor(request), course_id)
        can_manage = ref.role == "faculty"
        rows = selectors.materials(course.pk, can_manage=can_manage)
        return Response({"results": s.MaterialSerializer(rows, many=True).data})

    @extend_schema(request=s.MaterialWriteSerializer, responses=s.MaterialSerializer)
    def post(self, request, course_id):
        ref, course = _course(_actor(request), course_id)
        payload = s.MaterialWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = content.save_material(course=course, ref=ref, actor=_actor(request),
                                    data=payload.validated_data)
        return Response(s.MaterialSerializer(row).data, status=status.HTTP_201_CREATED)


class MaterialUpdateView(APIView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    permission_classes = p.allow(p.P_MATERIAL_MANAGE)

    @extend_schema(request=s.MaterialWriteSerializer, responses=s.MaterialSerializer)
    def put(self, request, course_id, material_id):
        ref, course = _course(_actor(request), course_id)
        current = CourseMaterial.objects.filter(pk=material_id, course=course).first()
        if not current:
            raise NotFoundError("No such course material.")
        payload = s.MaterialWriteSerializer(current, data=request.data)
        payload.is_valid(raise_exception=True)
        row = content.save_material(course=course, ref=ref, actor=_actor(request),
                                    data=payload.validated_data, material_id=material_id)
        return Response(s.MaterialSerializer(row).data)


class MaterialDownloadView(APIView):
    permission_classes = p.allow(p.P_MATERIAL)

    @extend_schema(responses=OpenApiTypes.BINARY)
    def get(self, request, course_id, material_id):
        ref, course = _course(_actor(request), course_id)
        qs = CourseMaterial.objects.filter(pk=material_id, course=course)
        if ref.role != "faculty":
            qs = qs.filter(status="published").filter(
                Q(release_at__isnull=True) | Q(release_at__lte=timezone.now()))
        material = qs.first()
        if not material or not material.file:
            raise NotFoundError("No downloadable course material was found.")
        return FileResponse(material.file.open("rb"), as_attachment=True,
                            filename=material.title)


class AnnouncementListCreateView(APIView):
    def get_permissions(self):
        code = (p.P_ANNOUNCEMENT if self.request.method == "GET"
                else p.P_ANNOUNCEMENT_CREATE)
        return [permission() for permission in p.allow(code)]

    @extend_schema(responses=s.AnnouncementSerializer(many=True))
    def get(self, request, course_id):
        _ref, course = _course(_actor(request), course_id)
        rows = selectors.announcements(course.pk)
        return Response({"results": s.AnnouncementSerializer(rows, many=True).data})

    @extend_schema(request=s.AnnouncementWriteSerializer,
                   responses=s.AnnouncementSerializer)
    def post(self, request, course_id):
        ref, course = _course(_actor(request), course_id)
        payload = s.AnnouncementWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = content.post_announcement(course=course, ref=ref, actor=_actor(request),
                                        **payload.validated_data)
        return Response(s.AnnouncementSerializer(row).data, status=status.HTTP_201_CREATED)


class AssignmentListCreateView(APIView):
    def get_permissions(self):
        code = p.P_ASSIGNMENT if self.request.method == "GET" else p.P_ASSIGNMENT_MANAGE
        return [permission() for permission in p.allow(code)]

    @extend_schema(responses=s.AssignmentSerializer(many=True))
    def get(self, request, course_id):
        ref, course = _course(_actor(request), course_id)
        can_manage = ref.role == "faculty"
        rows = selectors.assignments(course.pk, can_manage=can_manage)
        return Response({"results": s.AssignmentSerializer(rows, many=True).data})

    @extend_schema(request=s.AssignmentWriteSerializer, responses=s.AssignmentSerializer)
    def post(self, request, course_id):
        ref, course = _course(_actor(request), course_id)
        payload = s.AssignmentWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = content.save_assignment(course=course, ref=ref, actor=_actor(request),
                                      data=payload.validated_data)
        return Response(s.AssignmentSerializer(row).data, status=status.HTTP_201_CREATED)


class AssignmentUpdatePublishView(APIView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    permission_classes = p.allow(p.P_ASSIGNMENT_MANAGE)

    @extend_schema(request=s.AssignmentWriteSerializer, responses=s.AssignmentSerializer)
    def put(self, request, course_id, assignment_id):
        ref, course = _course(_actor(request), course_id)
        payload = s.AssignmentWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = content.save_assignment(course=course, ref=ref, actor=_actor(request),
                                      data=payload.validated_data,
                                      assignment_id=assignment_id)
        return Response(s.AssignmentSerializer(row).data)


class AssignmentDownloadView(APIView):
    permission_classes = p.allow(p.P_ASSIGNMENT)

    @extend_schema(responses=OpenApiTypes.BINARY)
    def get(self, request, course_id, assignment_id):
        ref, course = _course(_actor(request), course_id)
        assignment = selectors.assignments(
            course.pk, can_manage=ref.role == "faculty").filter(
                pk=assignment_id).first()
        if not assignment or not assignment.file:
            raise NotFoundError("No downloadable course assignment was found.")
        return FileResponse(assignment.file.open("rb"), as_attachment=True,
                            filename=assignment.file.name.rsplit("/", 1)[-1])



class AssignmentPublishView(APIView):
    permission_classes = p.allow(p.P_ASSIGNMENT_PUBLISH)

    @extend_schema(request=None, responses=s.AssignmentSerializer)
    def post(self, request, course_id, assignment_id):
        ref, course = _course(_actor(request), course_id)
        row = content.publish_assignment(course=course, ref=ref,
                                         assignment_id=assignment_id)
        return Response(s.AssignmentSerializer(row).data)


class AssignmentSubmitView(APIView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    permission_classes = p.allow(p.P_SUBMIT)

    @extend_schema(request=s.SubmissionWriteSerializer,
                   responses=s.SubmissionSerializer)
    def post(self, request, course_id, assignment_id):
        ref, course = _course(_actor(request), course_id)
        assignment = Assignment.objects.filter(
            pk=assignment_id, course=course).first()
        if not assignment:
            raise NotFoundError("No such assignment.")
        payload = s.SubmissionWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = content.submit(assignment=assignment, ref=ref, actor=_actor(request),
                             **payload.validated_data)
        return Response(s.SubmissionSerializer(row).data, status=status.HTTP_201_CREATED)


class SubmissionListView(APIView):
    def get_permissions(self):
        return [p.MODULE()]

    @extend_schema(responses=s.SubmissionSerializer(many=True))
    def get(self, request, course_id):
        ref, course = _course(_actor(request), course_id)
        actor = _actor(request)
        if ref.role == "student" and actor.has_permission(p.P_SUBMISSION_SELF):
            rows = AssignmentSubmission.objects.filter(
                assignment__course=course, user_id=actor.user_id)
        elif ref.role in ("faculty", "teaching_assistant") and \
                actor.has_permission(p.P_SUBMISSION):
            rows = AssignmentSubmission.objects.filter(assignment__course=course)
        else:
            raise NotFoundError("No submission history is available.")
        assignment_id = request.query_params.get("assignment")
        if assignment_id:
            rows = rows.filter(assignment_id=assignment_id)
        return Response({"results": s.SubmissionSerializer(
            rows.select_related("assignment").order_by("-submitted_at"), many=True).data})


class GradeSubmissionView(APIView):
    permission_classes = p.allow(p.P_GRADE_MANAGE)

    @extend_schema(request=s.GradeWriteSerializer, responses=s.GradeSerializer)
    def post(self, request, course_id, submission_id):
        ref, course = _course(_actor(request), course_id)
        submission = AssignmentSubmission.objects.filter(
            pk=submission_id, assignment__course=course).select_related(
                "assignment").first()
        if not submission:
            raise NotFoundError("No such course submission.")
        payload = s.GradeWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        grade = content.grade_submission(submission=submission, ref=ref,
                                         actor=_actor(request),
                                         **payload.validated_data)
        return Response(s.GradeSerializer(grade).data)


class SubmissionDownloadView(APIView):
    permission_classes = [p.MODULE]

    @extend_schema(responses=OpenApiTypes.BINARY)
    def get(self, request, course_id, submission_id):
        ref, course = _course(_actor(request), course_id)
        submission = AssignmentSubmission.objects.filter(
            pk=submission_id, assignment__course=course).first()
        if not submission or not submission.file:
            raise NotFoundError("No downloadable submission was found.")
        actor = _actor(request)
        if ref.role == "student":
            if not actor.has_permission(p.P_SUBMISSION_SELF) or \
                    submission.user_id != actor.user_id:
                raise NotFoundError("No downloadable submission was found.")
        elif ref.role not in ("faculty", "teaching_assistant") or \
                not actor.has_permission(p.P_SUBMISSION):
            raise NotFoundError("No downloadable submission was found.")
        return FileResponse(submission.file.open("rb"), as_attachment=True,
                            filename=submission.file.name.rsplit("/", 1)[-1])


class GradeListReleaseView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [permission() for permission in p.allow(p.P_GRADE_RELEASE)]
        return [p.MODULE()]

    @extend_schema(responses=s.GradeSerializer(many=True))
    def get(self, request, course_id):
        ref, course = _course(_actor(request), course_id)
        actor = _actor(request)
        if ref.role == "student" and actor.has_permission(p.P_GRADE_SELF):
            rows = selectors.grades_for_student(actor.user_id).filter(
                submission__assignment__course=course)
        elif ref.role in ("faculty", "teaching_assistant") and \
                actor.has_permission(p.P_GRADE_MANAGE):
            if ref.role == "teaching_assistant":
                access.allow_ta(ref, "grade")
            rows = SubmissionGrade.objects.filter(
                submission__assignment__course=course).select_related(
                    "submission", "submission__assignment")
        else:
            raise NotFoundError("No grade data is available.")
        return Response({"results": s.GradeSerializer(rows, many=True).data})

    @extend_schema(request=s.GradeReleaseSerializer,
                   responses=s.GradeSerializer(many=True))
    def post(self, request, course_id):
        ref, course = _course(_actor(request), course_id)
        payload = s.GradeReleaseSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        rows = content.release_grades(course=course, ref=ref, actor=_actor(request),
                                      grade_ids=payload.validated_data["grade_ids"])
        return Response(s.GradeSerializer(rows, many=True).data)
