from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.oap.api.serializers import (
    AssistantshipClaimCreateSerializer,
    AssistantshipClaimSerializer,
    AssistantshipDisburseSerializer,
    AssistantshipHodDecisionSerializer,
    AssistantshipSupervisorVerifySerializer,
    BonafideDecisionSerializer,
    BonafideRequestCreateSerializer,
    BonafideRequestSerializer,
    GraduateSeminarRequestSerializer,
    GraduateSeminarScheduleSerializer,
    GraduateSeminarSerializer,
    LeaveDecisionSerializer,
    NoDuesAuthorityClearanceSerializer,
    NoDuesClearanceVerifySerializer,
    NoDuesInitiateSerializer,
    NoDuesRequestSerializer,
    OAPNotificationSerializer,
    StudentLeaveApplicationCreateSerializer,
    StudentLeaveApplicationSerializer,
    TeachingAssistantAssignmentCreateSerializer,
    TeachingAssistantAssignmentSerializer,
    ThesisSupervisorAssignmentCreateSerializer,
    ThesisSupervisorAssignmentSerializer,
)
from modules.oap.domain import permissions as p
from modules.oap.selectors import (
    get_all_bonafides,
    get_all_no_dues,
    get_all_scheduled_seminars,
    get_all_seminar_requests,
    get_all_ta_assignments,
    get_all_thesis_assignments,
    get_approved_claims_for_disbursement,
    get_bonafide_by_id,
    get_claim_by_id,
    get_claims_for_dept_review,
    get_claims_for_hod,
    get_claims_for_supervisor,
    get_clearances_for_domain,
    get_department_leaves,
    get_leave_by_id,
    get_no_dues_by_id,
    get_notifications_for_user,
    get_seminar_by_id,
    get_student_bonafides,
    get_student_claims,
    get_student_leaves,
    get_student_no_dues,
    get_student_seminar_requests,
)
from modules.oap.services import (
    decide_assistantship_claim,
    decide_bonafide_request,
    decide_leave_application,
    disburse_stipend,
    download_bonafide_certificate,
    download_no_dues_certificate,
    finalize_no_dues_clearance,
    initiate_no_dues_clearance,
    record_ta_assignment,
    record_thesis_supervisor_assignment,
    request_bonafide_certificate,
    request_graduate_seminar,
    review_and_forward_claim,
    schedule_graduate_seminar,
    submit_assistantship_claim,
    submit_leave_application,
    verify_assistantship_claim,
    verify_authority_clearance,
)

# ---------------------------------------------------------------------------
# Leave Management Views (OA-UC-01, OA-UC-03, OA-UC-04)
# ---------------------------------------------------------------------------


class StudentLeaveListCreateView(APIView):
    permission_classes = [HasModuleGrant("oap")]

    @extend_schema(responses=StudentLeaveApplicationSerializer(many=True))
    def get(self, request):
        p_check = getattr(request, "principal", None)
        leaves = get_student_leaves(p_check.user_id)
        return Response(StudentLeaveApplicationSerializer(leaves, many=True).data)

    @extend_schema(
        request=StudentLeaveApplicationCreateSerializer,
        responses=StudentLeaveApplicationSerializer,
    )
    def post(self, request):
        p_check = getattr(request, "principal", None)
        if not p_check.has_permission(p.P_STUDENT_LEAVE_APPLY):
            raise PermissionDeniedError("Permission oap.leave.apply required.")

        serializer = StudentLeaveApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        app = submit_leave_application(
            user_id=p_check.user_id,
            department=data["department"],
            programme=data.get("programme", "ug"),
            leave_type=data.get("leave_type", "Casual Leave"),
            start_date=data["start_date"],
            end_date=data["end_date"],
            reason=data["reason"],
            attachments=data.get("attachments", []),
        )
        return Response(StudentLeaveApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


class StudentLeaveDetailView(APIView):
    permission_classes = [HasModuleGrant("oap")]

    @extend_schema(responses=StudentLeaveApplicationSerializer)
    def get(self, request, leave_id):
        p_check = getattr(request, "principal", None)
        app = get_leave_by_id(leave_id)
        if not app:
            raise NotFoundError("Leave application not found.")
        if app.user_id != p_check.user_id and not p_check.has_any_permission(p.P_HOD_LEAVE_DECIDE, p.P_HOD_LEAVE_VIEW_DEPT):
            raise PermissionDeniedError("Access to this leave application is denied.")
        return Response(StudentLeaveApplicationSerializer(app).data)


class DepartmentLeaveListView(APIView):
    permission_classes = [HasModuleGrant("oap"), HasPermission(p.P_HOD_LEAVE_VIEW_DEPT, p.P_HOD_LEAVE_DECIDE)]

    @extend_schema(responses=StudentLeaveApplicationSerializer(many=True))
    def get(self, request):
        dept = request.query_params.get("department", "")
        leaves = get_department_leaves(dept) if dept else get_student_leaves(request.principal.user_id)
        return Response(StudentLeaveApplicationSerializer(leaves, many=True).data)


class HoDLeaveDecisionView(APIView):
    permission_classes = [HasModuleGrant("oap"), HasPermission(p.P_HOD_LEAVE_DECIDE)]

    @extend_schema(
        request=LeaveDecisionSerializer,
        responses=StudentLeaveApplicationSerializer,
    )
    def post(self, request, leave_id):
        serializer = LeaveDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        app = decide_leave_application(
            leave_id=leave_id,
            hod_user_id=request.principal.user_id,
            decision=serializer.validated_data["decision"],
            remarks=serializer.validated_data.get("remarks", ""),
        )
        return Response(StudentLeaveApplicationSerializer(app).data)


# ---------------------------------------------------------------------------
# Bonafide Certificate Views (OA-UC-11, OA-UC-12, OA-UC-13, OA-UC-14)
# ---------------------------------------------------------------------------


class StudentBonafideListCreateView(APIView):
    permission_classes = [HasModuleGrant("oap")]

    @extend_schema(responses=BonafideRequestSerializer(many=True))
    def get(self, request):
        reqs = get_student_bonafides(request.principal.user_id)
        return Response(BonafideRequestSerializer(reqs, many=True).data)

    @extend_schema(
        request=BonafideRequestCreateSerializer,
        responses=BonafideRequestSerializer,
    )
    def post(self, request):
        if not request.principal.has_permission(p.P_STUDENT_BONAFIDE_REQUEST):
            raise PermissionDeniedError("Permission oap.bonafide.request required.")
        serializer = BonafideRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = request_bonafide_certificate(
            user_id=request.principal.user_id,
            purpose=serializer.validated_data["purpose"],
            details=serializer.validated_data.get("details", ""),
        )
        return Response(BonafideRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class AcademicAdminBonafideListView(APIView):
    permission_classes = [HasModuleGrant("oap"), HasPermission(p.P_ACAD_ADMIN_BONAFIDE_DECIDE)]

    @extend_schema(responses=BonafideRequestSerializer(many=True))
    def get(self, request):
        reqs = get_all_bonafides()
        return Response(BonafideRequestSerializer(reqs, many=True).data)


class AcademicAdminBonafideDecisionView(APIView):
    permission_classes = [HasModuleGrant("oap"), HasPermission(p.P_ACAD_ADMIN_BONAFIDE_DECIDE)]

    @extend_schema(
        request=BonafideDecisionSerializer,
        responses=BonafideRequestSerializer,
    )
    def post(self, request, request_id):
        serializer = BonafideDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = decide_bonafide_request(
            request_id=request_id,
            admin_user_id=request.principal.user_id,
            decision=serializer.validated_data["decision"],
            remarks=serializer.validated_data.get("remarks", ""),
        )
        return Response(BonafideRequestSerializer(req).data)


class StudentBonafideDownloadView(APIView):
    permission_classes = [HasModuleGrant("oap")]

    @extend_schema(responses={200: dict})
    def get(self, request, request_id):
        cert = download_bonafide_certificate(request_id, request.principal.user_id)
        return Response(cert)


# ---------------------------------------------------------------------------
# No-Dues Clearance Views (OA-UC-21, OA-UC-22, OA-UC-23, OA-UC-24, OA-UC-25)
# ---------------------------------------------------------------------------


class StudentNoDuesListInitiateView(APIView):
    permission_classes = [HasModuleGrant("oap")]

    @extend_schema(responses=NoDuesRequestSerializer(many=True))
    def get(self, request):
        reqs = get_student_no_dues(request.principal.user_id)
        return Response(NoDuesRequestSerializer(reqs, many=True).data)

    @extend_schema(
        request=NoDuesInitiateSerializer,
        responses=NoDuesRequestSerializer,
    )
    def post(self, request):
        if not request.principal.has_permission(p.P_STUDENT_NODUES_INITIATE):
            raise PermissionDeniedError("Permission oap.nodues.initiate required.")
        serializer = NoDuesInitiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = initiate_no_dues_clearance(
            user_id=request.principal.user_id,
            department=serializer.validated_data["department"],
            programme=serializer.validated_data.get("programme", "ug"),
        )
        return Response(NoDuesRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class NoDuesDetailView(APIView):
    permission_classes = [HasModuleGrant("oap")]

    @extend_schema(responses=NoDuesRequestSerializer)
    def get(self, request, request_id):
        req = get_no_dues_by_id(request_id)
        if not req:
            raise NotFoundError("No-Dues request not found.")
        p_check = request.principal
        if req.user_id != p_check.user_id and not p_check.has_any_permission(
            p.P_ACAD_ADMIN_NODUES_FINALIZE, p.P_NODUES_VERIFY
        ):
            raise PermissionDeniedError("Access to this no-dues record is denied.")
        return Response(NoDuesRequestSerializer(req).data)


class AcademicAdminNoDuesListView(APIView):
    permission_classes = [HasModuleGrant("oap"), HasPermission(p.P_ACAD_ADMIN_NODUES_FINALIZE)]

    @extend_schema(responses=NoDuesRequestSerializer(many=True))
    def get(self, request):
        reqs = get_all_no_dues()
        return Response(NoDuesRequestSerializer(reqs, many=True).data)


class AuthorityClearanceListView(APIView):
    permission_classes = [HasModuleGrant("oap"), HasPermission(p.P_NODUES_VERIFY)]

    @extend_schema(responses=NoDuesAuthorityClearanceSerializer(many=True))
    def get(self, request):
        domain = request.query_params.get("domain", "")
        if not domain:
            raise BadRequestError("domain query parameter is required.")
        clearances = get_clearances_for_domain(domain)
        return Response(NoDuesAuthorityClearanceSerializer(clearances, many=True).data)


class AuthorityClearanceVerifyView(APIView):
    permission_classes = [HasModuleGrant("oap"), HasPermission(p.P_NODUES_VERIFY)]

    @extend_schema(
        request=NoDuesClearanceVerifySerializer,
        responses=NoDuesAuthorityClearanceSerializer,
    )
    def post(self, request, request_id):
        serializer = NoDuesClearanceVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        clearance = verify_authority_clearance(
            request_id=request_id,
            domain=data["domain"],
            status=data["status"],
            verifier_user_id=request.principal.user_id,
            dues_amount=data.get("dues_amount", 0.00),
            remarks=data.get("remarks", ""),
        )
        return Response(NoDuesAuthorityClearanceSerializer(clearance).data)


class AcademicAdminNoDuesFinalizeView(APIView):
    permission_classes = [HasModuleGrant("oap"), HasPermission(p.P_ACAD_ADMIN_NODUES_FINALIZE)]

    @extend_schema(request=None, responses=NoDuesRequestSerializer)
    def post(self, request, request_id):
        req = finalize_no_dues_clearance(request_id, request.principal.user_id)
        return Response(NoDuesRequestSerializer(req).data)


class StudentNoDuesDownloadView(APIView):
    permission_classes = [HasModuleGrant("oap")]

    @extend_schema(responses={200: dict})
    def get(self, request, request_id):
        cert = download_no_dues_certificate(request_id, request.principal.user_id)
        return Response(cert)


# ---------------------------------------------------------------------------
# Departmental Assignments Views (OA-UC-41, OA-UC-42)
# ---------------------------------------------------------------------------


class ThesisAssignmentListCreateView(APIView):
    permission_classes = [HasModuleGrant("oap"), HasPermission(p.P_DEPT_ADMIN_ASSIGNMENT_MANAGE)]

    @extend_schema(responses=ThesisSupervisorAssignmentSerializer(many=True))
    def get(self, request):
        dept = request.query_params.get("department")
        qs = get_all_thesis_assignments(dept)
        return Response(ThesisSupervisorAssignmentSerializer(qs, many=True).data)

    @extend_schema(
        request=ThesisSupervisorAssignmentCreateSerializer,
        responses=ThesisSupervisorAssignmentSerializer,
    )
    def post(self, request):
        serializer = ThesisSupervisorAssignmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        assign = record_thesis_supervisor_assignment(
            student_user_id=data["student_user_id"],
            supervisor_user_id=data["supervisor_user_id"],
            department=data["department"],
            assigned_by_user_id=request.principal.user_id,
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
        )
        return Response(ThesisSupervisorAssignmentSerializer(assign).data, status=status.HTTP_201_CREATED)


class TAAssignmentListCreateView(APIView):
    permission_classes = [HasModuleGrant("oap"), HasPermission(p.P_DEPT_ADMIN_ASSIGNMENT_MANAGE)]

    @extend_schema(responses=TeachingAssistantAssignmentSerializer(many=True))
    def get(self, request):
        dept = request.query_params.get("department")
        qs = get_all_ta_assignments(dept)
        return Response(TeachingAssistantAssignmentSerializer(qs, many=True).data)

    @extend_schema(
        request=TeachingAssistantAssignmentCreateSerializer,
        responses=TeachingAssistantAssignmentSerializer,
    )
    def post(self, request):
        serializer = TeachingAssistantAssignmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        assign = record_ta_assignment(
            student_user_id=data["student_user_id"],
            department=data["department"],
            assigned_by_user_id=request.principal.user_id,
            ta_supervisor_user_id=data.get("ta_supervisor_user_id"),
            course_code=data.get("course_code", ""),
            semester=data.get("semester", ""),
            year=data.get("year"),
        )
        return Response(TeachingAssistantAssignmentSerializer(assign).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Assistantship Claim Views (OA-UC-31, 33, 34, 35, 36, 37)
# ---------------------------------------------------------------------------


class StudentAssistantshipClaimListCreateView(APIView):
    permission_classes = [HasModuleGrant("oap")]

    @extend_schema(responses=AssistantshipClaimSerializer(many=True))
    def get(self, request):
        claims = get_student_claims(request.principal.user_id)
        return Response(AssistantshipClaimSerializer(claims, many=True).data)

    @extend_schema(
        request=AssistantshipClaimCreateSerializer,
        responses=AssistantshipClaimSerializer,
    )
    def post(self, request):
        if not request.principal.has_permission(p.P_STUDENT_ASSISTANTSHIP_SUBMIT):
            raise PermissionDeniedError("Permission oap.assistantship.submit required.")
        serializer = AssistantshipClaimCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        claim = submit_assistantship_claim(
            user_id=request.principal.user_id,
            month=data["month"],
            year=data["year"],
            department=data["department"],
            stipend_amount=data["stipend_amount"],
            work_summary=data["work_summary"],
            hours_worked=data.get("hours_worked", 0.00),
            thesis_supervisor_user_id=data.get("thesis_supervisor_user_id"),
            ta_supervisor_user_id=data.get("ta_supervisor_user_id"),
        )
        return Response(AssistantshipClaimSerializer(claim).data, status=status.HTTP_201_CREATED)


class AssistantshipClaimDetailView(APIView):
    permission_classes = [HasModuleGrant("oap")]

    @extend_schema(responses=AssistantshipClaimSerializer)
    def get(self, request, claim_id):
        claim = get_claim_by_id(claim_id)
        if not claim:
            raise NotFoundError("Assistantship claim not found.")
        p_check = request.principal
        if claim.user_id != p_check.user_id and not p_check.has_any_permission(
            p.P_SUPERVISOR_VERIFY_THESIS,
            p.P_SUPERVISOR_VERIFY_TA,
            p.P_DEPT_ADMIN_ASSISTANTSHIP_REVIEW,
            p.P_HOD_ASSISTANTSHIP_DECIDE,
            p.P_ACAD_ADMIN_ASSISTANTSHIP_DISBURSE,
        ):
            raise PermissionDeniedError("Access to this claim is denied.")
        return Response(AssistantshipClaimSerializer(claim).data)


class SupervisorClaimListView(APIView):
    permission_classes = [HasModuleGrant("oap"), HasPermission(p.P_SUPERVISOR_VERIFY_THESIS, p.P_SUPERVISOR_VERIFY_TA)]

    @extend_schema(responses=AssistantshipClaimSerializer(many=True))
    def get(self, request):
        claims = get_claims_for_supervisor(request.principal.user_id)
        return Response(AssistantshipClaimSerializer(claims, many=True).data)


class SupervisorClaimVerifyView(APIView):
    permission_classes = [HasModuleGrant("oap"), HasPermission(p.P_SUPERVISOR_VERIFY_THESIS, p.P_SUPERVISOR_VERIFY_TA)]

    @extend_schema(
        request=AssistantshipSupervisorVerifySerializer,
        responses=AssistantshipClaimSerializer,
    )
    def post(self, request, claim_id):
        serializer = AssistantshipSupervisorVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = serializer.validated_data["role"]
        if role == "thesis_supervisor" and not request.principal.has_permission(p.P_SUPERVISOR_VERIFY_THESIS):
            raise PermissionDeniedError("Permission oap.assistantship.verify_thesis required.")
        if role == "ta_supervisor" and not request.principal.has_permission(p.P_SUPERVISOR_VERIFY_TA):
            raise PermissionDeniedError("Permission oap.assistantship.verify_ta required.")

        claim = verify_assistantship_claim(
            claim_id=claim_id,
            supervisor_user_id=request.principal.user_id,
            role=role,
            remarks=serializer.validated_data.get("remarks", ""),
        )
        return Response(AssistantshipClaimSerializer(claim).data)


class DepartmentAdminClaimReviewListView(APIView):
    permission_classes = [HasModuleGrant("oap"), HasPermission(p.P_DEPT_ADMIN_ASSISTANTSHIP_REVIEW)]

    @extend_schema(responses=AssistantshipClaimSerializer(many=True))
    def get(self, request):
        dept = request.query_params.get("department", "")
        claims = get_claims_for_dept_review(dept) if dept else AssistantshipClaim.objects.none()
        return Response(AssistantshipClaimSerializer(claims, many=True).data)


class DepartmentAdminClaimForwardView(APIView):
    permission_classes = [HasModuleGrant("oap"), HasPermission(p.P_DEPT_ADMIN_ASSISTANTSHIP_REVIEW)]

    @extend_schema(request=None, responses=AssistantshipClaimSerializer)
    def post(self, request, claim_id):
        claim = review_and_forward_claim(claim_id, request.principal.user_id)
        return Response(AssistantshipClaimSerializer(claim).data)


class HoDClaimListView(APIView):
    permission_classes = [HasModuleGrant("oap"), HasPermission(p.P_HOD_ASSISTANTSHIP_DECIDE)]

    @extend_schema(responses=AssistantshipClaimSerializer(many=True))
    def get(self, request):
        dept = request.query_params.get("department", "")
        claims = get_claims_for_hod(dept) if dept else AssistantshipClaim.objects.none()
        return Response(AssistantshipClaimSerializer(claims, many=True).data)


class HoDClaimDecisionView(APIView):
    permission_classes = [HasModuleGrant("oap"), HasPermission(p.P_HOD_ASSISTANTSHIP_DECIDE)]

    @extend_schema(
        request=AssistantshipHodDecisionSerializer,
        responses=AssistantshipClaimSerializer,
    )
    def post(self, request, claim_id):
        serializer = AssistantshipHodDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        claim = decide_assistantship_claim(
            claim_id=claim_id,
            hod_user_id=request.principal.user_id,
            decision=serializer.validated_data["decision"],
            remarks=serializer.validated_data.get("remarks", ""),
        )
        return Response(AssistantshipClaimSerializer(claim).data)


class AcademicAdminDisbursementListView(APIView):
    permission_classes = [HasModuleGrant("oap"), HasPermission(p.P_ACAD_ADMIN_ASSISTANTSHIP_DISBURSE)]

    @extend_schema(responses=AssistantshipClaimSerializer(many=True))
    def get(self, request):
        claims = get_approved_claims_for_disbursement()
        return Response(AssistantshipClaimSerializer(claims, many=True).data)


class AcademicAdminDisburseView(APIView):
    permission_classes = [HasModuleGrant("oap"), HasPermission(p.P_ACAD_ADMIN_ASSISTANTSHIP_DISBURSE)]

    @extend_schema(
        request=AssistantshipDisburseSerializer,
        responses=AssistantshipClaimSerializer,
    )
    def post(self, request, claim_id):
        serializer = AssistantshipDisburseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        claim = disburse_stipend(
            claim_id=claim_id,
            admin_user_id=request.principal.user_id,
            disbursement_reference=serializer.validated_data.get("disbursement_reference", ""),
        )
        return Response(AssistantshipClaimSerializer(claim).data)


# ---------------------------------------------------------------------------
# Graduate Seminar Views (OA-UC-51, 53, 54)
# ---------------------------------------------------------------------------


class StudentSeminarRequestListCreateView(APIView):
    permission_classes = [HasModuleGrant("oap")]

    @extend_schema(responses=GraduateSeminarSerializer(many=True))
    def get(self, request):
        qs = get_student_seminar_requests(request.principal.user_id)
        return Response(GraduateSeminarSerializer(qs, many=True).data)

    @extend_schema(
        request=GraduateSeminarRequestSerializer,
        responses=GraduateSeminarSerializer,
    )
    def post(self, request):
        if not request.principal.has_permission(p.P_STUDENT_SEMINAR_REQUEST):
            raise PermissionDeniedError("Permission oap.seminar.request required.")
        serializer = GraduateSeminarRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        seminar = request_graduate_seminar(
            user_id=request.principal.user_id,
            title=data["title"],
            abstract=data["abstract"],
            preferred_dates=data.get("preferred_dates", ""),
        )
        return Response(GraduateSeminarSerializer(seminar).data, status=status.HTTP_201_CREATED)


class DepartmentAdminSeminarListView(APIView):
    permission_classes = [HasModuleGrant("oap"), HasPermission(p.P_DEPT_ADMIN_SEMINAR_SCHEDULE)]

    @extend_schema(responses=GraduateSeminarSerializer(many=True))
    def get(self, request):
        qs = get_all_seminar_requests()
        return Response(GraduateSeminarSerializer(qs, many=True).data)


class DepartmentAdminSeminarScheduleView(APIView):
    permission_classes = [HasModuleGrant("oap"), HasPermission(p.P_DEPT_ADMIN_SEMINAR_SCHEDULE)]

    @extend_schema(
        request=GraduateSeminarScheduleSerializer,
        responses=GraduateSeminarSerializer,
    )
    def post(self, request, seminar_id):
        serializer = GraduateSeminarScheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        seminar = schedule_graduate_seminar(
            seminar_id=seminar_id,
            dept_admin_user_id=request.principal.user_id,
            scheduled_date=data["scheduled_date"],
            scheduled_time=data["scheduled_time"],
            venue=data["venue"],
            coordinator_user_id=data.get("coordinator_user_id"),
            remarks=data.get("remarks", ""),
        )
        return Response(GraduateSeminarSerializer(seminar).data)


class PublicSeminarScheduleListView(APIView):
    permission_classes = [HasModuleGrant("oap"), HasPermission(p.P_STUDENT_SEMINAR_VIEW, p.P_FACULTY_SEMINAR_VIEW)]

    @extend_schema(responses=GraduateSeminarSerializer(many=True))
    def get(self, request):
        qs = get_all_scheduled_seminars()
        return Response(GraduateSeminarSerializer(qs, many=True).data)


# ---------------------------------------------------------------------------
# Notifications Views (OA-UC-91, 92)
# ---------------------------------------------------------------------------


class OAPNotificationListView(APIView):
    permission_classes = [HasModuleGrant("oap")]

    @extend_schema(responses=OAPNotificationSerializer(many=True))
    def get(self, request):
        unread_only = request.query_params.get("unread") == "true"
        notifications = get_notifications_for_user(request.principal.user_id, unread_only=unread_only)
        return Response(OAPNotificationSerializer(notifications, many=True).data)


class OAPNotificationMarkReadView(APIView):
    permission_classes = [HasModuleGrant("oap")]

    @extend_schema(request=None, responses={200: dict})
    def post(self, request, notification_id):
        notif = get_notifications_for_user(request.principal.user_id).filter(id=notification_id).first()
        if not notif:
            raise NotFoundError("Notification not found.")
        notif.is_read = True
        notif.save(update_fields=["is_read", "updated_at"])
        return Response({"status": "marked_as_read"})
