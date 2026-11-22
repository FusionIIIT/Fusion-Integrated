"""API views for LMS Course Workspace and Materials."""
import os

from django.http import FileResponse
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError, PermissionDeniedError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.lms.api.serializers import (
    AssignmentDeadlineInfoSerializer,
    AssignmentExtensionItemSerializer,
    CourseAnnouncementCreateSerializer,
    CourseAnnouncementItemSerializer,
    CourseAnnouncementsResponseSerializer,
    CourseAssignmentCreateSerializer,
    CourseAssignmentItemSerializer,
    CourseAssignmentsResponseSerializer,
    CourseAssignmentUpdateSerializer,
    CourseMaterialCreateSerializer,
    CourseMaterialItemSerializer,
    CourseMaterialsResponseSerializer,
    CourseMaterialUpdateSerializer,
    CourseSubmissionCreateSerializer,
    CourseSubmissionGradeDetailSerializer,
    CourseSubmissionHistorySerializer,
    CourseSubmissionItemSerializer,
    CourseSubmissionsListResponseSerializer,
    CourseSummarySerializer,
    CourseWorkspaceDetailSerializer,
    CourseWorkspaceUpdateSerializer,
    GrantExtensionSerializer,
    RecordSubmissionGradeSerializer,
    UpdateDeadlineWindowSerializer,
)
from modules.lms.selectors.announcements import (
    get_course_announcement_detail,
    list_course_announcements,
)
from modules.lms.selectors.assignments import (
    get_assignment_for_download,
    get_course_assignment_detail,
    list_course_assignments,
)
from modules.lms.selectors.courses import course_workspace_details, visible_courses
from modules.lms.selectors.deadlines import (
    get_assignment_deadline_info,
    list_assignment_extensions,
)
from modules.lms.selectors.grades import get_submission_grade
from modules.lms.selectors.materials import (
    get_course_material_detail,
    get_material_for_download,
    list_course_materials,
)
from modules.lms.selectors.submissions import (
    _submission_to_dict,
    get_student_submission_history,
    get_submission_for_download,
    list_assignment_submissions,
)
from modules.lms.services import announcements as announcement_service
from modules.lms.services import assignments as assignment_service
from modules.lms.services import courses as course_service
from modules.lms.services import deadlines as deadline_service
from modules.lms.services import grades as grade_service
from modules.lms.services import materials as material_service
from modules.lms.services import submissions as submission_service

MODULE = HasModuleGrant("lms")
P_VIEW = "lms.course.view"
P_MANAGE = "lms.course.manage"
P_MAT_VIEW = "lms.material.view"
P_MAT_MANAGE = "lms.material.manage"
P_ANN_VIEW = "lms.announcement.view"
P_ANN_MANAGE = "lms.announcement.manage"
P_ASG_VIEW = "lms.assignment.view"
P_ASG_MANAGE = "lms.assignment.manage"
P_DDL_VIEW = "lms.deadline.view"
P_DDL_MANAGE = "lms.deadline.manage"
P_SUB_VIEW = "lms.submission.view"
P_SUB_SUBMIT = "lms.submission.submit"
P_GRD_VIEW = "lms.grade.view"
P_GRD_GRADE = "lms.grade.grade"



class CourseListView(APIView):
    """List all course workspaces the caller is enrolled in, assigned to, or linked to."""

    permission_classes = [MODULE, HasPermission(P_VIEW)]

    @extend_schema(
        summary="List authorized course workspaces",
        tags=["lms"],
        responses=CourseSummarySerializer(many=True),
    )
    def get(self, request):
        courses = visible_courses(request.principal)
        return Response({"results": CourseSummarySerializer(courses, many=True).data})


class CourseWorkspaceDetailView(APIView):
    """View and manage course home workspace details."""

    def get_permissions(self):
        perm = P_VIEW if self.request.method == "GET" else P_MANAGE
        return [MODULE(), HasPermission(perm)()]

    @extend_schema(
        summary="Retrieve course workspace details",
        tags=["lms"],
        responses={200: CourseWorkspaceDetailSerializer},
    )
    def get(self, request, code: str):
        data = course_workspace_details(principal=request.principal, course_code=code)
        if data is None:
            raise NotFoundError(
                "Course workspace not found or you are not authorized to access it."
            )
        return Response(CourseWorkspaceDetailSerializer(data).data)

    @extend_schema(
        summary="Configure course workspace details (Faculty only)",
        tags=["lms"],
        request=CourseWorkspaceUpdateSerializer,
        responses={200: CourseWorkspaceDetailSerializer},
    )
    def patch(self, request, code: str):
        payload = CourseWorkspaceUpdateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        course_service.update_course_workspace(
            actor=request.principal,
            course_code=code,
            **payload.validated_data,
        )

        refreshed = course_workspace_details(principal=request.principal, course_code=code)
        return Response(CourseWorkspaceDetailSerializer(refreshed).data, status=status.HTTP_200_OK)


class CourseMaterialListView(APIView):
    """List and create course materials (CFR-LMS-003, CFR-LMS-004)."""

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        perm = P_MAT_VIEW if self.request.method == "GET" else P_MAT_MANAGE
        return [MODULE(), HasPermission(perm)()]

    @extend_schema(
        operation_id="v1_lms_course_materials_list",
        summary="List published/accessible course materials",
        tags=["lms"],
        responses={200: CourseMaterialsResponseSerializer},
    )
    def get(self, request, code: str):
        data = list_course_materials(principal=request.principal, course_code=code)
        if data is None:
            raise NotFoundError("Course not found or you are not authorized to access it.")
        return Response(CourseMaterialsResponseSerializer(data).data)

    @extend_schema(
        operation_id="v1_lms_course_materials_create",
        summary="Add course material as file, link, or note (Faculty only)",
        tags=["lms"],
        request=CourseMaterialCreateSerializer,
        responses={201: CourseMaterialItemSerializer},
    )
    def post(self, request, code: str):
        payload = CourseMaterialCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        material = material_service.create_course_material(
            actor=request.principal,
            course_code=code,
            **payload.validated_data,
        )

        detail = get_course_material_detail(
            principal=request.principal,
            course_code=code,
            material_id=material.id,
        )
        return Response(CourseMaterialItemSerializer(detail).data, status=status.HTTP_201_CREATED)


class CourseMaterialDetailView(APIView):
    """Retrieve, update, or delete a specific course material item."""

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        perm = P_MAT_VIEW if self.request.method == "GET" else P_MAT_MANAGE
        return [MODULE(), HasPermission(perm)()]

    @extend_schema(
        operation_id="v1_lms_course_materials_retrieve",
        summary="Retrieve course material details",
        tags=["lms"],
        responses={200: CourseMaterialItemSerializer},
    )
    def get(self, request, code: str, material_id: int):
        detail = get_course_material_detail(
            principal=request.principal,
            course_code=code,
            material_id=material_id,
        )
        if detail is None:
            raise NotFoundError("Course material not found or not published.")
        return Response(CourseMaterialItemSerializer(detail).data)

    @extend_schema(
        operation_id="v1_lms_course_materials_partial_update",
        summary="Update course material details or schedule (Faculty only)",
        tags=["lms"],
        request=CourseMaterialUpdateSerializer,
        responses={200: CourseMaterialItemSerializer},
    )
    def patch(self, request, code: str, material_id: int):
        payload = CourseMaterialUpdateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        material_service.update_course_material(
            actor=request.principal,
            course_code=code,
            material_id=material_id,
            **payload.validated_data,
        )

        refreshed = get_course_material_detail(
            principal=request.principal,
            course_code=code,
            material_id=material_id,
        )
        return Response(CourseMaterialItemSerializer(refreshed).data, status=status.HTTP_200_OK)

    @extend_schema(
        operation_id="v1_lms_course_materials_destroy",
        summary="Delete a course material item (Faculty only)",
        tags=["lms"],
        responses={204: None},
    )
    def delete(self, request, code: str, material_id: int):
        material_service.delete_course_material(
            actor=request.principal,
            course_code=code,
            material_id=material_id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class CourseMaterialDownloadView(APIView):
    """Download attached course material file with membership verification."""

    permission_classes = [MODULE, HasPermission(P_MAT_VIEW)]

    @extend_schema(
        operation_id="v1_lms_course_materials_download",
        summary="Download published course material file",
        tags=["lms"],
        responses={200: None},
    )
    def get(self, request, code: str, material_id: int):
        material = get_material_for_download(
            principal=request.principal,
            course_code=code,
            material_id=material_id,
        )
        if material is None or not material.file:
            raise NotFoundError(
                "Material file not found or you are not authorized to download it."
            )

        filename = material.file_name or os.path.basename(material.file.name)
        return FileResponse(material.file.open("rb"), as_attachment=True, filename=filename)


class CourseAnnouncementListView(APIView):
    """List and post course announcements (CFR-LMS-005, UC-LMS-005, UC-LMS-006)."""

    def get_permissions(self):
        perm = P_ANN_VIEW if self.request.method == "GET" else P_ANN_MANAGE
        return [MODULE(), HasPermission(perm)()]

    @extend_schema(
        operation_id="v1_lms_course_announcements_list",
        summary="List course announcements",
        tags=["lms"],
        responses={200: CourseAnnouncementsResponseSerializer},
    )
    def get(self, request, code: str):
        data = list_course_announcements(principal=request.principal, course_code=code)
        if data is None:
            raise NotFoundError("Course not found or you are not authorized to access it.")
        return Response(CourseAnnouncementsResponseSerializer(data).data)

    @extend_schema(
        operation_id="v1_lms_course_announcements_create",
        summary="Post a course-wide announcement (Faculty only)",
        tags=["lms"],
        request=CourseAnnouncementCreateSerializer,
        responses={201: CourseAnnouncementItemSerializer},
    )
    def post(self, request, code: str):
        payload = CourseAnnouncementCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        announcement = announcement_service.post_course_announcement(
            actor=request.principal,
            course_code=code,
            **payload.validated_data,
        )

        detail = get_course_announcement_detail(
            principal=request.principal,
            course_code=code,
            announcement_id=announcement.id,
        )
        return Response(
            CourseAnnouncementItemSerializer(detail).data,
            status=status.HTTP_201_CREATED,
        )



class CourseAnnouncementDetailView(APIView):
    """Retrieve details for a specific course announcement."""

    permission_classes = [MODULE, HasPermission(P_ANN_VIEW)]

    @extend_schema(
        operation_id="v1_lms_course_announcements_retrieve",
        summary="Retrieve course announcement details",
        tags=["lms"],
        responses={200: CourseAnnouncementItemSerializer},
    )
    def get(self, request, code: str, announcement_id: int):
        detail = get_course_announcement_detail(
            principal=request.principal,
            course_code=code,
            announcement_id=announcement_id,
        )
        if detail is None:
            raise NotFoundError("Course announcement not found.")
        return Response(CourseAnnouncementItemSerializer(detail).data)


class CourseAssignmentListView(APIView):
    """List assignments or create a new assignment for a course."""

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        perm = P_ASG_VIEW if self.request.method == "GET" else P_ASG_MANAGE
        return [MODULE(), HasPermission(perm)()]

    @extend_schema(
        operation_id="v1_lms_course_assignments_list",
        summary="List course assignments",
        tags=["lms"],
        responses={200: CourseAssignmentsResponseSerializer},
    )
    def get(self, request, code: str):
        data = list_course_assignments(principal=request.principal, course_code=code)
        if data is None:
            raise NotFoundError("Course not found or you are not authorized to access it.")
        return Response(CourseAssignmentsResponseSerializer(data).data)

    @extend_schema(
        operation_id="v1_lms_course_assignments_create",
        summary="Create a new course assignment (Faculty only)",
        tags=["lms"],
        request=CourseAssignmentCreateSerializer,
        responses={201: CourseAssignmentItemSerializer},
    )
    def post(self, request, code: str):
        payload = CourseAssignmentCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        assignment = assignment_service.create_course_assignment(
            actor=request.principal,
            course_code=code,
            **payload.validated_data,
        )

        detail = get_course_assignment_detail(
            principal=request.principal,
            course_code=code,
            assignment_id=assignment.id,
        )
        return Response(
            CourseAssignmentItemSerializer(detail).data,
            status=status.HTTP_201_CREATED,
        )


class CourseAssignmentDetailView(APIView):
    """Retrieve, update, or delete a course assignment."""

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        perm = P_ASG_VIEW if self.request.method == "GET" else P_ASG_MANAGE
        return [MODULE(), HasPermission(perm)()]

    @extend_schema(
        operation_id="v1_lms_course_assignments_retrieve",
        summary="Retrieve course assignment details",
        tags=["lms"],
        responses={200: CourseAssignmentItemSerializer},
    )
    def get(self, request, code: str, assignment_id: int):
        detail = get_course_assignment_detail(
            principal=request.principal,
            course_code=code,
            assignment_id=assignment_id,
        )
        if detail is None:
            raise NotFoundError("Course assignment not found.")
        return Response(CourseAssignmentItemSerializer(detail).data)

    @extend_schema(
        operation_id="v1_lms_course_assignments_update",
        summary="Update a course assignment (Faculty only)",
        tags=["lms"],
        request=CourseAssignmentUpdateSerializer,
        responses={200: CourseAssignmentItemSerializer},
    )
    def patch(self, request, code: str, assignment_id: int):
        payload = CourseAssignmentUpdateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        assignment = assignment_service.update_course_assignment(
            actor=request.principal,
            course_code=code,
            assignment_id=assignment_id,
            **payload.validated_data,
        )

        detail = get_course_assignment_detail(
            principal=request.principal,
            course_code=code,
            assignment_id=assignment.id,
        )
        return Response(CourseAssignmentItemSerializer(detail).data)

    @extend_schema(
        operation_id="v1_lms_course_assignments_destroy",
        summary="Delete a course assignment (Faculty only)",
        tags=["lms"],
        responses={204: None},
    )
    def delete(self, request, code: str, assignment_id: int):
        assignment_service.delete_course_assignment(
            actor=request.principal,
            course_code=code,
            assignment_id=assignment_id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class CourseAssignmentDownloadView(APIView):
    """Download attached file for a released assignment."""

    permission_classes = [MODULE, HasPermission(P_ASG_VIEW)]

    @extend_schema(
        operation_id="v1_lms_course_assignments_download",
        summary="Download attached assignment file",
        tags=["lms"],
        responses={200: {"type": "string", "format": "binary"}},
    )
    def get(self, request, code: str, assignment_id: int):
        assignment, file_path = get_assignment_for_download(
            principal=request.principal,
            course_code=code,
            assignment_id=assignment_id,
        )
        filename = assignment.file_name or os.path.basename(file_path)
        return FileResponse(open(file_path, "rb"), as_attachment=True, filename=filename)


class CourseAssignmentDeadlineView(APIView):
    """View submission deadline and window controls for an assignment."""

    permission_classes = [MODULE, HasPermission(P_DDL_VIEW)]

    @extend_schema(
        operation_id="v1_lms_course_assignments_deadline_retrieve",
        summary="Retrieve assignment deadline and submission window status",
        tags=["lms"],
        responses={200: AssignmentDeadlineInfoSerializer},
    )
    def get(self, request, code: str, assignment_id: int):
        info = get_assignment_deadline_info(
            principal=request.principal,
            course_code=code,
            assignment_id=assignment_id,
        )
        if info is None:
            raise NotFoundError("Course assignment not found or access denied.")
        return Response(AssignmentDeadlineInfoSerializer(info).data)


class CourseAssignmentWindowView(APIView):
    """Configure submission window and deadline parameters (Faculty only)."""

    permission_classes = [MODULE, HasPermission(P_DDL_MANAGE)]

    @extend_schema(
        operation_id="v1_lms_course_assignments_window_update",
        summary="Update assignment deadline window and late policy",
        tags=["lms"],
        request=UpdateDeadlineWindowSerializer,
        responses={200: AssignmentDeadlineInfoSerializer},
    )
    def patch(self, request, code: str, assignment_id: int):
        payload = UpdateDeadlineWindowSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        asg = deadline_service.update_assignment_window(
            actor=request.principal,
            course_code=code,
            assignment_id=assignment_id,
            **payload.validated_data,
        )

        info = get_assignment_deadline_info(
            principal=request.principal,
            course_code=code,
            assignment_id=asg.id,
        )
        return Response(AssignmentDeadlineInfoSerializer(info).data)


class CourseAssignmentExtensionsView(APIView):
    """List or grant student deadline extensions for an assignment."""

    def get_permissions(self):
        perm = P_DDL_VIEW if self.request.method == "GET" else P_DDL_MANAGE
        return [MODULE(), HasPermission(perm)()]

    @extend_schema(
        operation_id="v1_lms_course_assignments_extensions_list",
        summary="List all granted deadline extensions (Faculty and TA only)",
        tags=["lms"],
        responses={200: AssignmentExtensionItemSerializer(many=True)},
    )
    def get(self, request, code: str, assignment_id: int):
        extensions = list_assignment_extensions(
            principal=request.principal,
            course_code=code,
            assignment_id=assignment_id,
        )
        if extensions is None:
            raise PermissionDeniedError(
                "You are not authorized to view extensions for this course."
            )
        return Response(AssignmentExtensionItemSerializer(extensions, many=True).data)

    @extend_schema(
        operation_id="v1_lms_course_assignments_extensions_create",
        summary="Grant student deadline extension (Faculty only)",
        tags=["lms"],
        request=GrantExtensionSerializer,
        responses={201: AssignmentExtensionItemSerializer},
    )
    def post(self, request, code: str, assignment_id: int):
        payload = GrantExtensionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        ext = deadline_service.grant_assignment_extension(
            actor=request.principal,
            course_code=code,
            assignment_id=assignment_id,
            **payload.validated_data,
        )

        # Retrieve formatted detail with student/grantor names
        extensions = list_assignment_extensions(
            principal=request.principal,
            course_code=code,
            assignment_id=assignment_id,
        )
        detail = next((item for item in (extensions or []) if item["id"] == ext.id), None)
        if detail is None:
            detail = {
                "id": ext.id,
                "assignment_id": ext.assignment_id,
                "user_id": ext.user_id,
                "student_name": f"User {ext.user_id}",
                "student_email": "",
                "extended_due_at": ext.extended_due_at.isoformat(),
                "reason": ext.reason,
                "granted_by_user_id": ext.granted_by_user_id,
                "granted_by_name": f"User {ext.granted_by_user_id}",
                "created_at": ext.created_at.isoformat(),
                "updated_at": ext.updated_at.isoformat(),
            }

        return Response(
            AssignmentExtensionItemSerializer(detail).data,
            status=status.HTTP_201_CREATED,
        )


class CourseAssignmentExtensionDetailView(APIView):
    """Revoke a student deadline extension (Faculty only)."""

    permission_classes = [MODULE, HasPermission(P_DDL_MANAGE)]

    @extend_schema(
        operation_id="v1_lms_course_assignments_extensions_destroy",
        summary="Revoke an approved student deadline extension",
        tags=["lms"],
        responses={204: None},
    )
    def delete(self, request, code: str, assignment_id: int, extension_id: int):
        deadline_service.revoke_assignment_extension(
            actor=request.principal,
            course_code=code,
            assignment_id=assignment_id,
            extension_id=extension_id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class CourseSubmissionMineView(APIView):
    """Retrieve own submission history or submit assignment work (Student only)."""

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        perm = P_SUB_VIEW if self.request.method == "GET" else P_SUB_SUBMIT
        return [MODULE(), HasPermission(perm)()]

    @extend_schema(
        operation_id="v1_lms_course_assignment_submission_mine",
        summary="View own assignment submission history and status",
        tags=["lms"],
        responses={200: CourseSubmissionHistorySerializer},
    )
    def get(self, request, code: str, assignment_id: int):
        data = get_student_submission_history(
            principal=request.principal,
            course_code=code,
            assignment_id=assignment_id,
        )
        if data is None:
            raise NotFoundError("Course assignment not found or you are not authorized.")
        return Response(CourseSubmissionHistorySerializer(data).data)

    @extend_schema(
        operation_id="v1_lms_course_assignment_submission_create",
        summary="Submit assignment work (file, text, or link)",
        tags=["lms"],
        request=CourseSubmissionCreateSerializer,
        responses={201: CourseSubmissionItemSerializer},
    )
    def post(self, request, code: str, assignment_id: int):
        payload = CourseSubmissionCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        submission = submission_service.create_submission(
            actor=request.principal,
            course_code=code,
            assignment_id=assignment_id,
            **payload.validated_data,
        )
        return Response(
            CourseSubmissionItemSerializer(_submission_to_dict(submission)).data,
            status=status.HTTP_201_CREATED,
        )


class CourseAssignmentSubmissionsListView(APIView):
    """List all student submissions for an assignment (Faculty and TA only)."""

    permission_classes = [MODULE, HasPermission(P_SUB_VIEW)]

    @extend_schema(
        operation_id="v1_lms_course_assignment_submissions_list",
        summary="List student submissions for an assignment (Faculty and TA only)",
        tags=["lms"],
        responses={200: CourseSubmissionsListResponseSerializer},
    )
    def get(self, request, code: str, assignment_id: int):
        data = list_assignment_submissions(
            principal=request.principal,
            course_code=code,
            assignment_id=assignment_id,
        )
        if data is None:
            raise PermissionDeniedError(
                "You are not authorized to view submissions for this course."
            )
        return Response(CourseSubmissionsListResponseSerializer(data).data)


class CourseSubmissionDownloadView(APIView):
    """Download attached submission file with student ownership / instructor verification."""

    permission_classes = [MODULE, HasPermission(P_SUB_VIEW)]

    @extend_schema(
        operation_id="v1_lms_course_assignment_submission_download",
        summary="Download student submission attachment",
        tags=["lms"],
        responses={200: None},
    )
    def get(self, request, code: str, assignment_id: int, submission_id: int):
        sub = get_submission_for_download(
            principal=request.principal,
            course_code=code,
            assignment_id=assignment_id,
            submission_id=submission_id,
        )
        if sub is None:
            raise NotFoundError(
                "Submission file not found or you are not authorized to download it."
            )

        f_name = sub.file_name or os.path.basename(sub.file.name)
        return FileResponse(sub.file.open("rb"), as_attachment=True, filename=f_name)


class CourseSubmissionGradeView(APIView):
    """Retrieve or record/update evaluation score for a student submission."""

    def get_permissions(self):
        perm = P_GRD_VIEW if self.request.method == "GET" else P_GRD_GRADE
        return [MODULE(), HasPermission(perm)()]

    @extend_schema(
        operation_id="v1_lms_course_assignment_submission_grade_retrieve",
        summary="Retrieve submission grade and evaluation details",
        tags=["lms"],
        responses={200: CourseSubmissionGradeDetailSerializer},
    )
    def get(self, request, code: str, assignment_id: int, submission_id: int):
        grade = get_submission_grade(
            principal=request.principal,
            course_code=code,
            assignment_id=assignment_id,
            submission_id=submission_id,
        )
        if grade is None:
            raise NotFoundError("Evaluation record not found or access denied.")
        return Response(CourseSubmissionGradeDetailSerializer(grade).data)

    @extend_schema(
        operation_id="v1_lms_course_assignment_submission_grade_record",
        summary="Record or update submission evaluation score (Faculty and TA only)",
        tags=["lms"],
        request=RecordSubmissionGradeSerializer,
        responses={201: CourseSubmissionGradeDetailSerializer},
    )
    def post(self, request, code: str, assignment_id: int, submission_id: int):
        payload = RecordSubmissionGradeSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        grade_service.record_submission_grade(
            actor=request.principal,
            course_code=code,
            assignment_id=assignment_id,
            submission_id=submission_id,
            score=payload.validated_data["score"],
        )

        grade_detail = get_submission_grade(
            principal=request.principal,
            course_code=code,
            assignment_id=assignment_id,
            submission_id=submission_id,
        )
        return Response(
            CourseSubmissionGradeDetailSerializer(grade_detail).data,
            status=status.HTTP_201_CREATED,
        )
