from __future__ import annotations

from decimal import Decimal
from django.db.models import Count, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError, NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.lms.models import (
    Course,
    CourseMembership,
    CourseMaterial,
    CourseAnnouncement,
    Assignment,
    AssignmentSubmission,
    SubmissionGrade,
    GradeChangeAudit,
)
from modules.lms.api.serializers import (
    CourseSerializer,
    CourseMembershipSerializer,
    CourseMaterialSerializer,
    CourseAnnouncementSerializer,
    AssignmentSerializer,
    AssignmentSubmissionSerializer,
    SubmissionGradeSerializer,
    GradeChangeAuditSerializer,
)
from modules.lms.services.access import (
    get_course_membership,
    require_course_access,
    require_faculty,
    require_can_announce,
    require_can_grade,
    require_non_observer,
)
from modules.lms.services.grading import (
    grade_submission,
    release_assignment_grades,
    release_single_grade,
)
from modules.lms.services.releases import process_scheduled_releases

MODULE = HasModuleGrant("lms")

PERM_COURSE_CREATE = "lms.course.create"
PERM_COURSE_VIEW = "lms.course.view"
PERM_COURSE_MANAGE = "lms.course.manage"
PERM_MATERIAL_VIEW = "lms.material.view"
PERM_MATERIAL_MANAGE = "lms.material.manage"
PERM_ANNOUNCEMENT_VIEW = "lms.announcement.view"
PERM_ANNOUNCEMENT_POST = "lms.announcement.post"
PERM_ASSIGNMENT_VIEW = "lms.assignment.view"
PERM_ASSIGNMENT_MANAGE = "lms.assignment.manage"
PERM_SUBMISSION_CREATE = "lms.submission.create"
PERM_SUBMISSION_VIEW_SELF = "lms.submission.view_self"
PERM_SUBMISSION_VIEW_ALL = "lms.submission.view_all"
PERM_GRADE_VIEW = "lms.grade.view"
PERM_GRADE_VIEW_SELF = "lms.grade.view_self"
PERM_GRADE_VIEW_ALL = "lms.grade.view_all"
PERM_GRADE_MANAGE = "lms.grade.manage"
PERM_GRADE_RELEASE = "lms.grade.release"
PERM_AUDIT_VIEW = "lms.audit.view"


def _actor(request):
    return getattr(request, "principal", None)


class CourseListView(APIView):
    permission_classes = [MODULE]

    @extend_schema(operation_id="lms_courses_list", responses=CourseSerializer(many=True))
    def get(self, request):
        actor = _actor(request)
        user_id = actor.user_id if actor else None

        # BR-LMS-001, BR-LMS-002: Return courses the user is enrolled in or assigned to
        memberships = CourseMembership.objects.filter(user_id=user_id, is_active=True).values_list("course_id", "role")
        user_course_ids = [m[0] for m in memberships]
        role_map = {m[0]: m[1] for m in memberships}

        courses = Course.objects.filter(id__in=user_course_ids, is_active=True).annotate(
            materials_count=Count("materials", filter=Q(materials__status="published"), distinct=True),
            assignments_count=Count("assignments", filter=Q(assignments__status="published"), distinct=True),
            announcements_count=Count("announcements", distinct=True),
        )

        data = CourseSerializer(courses, many=True, context={"request": request}).data
        for c in data:
            c["my_role"] = role_map.get(c["id"], "")
        return Response(data)

    @extend_schema(operation_id="lms_courses_create", request=CourseSerializer, responses=CourseSerializer)
    def post(self, request):
        actor = _actor(request)
        serializer = CourseSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        course = serializer.save()

        # Creator automatically becomes faculty and primary instructor
        if actor:
            CourseMembership.objects.create(
                course=course,
                user_id=actor.user_id,
                role="faculty",
                is_primary_instructor=True,
            )

        return Response(CourseSerializer(course, context={"request": request}).data, status=status.HTTP_201_CREATED)


class CourseDetailView(APIView):
    permission_classes = [MODULE]

    @extend_schema(operation_id="lms_course_retrieve", responses=CourseSerializer)
    def get(self, request, course_id: int):
        actor = _actor(request)
        course, membership = require_course_access(course_id, actor.user_id)
        data = CourseSerializer(course, context={"request": request}).data
        data["my_role"] = membership.role
        return Response(data)

    @extend_schema(operation_id="lms_course_update_put", request=CourseSerializer, responses=CourseSerializer)
    def put(self, request, course_id: int):
        return self.patch(request, course_id)

    @extend_schema(operation_id="lms_course_update", request=CourseSerializer, responses=CourseSerializer)
    def patch(self, request, course_id: int):
        actor = _actor(request)
        course, membership = require_course_access(course_id, actor.user_id)
        require_faculty(membership, "Only assigned faculty may edit course details (CFR-LMS-002).")

        serializer = CourseSerializer(course, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        data = CourseSerializer(updated, context={"request": request}).data
        data["my_role"] = membership.role
        return Response(data)


class CourseRosterView(APIView):
    permission_classes = [MODULE]

    @extend_schema(operation_id="lms_roster_list", responses=CourseMembershipSerializer(many=True))
    def get(self, request, course_id: int):
        actor = _actor(request)
        course, membership = require_course_access(course_id, actor.user_id)
        if membership.role == "observer":
            members = CourseMembership.objects.filter(course=course, role__in=["faculty", "ta"], is_active=True)
        else:
            members = CourseMembership.objects.filter(course=course, is_active=True)
        return Response(CourseMembershipSerializer(members, many=True).data)

    @extend_schema(operation_id="lms_roster_add", request=CourseMembershipSerializer, responses=CourseMembershipSerializer)
    def post(self, request, course_id: int):
        actor = _actor(request)
        course, membership = require_course_access(course_id, actor.user_id)
        require_faculty(membership, "Only course faculty may add or invite members.")

        user_id = request.data.get("user_id")
        role = request.data.get("role", "student")
        if not user_id:
            raise ValidationError({"user_id": "user_id is required."})

        mem, _ = CourseMembership.objects.update_or_create(
            course=course,
            user_id=int(user_id),
            role=role,
            defaults={"is_active": True},
        )
        return Response(CourseMembershipSerializer(mem).data, status=status.HTTP_201_CREATED)


class CourseMaterialListView(APIView):
    permission_classes = [MODULE]

    @extend_schema(operation_id="lms_materials_list", responses=CourseMaterialSerializer(many=True))
    def get(self, request, course_id: int):
        actor = _actor(request)
        course, membership = require_course_access(course_id, actor.user_id)

        materials = CourseMaterial.objects.filter(course=course)
        if membership.role != "faculty":
            now = timezone.now()
            materials = materials.filter(
                status="published"
            ).filter(Q(release_date__isnull=True) | Q(release_date__lte=now))

        return Response(CourseMaterialSerializer(materials, many=True).data)

    @extend_schema(operation_id="lms_materials_create", request=CourseMaterialSerializer, responses=CourseMaterialSerializer)
    def post(self, request, course_id: int):
        actor = _actor(request)
        course, membership = require_course_access(course_id, actor.user_id)
        require_faculty(membership, "TAs and students cannot create course materials (BR-LMS-004).")

        serializer = CourseMaterialSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        release_date = serializer.validated_data.get("release_date")
        stat = serializer.validated_data.get("status", "published")
        if release_date and release_date > timezone.now() and stat != "draft":
            stat = "scheduled"

        mat = serializer.save(
            course=course,
            status=stat,
            created_by_user_id=actor.user_id,
        )
        return Response(CourseMaterialSerializer(mat).data, status=status.HTTP_201_CREATED)


class CourseMaterialDetailView(APIView):
    permission_classes = [MODULE]

    @extend_schema(operation_id="lms_material_update_put", request=CourseMaterialSerializer, responses=CourseMaterialSerializer)
    def put(self, request, material_id: int):
        return self.patch(request, material_id)

    @extend_schema(operation_id="lms_material_update", request=CourseMaterialSerializer, responses=CourseMaterialSerializer)
    def patch(self, request, material_id: int):
        actor = _actor(request)
        mat = CourseMaterial.objects.filter(id=material_id).first()
        if not mat:
            raise NotFound("Material not found.")
        _, membership = require_course_access(mat.course_id, actor.user_id)
        require_faculty(membership, "Only course faculty may edit materials (BR-LMS-004).")

        serializer = CourseMaterialSerializer(mat, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        return Response(CourseMaterialSerializer(updated).data)

    @extend_schema(operation_id="lms_material_delete", responses={204: None})
    def delete(self, request, material_id: int):
        actor = _actor(request)
        mat = CourseMaterial.objects.filter(id=material_id).first()
        if not mat:
            raise NotFound("Material not found.")
        _, membership = require_course_access(mat.course_id, actor.user_id)
        require_faculty(membership, "Only course faculty may delete materials (BR-LMS-004).")
        mat.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CourseAnnouncementListView(APIView):
    permission_classes = [MODULE]

    @extend_schema(operation_id="lms_announcements_list", responses=CourseAnnouncementSerializer(many=True))
    def get(self, request, course_id: int):
        actor = _actor(request)
        course, _ = require_course_access(course_id, actor.user_id)
        announcements = CourseAnnouncement.objects.filter(course=course)
        return Response(CourseAnnouncementSerializer(announcements, many=True).data)

    @extend_schema(operation_id="lms_announcements_create", request=CourseAnnouncementSerializer, responses=CourseAnnouncementSerializer)
    def post(self, request, course_id: int):
        actor = _actor(request)
        course, membership = require_course_access(course_id, actor.user_id)
        require_can_announce(course, membership)

        serializer = CourseAnnouncementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        announcement = serializer.save(
            course=course,
            posted_by_user_id=actor.user_id,
            posted_by_role=membership.role,
            posted_by_name=getattr(actor, "display_name", "") or getattr(actor, "username", f"User {actor.user_id}"),
        )
        return Response(CourseAnnouncementSerializer(announcement).data, status=status.HTTP_201_CREATED)


class CourseAnnouncementDetailView(APIView):
    permission_classes = [MODULE]

    @extend_schema(operation_id="lms_announcement_delete", responses={204: None})
    def delete(self, request, announcement_id: int):
        actor = _actor(request)
        ann = CourseAnnouncement.objects.filter(id=announcement_id).first()
        if not ann:
            raise NotFound("Announcement not found.")
        _, membership = require_course_access(ann.course_id, actor.user_id)
        require_faculty(membership, "Only course faculty may delete announcements.")
        ann.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AllAnnouncementsView(APIView):
    permission_classes = [MODULE]

    @extend_schema(operation_id="lms_all_announcements", responses=CourseAnnouncementSerializer(many=True))
    def get(self, request):
        actor = _actor(request)
        user_id = actor.user_id if actor else None
        user_course_ids = CourseMembership.objects.filter(user_id=user_id, is_active=True).values_list("course_id", flat=True)
        announcements = CourseAnnouncement.objects.filter(course_id__in=user_course_ids).order_by("-is_pinned", "-created_at")
        return Response(CourseAnnouncementSerializer(announcements, many=True).data)


class CourseAssignmentListView(APIView):
    permission_classes = [MODULE]

    @extend_schema(operation_id="lms_assignments_list", responses=AssignmentSerializer(many=True))
    def get(self, request, course_id: int):
        actor = _actor(request)
        course, membership = require_course_access(course_id, actor.user_id)

        assignments = Assignment.objects.filter(course=course).annotate(
            submissions_count=Count("submissions", distinct=True)
        )
        if membership.role == "student":
            now = timezone.now()
            assignments = assignments.filter(status="published").filter(
                Q(release_date__isnull=True) | Q(release_date__lte=now)
            )

        return Response(AssignmentSerializer(assignments, many=True, context={"request": request}).data)

    @extend_schema(operation_id="lms_assignments_create", request=AssignmentSerializer, responses=AssignmentSerializer)
    def post(self, request, course_id: int):
        actor = _actor(request)
        course, membership = require_course_access(course_id, actor.user_id)
        require_faculty(membership, "TAs cannot create assignments (BR-LMS-004).")

        serializer = AssignmentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        stat = serializer.validated_data.get("status", "draft")
        asgn = serializer.save(
            course=course,
            status=stat,
            created_by_user_id=actor.user_id,
        )
        return Response(AssignmentSerializer(asgn, context={"request": request}).data, status=status.HTTP_201_CREATED)


class AllAssignmentsView(APIView):
    permission_classes = [MODULE]

    @extend_schema(operation_id="lms_all_assignments", responses=AssignmentSerializer(many=True))
    def get(self, request):
        actor = _actor(request)
        user_id = actor.user_id if actor else None
        memberships = CourseMembership.objects.filter(user_id=user_id, is_active=True).values_list("course_id", "role")
        user_course_ids = [m[0] for m in memberships]
        is_only_student = all(m[1] == "student" for m in memberships) if memberships else True

        assignments = Assignment.objects.filter(course_id__in=user_course_ids).select_related("course")
        if is_only_student:
            now = timezone.now()
            assignments = assignments.filter(status="published").filter(
                Q(release_date__isnull=True) | Q(release_date__lte=now)
            )
        return Response(AssignmentSerializer(assignments, many=True, context={"request": request}).data)


class AssignmentDetailView(APIView):
    permission_classes = [MODULE]

    @extend_schema(operation_id="lms_assignment_retrieve", responses=AssignmentSerializer)
    def get(self, request, assignment_id: int):
        actor = _actor(request)
        asgn = Assignment.objects.filter(id=assignment_id).first()
        if not asgn:
            raise NotFound("Assignment not found.")
        _, membership = require_course_access(asgn.course_id, actor.user_id)

        if membership.role == "student" and not asgn.is_available_to_students():
            raise NotFound("Assignment not available yet.")

        return Response(AssignmentSerializer(asgn, context={"request": request}).data)

    @extend_schema(operation_id="lms_assignment_update_put", request=AssignmentSerializer, responses=AssignmentSerializer)
    def put(self, request, assignment_id: int):
        return self.patch(request, assignment_id)

    @extend_schema(operation_id="lms_assignment_update", request=AssignmentSerializer, responses=AssignmentSerializer)
    def patch(self, request, assignment_id: int):
        actor = _actor(request)
        asgn = Assignment.objects.filter(id=assignment_id).first()
        if not asgn:
            raise NotFound("Assignment not found.")
        _, membership = require_course_access(asgn.course_id, actor.user_id)
        require_faculty(membership, "Only course faculty may edit assignments (BR-LMS-004).")

        serializer = AssignmentSerializer(asgn, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        return Response(AssignmentSerializer(updated, context={"request": request}).data)


class AssignmentPublishView(APIView):
    permission_classes = [MODULE]

    @extend_schema(operation_id="lms_assignment_publish", request=None, responses=AssignmentSerializer)
    def post(self, request, assignment_id: int):
        actor = _actor(request)
        asgn = Assignment.objects.filter(id=assignment_id).first()
        if not asgn:
            raise NotFound("Assignment not found.")
        _, membership = require_course_access(asgn.course_id, actor.user_id)
        require_faculty(membership, "Only course faculty may publish assignments (BR-LMS-004).")

        asgn.status = "published"
        asgn.save()
        return Response(AssignmentSerializer(asgn, context={"request": request}).data)


class AssignmentSubmitView(APIView):
    permission_classes = [MODULE]

    @extend_schema(operation_id="lms_assignment_submit", request=AssignmentSubmissionSerializer, responses=AssignmentSubmissionSerializer)
    def post(self, request, assignment_id: int):
        actor = _actor(request)
        asgn = Assignment.objects.filter(id=assignment_id).first()
        if not asgn:
            raise NotFound("Assignment not found.")
        _, membership = require_course_access(asgn.course_id, actor.user_id)
        require_non_observer(membership, "Observers cannot submit assignments (BR-LMS-003).")

        if membership.role != "student":
            raise PermissionDenied("Only enrolled students may submit assignment solutions.")

        now = timezone.now()
        is_late = now > asgn.due_date
        if is_late and not asgn.allow_late_submissions:
            raise ValidationError("Late submissions are not accepted for this assignment (BR-LMS-012).")

        previous_sub = AssignmentSubmission.objects.filter(
            assignment=asgn, student_user_id=actor.user_id
        ).order_by("-version").first()
        version = (previous_sub.version + 1) if previous_sub else 1

        serializer = AssignmentSubmissionSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        sub_type = serializer.validated_data.get("submission_type")
        if sub_type and sub_type != asgn.submission_type:
            raise ValidationError(f"Submission type '{sub_type}' does not match required type '{asgn.submission_type}' (BR-LMS-012).")

        submission = serializer.save(
            assignment=asgn,
            student_user_id=actor.user_id,
            status="late" if is_late else "submitted",
            submitted_at=now,
            version=version,
        )
        return Response(AssignmentSubmissionSerializer(submission, context={"request": request}).data, status=status.HTTP_201_CREATED)


class MyAssignmentSubmissionView(APIView):
    permission_classes = [MODULE]

    @extend_schema(operation_id="lms_assignment_my_submission", responses=AssignmentSubmissionSerializer)
    def get(self, request, assignment_id: int):
        actor = _actor(request)
        sub = AssignmentSubmission.objects.filter(
            assignment_id=assignment_id,
            student_user_id=actor.user_id,
        ).order_by("-submitted_at").first()
        if not sub:
            raise NotFound("No submission found.")
        return Response(AssignmentSubmissionSerializer(sub, context={"request": request}).data)


class AssignmentSubmissionsListView(APIView):
    permission_classes = [MODULE]

    @extend_schema(operation_id="lms_submissions_list", responses=AssignmentSubmissionSerializer(many=True))
    def get(self, request, assignment_id: int):
        actor = _actor(request)
        asgn = Assignment.objects.filter(id=assignment_id).first()
        if not asgn:
            raise NotFound("Assignment not found.")
        _, membership = require_course_access(asgn.course_id, actor.user_id)
        require_non_observer(membership, "Observers cannot view student submissions (BR-LMS-003).")

        if membership.role not in ["faculty", "ta"]:
            raise PermissionDenied("Only course faculty and TAs may view student submissions (BR-LMS-003).")

        submissions = AssignmentSubmission.objects.filter(assignment=asgn).select_related("grade").order_by("-submitted_at")
        return Response(AssignmentSubmissionSerializer(submissions, many=True, context={"request": request}).data)


class GradeSubmissionView(APIView):
    permission_classes = [MODULE]

    @extend_schema(operation_id="lms_submission_grade", request=SubmissionGradeSerializer, responses=SubmissionGradeSerializer)
    def post(self, request, submission_id: int):
        actor = _actor(request)
        sub = AssignmentSubmission.objects.filter(id=submission_id).select_related("assignment__course").first()
        if not sub:
            raise NotFound("Submission not found.")
        course = sub.assignment.course
        _, membership = require_course_access(course.id, actor.user_id)
        require_can_grade(course, membership)

        points = request.data.get("points_awarded")
        if points is None:
            raise ValidationError({"points_awarded": "points_awarded is required."})

        feedback = request.data.get("feedback", "")
        change_reason = request.data.get("change_reason", "")
        grader_name = getattr(actor, "display_name", "") or getattr(actor, "username", f"User {actor.user_id}")

        grade = grade_submission(
            submission=sub,
            points=Decimal(str(points)),
            feedback=feedback,
            grader_user_id=actor.user_id,
            grader_role=membership.role,
            grader_name=grader_name,
            change_reason=change_reason,
        )
        return Response(SubmissionGradeSerializer(grade).data)


class ReleaseGradesView(APIView):
    permission_classes = [MODULE]

    @extend_schema(operation_id="lms_grades_release", request=None, responses={200: None})
    def post(self, request, assignment_id: int):
        actor = _actor(request)
        asgn = Assignment.objects.filter(id=assignment_id).first()
        if not asgn:
            raise NotFound("Assignment not found.")
        _, membership = require_course_access(asgn.course_id, actor.user_id)
        require_faculty(membership, "TAs cannot release grades; faculty only (BR-LMS-004, BR-LMS-016).")

        count = release_assignment_grades(asgn, actor.user_id)
        return Response({"released_count": count, "message": f"Successfully released {count} grade(s)."})


class MyGradesListView(APIView):
    permission_classes = [MODULE]

    @extend_schema(operation_id="lms_my_grades", responses={200: None})
    def get(self, request):
        actor = _actor(request)
        user_id = actor.user_id if actor else None

        # BR-LMS-016, BR-LMS-018: Student only sees released grades
        grades = SubmissionGrade.objects.filter(
            submission__student_user_id=user_id,
            status="released",
        ).select_related("submission__assignment__course")

        data = []
        for g in grades:
            asgn = g.submission.assignment
            data.append({
                "grade_id": g.id,
                "submission_id": g.submission.id,
                "assignment_id": asgn.id,
                "assignment_title": asgn.title,
                "assignment_points_possible": asgn.points_possible,
                "points_awarded": g.points_awarded,
                "feedback": g.feedback,
                "course_id": asgn.course.id,
                "course_code": asgn.course.code,
                "course_name": asgn.course.name,
                "released_at": g.released_at,
                "graded_by_name": g.graded_by_name,
                "status": g.status,
            })

        return Response(data)


class GradeAuditListView(APIView):
    permission_classes = [MODULE]

    @extend_schema(operation_id="lms_grade_audit_list", responses=GradeChangeAuditSerializer(many=True))
    def get(self, request, grade_id: int):
        actor = _actor(request)
        grade = SubmissionGrade.objects.filter(id=grade_id).select_related("submission__assignment").first()
        if not grade:
            raise NotFound("Grade not found.")
        _, membership = require_course_access(grade.submission.assignment.course_id, actor.user_id)
        require_faculty(membership, "Only course faculty may view grade change audit logs (BR-LMS-019).")

        audits = GradeChangeAudit.objects.filter(grade=grade).order_by("-changed_at")
        return Response(GradeChangeAuditSerializer(audits, many=True).data)


class ProcessScheduledReleasesView(APIView):
    permission_classes = [MODULE]

    @extend_schema(operation_id="lms_process_scheduled_releases", request=None, responses={200: None})
    def post(self, request):
        # UC-LMS-015: Event/cron triggered content release processor
        results = process_scheduled_releases()
        return Response(results)
