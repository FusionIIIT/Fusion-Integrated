"""DRF API views for LMS (Course Management)."""
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..domain.errors import LmsDomainError
from ..selectors import courses as selectors
from ..services import courses as services
from .permissions import (
    RequireAnnouncementPost,
    RequireAssignmentCreate,
    RequireAssignmentSubmit,
    RequireAssignmentView,
    RequireCourseManage,
    RequireCourseView,
    RequireGradeAudit,
    RequireGradeEvaluate,
    RequireGradeRelease,
    RequireGradeView,
    RequireLmsModule,
    RequireMaterialUpload,
    RequireMaterialView,
)
from .serializers import (
    AssignmentCreateSerializer,
    AssignmentPublishSerializer,
    AssignmentSerializer,
    CourseAnnouncementSerializer,
    CourseMaterialSerializer,
    CourseMembershipSerializer,
    CourseWorkspaceSerializer,
    GradeChangeLogSerializer,
    GradeEvaluationSerializer,
    GradeModificationSerializer,
    GradeSerializer,
    StudentSubmissionCreateSerializer,
    StudentSubmissionSerializer,
)


def _get_principal_user(request) -> tuple[int, str]:
    principal = getattr(request, "principal", None)
    if principal:
        user_id = getattr(principal, "erp_user_id", getattr(request.user, "id", 1))
        role = getattr(principal, "designation", "student")
        return user_id, role
    return getattr(request.user, "id", 1), "student"


class UserCourseListView(APIView):
    """Return all courses the current user is enrolled in or assigned to."""

    permission_classes = [RequireLmsModule, RequireCourseView]

    def get(self, request):
        user_id, _ = _get_principal_user(request)
        memberships = selectors.get_user_memberships(user_id)
        serializer = CourseMembershipSerializer(memberships, many=True)
        return Response(serializer.data)


class CourseDetailView(APIView):
    """Return dedicated course workspace details (BR-LMS-001)."""

    permission_classes = [RequireLmsModule, RequireCourseView]

    def get(self, request, course_id: int):
        user_id, _ = _get_principal_user(request)
        try:
            workspace = selectors.get_course_workspace(course_id, user_id)
            serializer = CourseWorkspaceSerializer(workspace)
            membership = selectors.get_membership(course_id, user_id)
            data = serializer.data
            data["user_role"] = membership.role if membership else None
            data["can_post_announcements"] = membership.can_post_announcements if membership else False
            return Response(data)
        except LmsDomainError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)


class CourseMaterialListCreateView(APIView):
    """List published materials (or all for faculty) and upload new materials."""

    permission_classes = [RequireLmsModule, RequireMaterialView]

    def get(self, request, course_id: int):
        user_id, _ = _get_principal_user(request)
        membership = selectors.get_membership(course_id, user_id)
        role = membership.role if membership else "student"

        materials = selectors.get_course_materials(course_id, role)
        serializer = CourseMaterialSerializer(materials, many=True)
        return Response(serializer.data)

    def post(self, request, course_id: int):
        user_id, _ = _get_principal_user(request)
        membership = selectors.get_membership(course_id, user_id)
        role = membership.role if membership else "student"

        try:
            mat = services.upload_course_material(
                course_id=course_id,
                user_id=user_id,
                user_role=role,
                title=request.data.get("title", ""),
                description=request.data.get("description", ""),
                section_or_week=request.data.get("section_or_week", "General"),
                material_type=request.data.get("material_type", "file"),
                file_url=request.data.get("file_url", ""),
                content=request.data.get("content", ""),
                is_scheduled=request.data.get("is_scheduled", False),
                scheduled_release_at=request.data.get("scheduled_release_at"),
            )
            return Response(CourseMaterialSerializer(mat).data, status=status.HTTP_201_CREATED)
        except LmsDomainError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CourseAnnouncementListCreateView(APIView):
    """List and post course-wide announcements."""

    permission_classes = [RequireLmsModule, RequireCourseView]

    def get(self, request, course_id: int):
        announcements = selectors.get_course_announcements(course_id)
        return Response(CourseAnnouncementSerializer(announcements, many=True).data)

    def post(self, request, course_id: int):
        user_id, _ = _get_principal_user(request)
        membership = selectors.get_membership(course_id, user_id)
        role = membership.role if membership else "student"
        can_post = membership.can_post_announcements if membership else False

        try:
            ann = services.post_course_announcement(
                course_id=course_id,
                user_id=user_id,
                user_role=role,
                title=request.data.get("title", ""),
                content=request.data.get("content", ""),
                can_post_announcements=can_post,
            )
            return Response(CourseAnnouncementSerializer(ann).data, status=status.HTTP_201_CREATED)
        except LmsDomainError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)


class AssignmentListCreateView(APIView):
    """List assignments and create new assignments in Draft state."""

    permission_classes = [RequireLmsModule, RequireAssignmentView]

    def get(self, request, course_id: int):
        user_id, _ = _get_principal_user(request)
        membership = selectors.get_membership(course_id, user_id)
        role = membership.role if membership else "student"

        assignments = selectors.get_course_assignments(course_id, role)
        return Response(AssignmentSerializer(assignments, many=True).data)

    def post(self, request, course_id: int):
        user_id, _ = _get_principal_user(request)
        membership = selectors.get_membership(course_id, user_id)
        role = membership.role if membership else "student"

        serializer = AssignmentCreateSerializer(data={**request.data, "course_id": course_id})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            asgn = services.create_assignment(
                course_id=course_id,
                user_id=user_id,
                user_role=role,
                title=data["title"],
                instructions=data["instructions"],
                points_possible=data["points_possible"],
                submission_type=data["submission_type"],
                due_date=data["due_date"],
            )
            return Response(AssignmentSerializer(asgn).data, status=status.HTTP_201_CREATED)
        except LmsDomainError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AssignmentPublishView(APIView):
    """Publish an assignment immediately or schedule future release (CW-LMS-01)."""

    permission_classes = [RequireLmsModule, RequireAssignmentCreate]

    def post(self, request, assignment_id: int):
        user_id, _ = _get_principal_user(request)
        assignment = generics.get_object_or_404(selectors.Assignment, id=assignment_id)
        membership = selectors.get_membership(assignment.course_id, user_id)
        role = membership.role if membership else "faculty"

        serializer = AssignmentPublishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            asgn = services.publish_assignment(
                assignment_id=assignment_id,
                user_role=role,
                is_scheduled=data["is_scheduled"],
                release_date=data.get("release_date"),
            )
            return Response(AssignmentSerializer(asgn).data)
        except LmsDomainError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StudentSubmissionView(APIView):
    """Submit work or view student submission."""

    permission_classes = [RequireLmsModule, RequireAssignmentView]

    def get(self, request, assignment_id: int):
        user_id, _ = _get_principal_user(request)
        assignment = generics.get_object_or_404(selectors.Assignment, id=assignment_id)
        membership = selectors.get_membership(assignment.course_id, user_id)
        role = membership.role if membership else "student"

        try:
            submissions = selectors.get_assignment_submissions(assignment_id, user_id, role)
            return Response(StudentSubmissionSerializer(submissions, many=True).data)
        except LmsDomainError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

    def post(self, request, assignment_id: int):
        user_id, _ = _get_principal_user(request)
        assignment = generics.get_object_or_404(selectors.Assignment, id=assignment_id)
        membership = selectors.get_membership(assignment.course_id, user_id)
        role = membership.role if membership else "student"

        serializer = StudentSubmissionCreateSerializer(data={**request.data, "assignment_id": assignment_id})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            sub = services.submit_assignment(
                assignment_id=assignment_id,
                student_user_id=user_id,
                student_role=role,
                submission_type=data["submission_type"],
                submission_content=data["submission_content"],
            )
            return Response(StudentSubmissionSerializer(sub).data, status=status.HTTP_201_CREATED)
        except LmsDomainError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GradeSubmissionView(APIView):
    """Grade submission (draft) or release assignment grades."""

    permission_classes = [RequireLmsModule, RequireGradeView]

    def post(self, request, submission_id: int):
        """Enter points and feedback (draft)."""
        user_id, _ = _get_principal_user(request)
        submission = generics.get_object_or_404(selectors.StudentSubmission, id=submission_id)
        membership = selectors.get_membership(submission.assignment.course_id, user_id)
        role = membership.role if membership else "faculty"

        serializer = GradeEvaluationSerializer(data={**request.data, "submission_id": submission_id})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            grade = services.grade_submission(
                submission_id=submission_id,
                grader_user_id=user_id,
                grader_role=role,
                points=data["points"],
                feedback=data.get("feedback", ""),
            )
            return Response(GradeSerializer(grade).data, status=status.HTTP_200_OK)
        except LmsDomainError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ReleaseGradesView(APIView):
    """Faculty release draft grades to students."""

    permission_classes = [RequireLmsModule, RequireGradeRelease]

    def post(self, request, assignment_id: int):
        user_id, _ = _get_principal_user(request)
        assignment = generics.get_object_or_404(selectors.Assignment, id=assignment_id)
        membership = selectors.get_membership(assignment.course_id, user_id)
        role = membership.role if membership else "faculty"

        try:
            count = services.release_assignment_grades(
                assignment_id=assignment_id,
                releaser_user_id=user_id,
                releaser_role=role,
            )
            return Response({"released_count": count}, status=status.HTTP_200_OK)
        except LmsDomainError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)


class ModifyReleasedGradeView(APIView):
    """Modify a grade after release and record audit log (BR-LMS-019)."""

    permission_classes = [RequireLmsModule, RequireGradeRelease]

    def patch(self, request, grade_id: int):
        user_id, _ = _get_principal_user(request)
        grade = generics.get_object_or_404(selectors.Grade, id=grade_id)
        membership = selectors.get_membership(grade.submission.assignment.course_id, user_id)
        role = membership.role if membership else "faculty"

        serializer = GradeModificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            updated = services.modify_released_grade(
                grade_id=grade_id,
                modifier_user_id=user_id,
                modifier_role=role,
                new_points=data["new_points"],
                reason=data["reason"],
            )
            return Response(GradeSerializer(updated).data)
        except LmsDomainError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GradeAuditLogView(APIView):
    """View post-release grade modification audit logs (BR-LMS-019)."""

    permission_classes = [RequireLmsModule, RequireGradeAudit]

    def get(self, request, grade_id: int):
        logs = selectors.get_grade_change_logs(grade_id)
        return Response(GradeChangeLogSerializer(logs, many=True).data)
