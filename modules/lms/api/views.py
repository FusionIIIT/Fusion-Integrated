"""API views for the LMS module."""
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import viewsets
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.lms.api.permissions import LmsPerm
from modules.lms.api.serializers import (
    AnnouncementSerializer,
    AssignmentSerializer,
    CourseMaterialSerializer,
    GradeSerializer,
    SubmissionSerializer,
)
from modules.lms.models import (
    Announcement,
    Assignment,
    CourseMaterial,
    Grade,
    Submission,
)
from modules.lms.selectors import scoping
from modules.lms.services import (
    grade_submission,
    publish_assignment,
    release_grade,
    submit_assignment,
)


def _actor(request):
    return getattr(request, "principal", None)


class CourseWorkspaceView(APIView):
    throttle_scope = "lms_submit"

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH", "POST"):
            return [LmsPerm("lms.course.manage")()]
        return [LmsPerm("lms.course.view")()]

    @extend_schema(
        tags=["lms"],
        summary="Get course workspace summary",
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request, course_id):
        actor = _actor(request)
        cid = scoping.course_for(actor, course_id)
        return Response({"course_id": cid, "title": f"Course {cid}"})

    @extend_schema(
        tags=["lms"],
        summary="Update course workspace settings",
        responses={200: OpenApiTypes.OBJECT},
    )
    def patch(self, request, course_id):
        actor = _actor(request)
        cid = scoping.course_for(actor, course_id)
        return Response({"course_id": cid, "status": "updated"})


class CourseMaterialViewSet(viewsets.ModelViewSet):
    serializer_class = CourseMaterialSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope = "lms_upload"

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [LmsPerm("lms.material.view")()]
        return [LmsPerm("lms.material.manage")()]

    def get_queryset(self):
        course_id = self.kwargs.get("course_id")
        if not course_id:
            return CourseMaterial.objects.none()
        actor = _actor(self.request)
        cid = scoping.course_for(actor, course_id)
        return scoping.materials_for_course(actor, cid)

    def perform_create(self, serializer):
        course_id = self.kwargs.get("course_id")
        actor = _actor(self.request)
        cid = scoping.course_for(actor, course_id)
        serializer.save(course_id=cid, user_id=actor.user_id if actor else 0)


class AnnouncementViewSet(viewsets.ModelViewSet):
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope = "lms_submit"

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [LmsPerm("lms.announcement.view")()]
        return [LmsPerm("lms.announcement.create")()]

    def get_queryset(self):
        course_id = self.kwargs.get("course_id")
        if not course_id:
            return Announcement.objects.none()
        actor = _actor(self.request)
        cid = scoping.course_for(actor, course_id)
        return scoping.announcements_for_course(actor, cid)

    def perform_create(self, serializer):
        course_id = self.kwargs.get("course_id")
        actor = _actor(self.request)
        cid = scoping.course_for(actor, course_id)
        serializer.save(course_id=cid, user_id=actor.user_id if actor else 0)


class AssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = AssignmentSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope = "lms_submit"

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [LmsPerm("lms.assignment.view")()]
        return [LmsPerm("lms.assignment.manage")()]

    def get_queryset(self):
        course_id = self.kwargs.get("course_id")
        if not course_id:
            return Assignment.objects.none()
        actor = _actor(self.request)
        cid = scoping.course_for(actor, course_id)
        return scoping.assignments_for_course(actor, cid)

    def perform_create(self, serializer):
        course_id = self.kwargs.get("course_id")
        actor = _actor(self.request)
        cid = scoping.course_for(actor, course_id)
        serializer.save(course_id=cid, user_id=actor.user_id if actor else 0)


class PublishAssignmentView(APIView):
    permission_classes = [LmsPerm("lms.assignment.manage")]
    throttle_scope = "lms_submit"

    @extend_schema(
        tags=["lms"],
        summary="Publish an assignment",
        request=None,
        responses={200: AssignmentSerializer},
    )
    def post(self, request, course_id, aid):
        actor = _actor(request)
        cid = scoping.course_for(actor, course_id)
        try:
            a = Assignment.objects.get(pk=int(aid), course_id=cid)
        except Assignment.DoesNotExist:
            raise NotFound("Assignment not found in course") from None
        try:
            a = publish_assignment(a.id, release_at=None)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        return Response(AssignmentSerializer(a).data)


class SubmitAssignmentView(APIView):
    permission_classes = [LmsPerm("lms.submission.create")]
    throttle_scope = "lms_submit"

    @extend_schema(
        tags=["lms"],
        summary="Submit an assignment attempt",
        request=SubmissionSerializer,
        responses={201: SubmissionSerializer},
    )
    def post(self, request, course_id, aid):
        actor = _actor(request)
        uid = actor.user_id if actor else 0
        cid = scoping.course_for(actor, course_id)
        try:
            a = Assignment.objects.get(pk=int(aid), course_id=cid)
        except Assignment.DoesNotExist:
            raise NotFound("Assignment not found in course") from None
        data = request.data or {}
        sub = submit_assignment(
            assignment_id=a.id, student_id=uid,
            submission_type=data.get("submission_type", "text"),
            content=data.get("content", ""),
        )
        return Response(SubmissionSerializer(sub).data, status=201)


class MySubmissionView(APIView):
    permission_classes = [LmsPerm("lms.submission.view_own")]
    throttle_scope = "lms_submit"

    @extend_schema(
        tags=["lms"],
        summary="View current student's submissions for an assignment",
        responses={200: SubmissionSerializer(many=True)},
    )
    def get(self, request, course_id, aid):
        actor = _actor(request)
        cid = scoping.course_for(actor, course_id)
        try:
            Assignment.objects.get(pk=int(aid), course_id=cid)
        except Assignment.DoesNotExist:
            raise NotFound("Assignment not found in course") from None
        subs = scoping.submissions_for_student(actor, int(aid))
        return Response(SubmissionSerializer(subs, many=True).data)


class GradeSubmissionView(APIView):
    permission_classes = [LmsPerm("lms.grade.create")]
    throttle_scope = "lms_grade"

    @extend_schema(
        tags=["lms"],
        summary="Grade a submission",
        request=GradeSerializer,
        responses={201: GradeSerializer},
    )
    def post(self, request, course_id, aid, sid):
        actor = _actor(request)
        uid = actor.user_id if actor else 0
        cid = scoping.course_for(actor, course_id)
        try:
            sub = Submission.objects.get(
                pk=int(sid), assignment_id=int(aid), assignment__course_id=cid
            )
        except Submission.DoesNotExist:
            raise NotFound("Submission not found in assignment") from None
        data = request.data or {}
        grade = grade_submission(
            submission_id=sub.id, grader_id=uid,
            points=data.get("points", 0), feedback=data.get("feedback", ""),
        )
        return Response(GradeSerializer(grade).data, status=201)


class ReleaseGradeView(APIView):
    permission_classes = [LmsPerm("lms.grade.release")]
    throttle_scope = "lms_grade"

    @extend_schema(
        tags=["lms"],
        summary="Release a graded submission to the student",
        request=None,
        responses={200: GradeSerializer},
    )
    def post(self, request, course_id, aid, sid):
        actor = _actor(request)
        uid = actor.user_id if actor else 0
        cid = scoping.course_for(actor, course_id)
        try:
            sub = Submission.objects.get(
                pk=int(sid), assignment_id=int(aid), assignment__course_id=cid
            )
        except Submission.DoesNotExist:
            raise NotFound("Submission not found in assignment") from None
        try:
            grade = Grade.objects.get(submission=sub)
        except Grade.DoesNotExist:
            raise NotFound("Grade not found") from None
        g = release_grade(grade_id=grade.id, releaser_id=uid)
        return Response(GradeSerializer(g).data)


class MyGradeView(APIView):
    permission_classes = [LmsPerm("lms.grade.view")]
    throttle_scope = "lms_grade"

    @extend_schema(
        tags=["lms"],
        summary="View current student's released grade for an assignment",
        responses={200: GradeSerializer(many=True)},
    )
    def get(self, request, course_id, aid):
        actor = _actor(request)
        uid = actor.user_id if actor else 0
        cid = scoping.course_for(actor, course_id)
        try:
            Assignment.objects.get(pk=int(aid), course_id=cid)
        except Assignment.DoesNotExist:
            raise NotFound("Assignment not found in course") from None
        grades = scoping.released_grades_for_student(int(aid), uid)
        return Response(GradeSerializer(grades, many=True).data)


class SubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = SubmissionSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope = "lms_submit"

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [LmsPerm("lms.submission.view")()]
        return [LmsPerm("lms.submission.create")()]

    def get_queryset(self):
        actor = _actor(self.request)
        aid = self.kwargs.get("aid") or self.request.query_params.get("assignment_id")
        if not aid:
            return Submission.objects.none()
        perms = getattr(actor, "permissions", []) or []
        if "lms.submission.grade" in perms or "lms.assignment.manage" in perms:
            return scoping.submissions_for_grading(actor, int(aid))
        return scoping.submissions_for_student(actor, int(aid))


class GradeViewSet(viewsets.ModelViewSet):
    serializer_class = GradeSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope = "lms_grade"

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [LmsPerm("lms.grade.view")()]
        return [LmsPerm("lms.grade.create")()]

    def get_queryset(self):
        actor = _actor(self.request)
        aid = self.kwargs.get("aid") or self.request.query_params.get("assignment_id")
        if not aid:
            return Grade.objects.none()
        perms = getattr(actor, "permissions", []) or []
        if "lms.grade.release" in perms or "lms.grade.create" in perms:
            return Grade.objects.filter(submission__assignment_id=int(aid))
        uid = getattr(actor, "user_id", None)
        return scoping.released_grades_for_student(int(aid), uid)
