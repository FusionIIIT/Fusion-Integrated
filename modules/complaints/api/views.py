"""API views for the Complaint Management System."""
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiTypes

from fusion_auth.permissions import HasModuleGrant, HasPermission, IsAuthenticatedPrincipal
from modules.complaints import selectors, services
from modules.complaints.domain.errors import (
    ActiveRoleConstraintError,
    ComplaintAlreadyEscalated,
    ComplaintDomainError,
    ComplaintNotClosed,
    ComplaintNotResolved,
    ComplaintPermissionDenied,
    ComplaintValidationError,
    InvalidComplaintTransition,
)
from modules.complaints.models import ComplaintAnnouncement, ComplaintCategory, ComplaintFeedback
from modules.complaints.api.serializers import (
    AssignComplaintSerializer,
    CmsRoleAssignmentSerializer,
    ComplaintAnnouncementSerializer,
    ComplaintCategorySerializer,
    ComplaintDetailSerializer,
    ComplaintFeedbackSerializer,
    ComplaintListSerializer,
    ManualEscalateSerializer,
    ProgressUpdateSerializer,
    RejectComplaintSerializer,
    ReopeningRequestSerializer,
    ReopeningReviewSerializer,
    ResolveComplaintSerializer,
    SlaCheckResultSerializer,
    SubmitComplaintSerializer,
    SubmitFeedbackSerializer,
    VerifyCloseSerializer,
)


def _get_principal_user_id(principal) -> int:
    return getattr(principal, "user_id", None) or getattr(principal, "erp_user_id", 0)


def _handle_domain_error(exc: Exception):
    if isinstance(exc, (ComplaintValidationError, InvalidComplaintTransition)):
        raise ValidationError(str(exc))
    if isinstance(exc, (ComplaintPermissionDenied, ActiveRoleConstraintError)):
        raise PermissionDenied(str(exc))
    if isinstance(exc, (ComplaintNotClosed, ComplaintNotResolved, ComplaintAlreadyEscalated)):
        raise ValidationError(str(exc))
    raise ValidationError(str(exc))


class ComplaintListCreateView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("complaints")]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(summary="List visible complaints", responses={200: ComplaintListSerializer(many=True)})
    def get(self, request):
        if not (
            request.principal.has_any_permission(
                "complaints.complaint.view",
                "complaints.complaint.view_self",
            )
            or getattr(request.principal, "kind", None) == "admin"
        ):
            raise PermissionDenied("You do not have permission to view complaints.")

        complaints = selectors.visible_complaints(
            request.principal,
            status=request.query_params.get("status"),
            priority=request.query_params.get("priority"),
            category_id=request.query_params.get("category_id"),
            is_escalated=request.query_params.get("is_escalated"),
            search=request.query_params.get("search"),
        )
        serializer = ComplaintListSerializer(complaints, many=True)
        return Response(serializer.data)

    @extend_schema(summary="Submit a complaint", request=SubmitComplaintSerializer, responses={201: ComplaintDetailSerializer})
    def post(self, request):
        if not (
            request.principal.has_permission("complaints.complaint.create")
            or getattr(request.principal, "kind", None) == "admin"
        ):
            raise PermissionDenied("You do not have permission to submit a complaint.")

        serializer = SubmitComplaintSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        attachments = request.FILES.getlist("attachments")

        try:
            complaint = services.submit_complaint(
                complainant_user_id=_get_principal_user_id(request.principal),
                category_id=data["category_id"],
                location=data["location"],
                description=data["description"],
                priority=data.get("priority", "medium"),
                verification_required=data.get("verification_required", "none"),
                attachments=attachments,
            )
        except ComplaintDomainError as e:
            _handle_domain_error(e)

        return Response(
            ComplaintDetailSerializer(complaint).data,
            status=status.HTTP_201_CREATED,
        )


class ComplaintDetailView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("complaints")]

    @extend_schema(summary="Get complaint details", responses={200: ComplaintDetailSerializer})
    def get(self, request, pk):
        if not (
            request.principal.has_any_permission(
                "complaints.complaint.view",
                "complaints.complaint.view_self",
            )
            or getattr(request.principal, "kind", None) == "admin"
        ):
            raise PermissionDenied("You do not have permission to view this complaint.")

        complaint = selectors.get_complaint_by_id(pk, request.principal)
        if not complaint:
            raise NotFound("Complaint not found or not accessible.")
        return Response(ComplaintDetailSerializer(complaint).data)


class ComplaintAssignView(APIView):
    permission_classes = [
        IsAuthenticatedPrincipal,
        HasModuleGrant("complaints"),
        HasPermission("complaints.complaint.assign"),
    ]

    @extend_schema(summary="Assign worker and update category/priority", request=AssignComplaintSerializer, responses={200: ComplaintDetailSerializer})
    def post(self, request, pk):
        complaint = selectors.get_complaint_by_id(pk, request.principal)
        if not complaint:
            raise NotFound("Complaint not found.")

        serializer = AssignComplaintSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            updated = services.assign_and_prioritize_complaint(
                complaint=complaint,
                actor_user_id=_get_principal_user_id(request.principal),
                worker_id=data.get("worker_id"),
                worker_name=data.get("worker_name", ""),
                priority=data.get("priority"),
                category_id=data.get("category_id"),
                remarks=data.get("remarks", ""),
            )
        except ComplaintDomainError as e:
            _handle_domain_error(e)

        return Response(ComplaintDetailSerializer(updated).data)


class ComplaintProgressView(APIView):
    permission_classes = [
        IsAuthenticatedPrincipal,
        HasModuleGrant("complaints"),
        HasPermission("complaints.complaint.update"),
    ]

    @extend_schema(summary="Update complaint progress", request=ProgressUpdateSerializer, responses={200: ComplaintDetailSerializer})
    def post(self, request, pk):
        complaint = selectors.get_complaint_by_id(pk, request.principal)
        if not complaint:
            raise NotFound("Complaint not found.")

        serializer = ProgressUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = services.update_complaint_progress(
                complaint=complaint,
                actor_user_id=_get_principal_user_id(request.principal),
                progress_notes=serializer.validated_data["progress_notes"],
            )
        except ComplaintDomainError as e:
            _handle_domain_error(e)

        return Response(ComplaintDetailSerializer(updated).data)


class ComplaintResolveView(APIView):
    permission_classes = [
        IsAuthenticatedPrincipal,
        HasModuleGrant("complaints"),
        HasPermission("complaints.complaint.resolve"),
    ]

    @extend_schema(summary="Resolve complaint", request=ResolveComplaintSerializer, responses={200: ComplaintDetailSerializer})
    def post(self, request, pk):
        complaint = selectors.get_complaint_by_id(pk, request.principal)
        if not complaint:
            raise NotFound("Complaint not found.")

        serializer = ResolveComplaintSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = services.resolve_complaint(
                complaint=complaint,
                actor_user_id=_get_principal_user_id(request.principal),
                resolution_details=serializer.validated_data["resolution_details"],
            )
        except ComplaintDomainError as e:
            _handle_domain_error(e)

        return Response(ComplaintDetailSerializer(updated).data)


class ComplaintRejectView(APIView):
    permission_classes = [
        IsAuthenticatedPrincipal,
        HasModuleGrant("complaints"),
        HasPermission("complaints.complaint.resolve"),
    ]

    @extend_schema(summary="Reject complaint with mandatory reason", request=RejectComplaintSerializer, responses={200: ComplaintDetailSerializer})
    def post(self, request, pk):
        complaint = selectors.get_complaint_by_id(pk, request.principal)
        if not complaint:
            raise NotFound("Complaint not found.")

        serializer = RejectComplaintSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = services.reject_complaint(
                complaint=complaint,
                actor_user_id=_get_principal_user_id(request.principal),
                rejection_reason=serializer.validated_data["rejection_reason"],
            )
        except ComplaintDomainError as e:
            _handle_domain_error(e)

        return Response(ComplaintDetailSerializer(updated).data)


class ComplaintVerifyCloseView(APIView):
    permission_classes = [
        IsAuthenticatedPrincipal,
        HasModuleGrant("complaints"),
        HasPermission("complaints.complaint.close"),
    ]

    @extend_schema(summary="Verify and close resolved complaint", request=VerifyCloseSerializer, responses={200: ComplaintDetailSerializer})
    def post(self, request, pk):
        complaint = selectors.get_complaint_by_id(pk, request.principal)
        if not complaint:
            raise NotFound("Complaint not found.")

        serializer = VerifyCloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        actor_role = getattr(request.principal, "active_role", "complainant")

        try:
            updated = services.verify_and_close_complaint(
                complaint=complaint,
                actor_user_id=_get_principal_user_id(request.principal),
                actor_role=actor_role,
                remarks=serializer.validated_data.get("remarks", ""),
            )
        except ComplaintDomainError as e:
            _handle_domain_error(e)

        return Response(ComplaintDetailSerializer(updated).data)


class ComplaintReopenRequestView(APIView):
    permission_classes = [
        IsAuthenticatedPrincipal,
        HasModuleGrant("complaints"),
        HasPermission("complaints.complaint.reopen"),
    ]

    @extend_schema(summary="Request reopening for closed complaint", request=ReopeningRequestSerializer, responses={200: ComplaintDetailSerializer})
    def post(self, request, pk):
        complaint = selectors.get_complaint_by_id(pk, request.principal)
        if not complaint:
            raise NotFound("Complaint not found.")

        serializer = ReopeningRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = services.request_reopening(
                complaint=complaint,
                complainant_user_id=_get_principal_user_id(request.principal),
                reopening_reason=serializer.validated_data["reopening_reason"],
            )
        except ComplaintDomainError as e:
            _handle_domain_error(e)

        return Response(ComplaintDetailSerializer(updated).data)


class ComplaintReopenReviewView(APIView):
    permission_classes = [
        IsAuthenticatedPrincipal,
        HasModuleGrant("complaints"),
        HasPermission("complaints.complaint.supervise"),
    ]

    @extend_schema(summary="Review reopening request (approve or deny)", request=ReopeningReviewSerializer, responses={200: ComplaintDetailSerializer})
    def post(self, request, pk):
        complaint = selectors.get_complaint_by_id(pk, request.principal)
        if not complaint:
            raise NotFound("Complaint not found.")

        serializer = ReopeningReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = services.review_reopening_request(
                complaint=complaint,
                supervisor_user_id=_get_principal_user_id(request.principal),
                approved=serializer.validated_data["approved"],
                review_remarks=serializer.validated_data.get("review_remarks", ""),
            )
        except ComplaintDomainError as e:
            _handle_domain_error(e)

        return Response(ComplaintDetailSerializer(updated).data)


class ComplaintManualEscalateView(APIView):
    permission_classes = [
        IsAuthenticatedPrincipal,
        HasModuleGrant("complaints"),
        HasPermission("complaints.complaint.escalate"),
    ]

    @extend_schema(summary="Manually escalate complaint", request=ManualEscalateSerializer, responses={200: ComplaintDetailSerializer})
    def post(self, request, pk):
        complaint = selectors.get_complaint_by_id(pk, request.principal)
        if not complaint:
            raise NotFound("Complaint not found.")

        serializer = ManualEscalateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = services.escalate_complaint_manually(
                complaint=complaint,
                handler_user_id=_get_principal_user_id(request.principal),
                remarks=serializer.validated_data["remarks"],
            )
        except ComplaintDomainError as e:
            _handle_domain_error(e)

        return Response(ComplaintDetailSerializer(updated).data)


class ComplaintSlaCheckView(APIView):
    permission_classes = [
        IsAuthenticatedPrincipal,
        HasModuleGrant("complaints"),
    ]
    serializer_class = SlaCheckResultSerializer

    @extend_schema(summary="Trigger autonomous SLA breach checks and reminders", request=None, responses={200: SlaCheckResultSerializer})
    def post(self, request):
        """Trigger SLA check and reminders."""
        escalated = services.check_and_escalate_sla_breaches()
        reminders = services.check_and_send_sla_reminders()
        return Response({"escalated_count": escalated, "reminders_sent": reminders})


class ComplaintFeedbackView(APIView):
    permission_classes = [
        IsAuthenticatedPrincipal,
        HasModuleGrant("complaints"),
        HasPermission("complaints.complaint.feedback"),
    ]

    @extend_schema(summary="Submit satisfaction feedback", request=SubmitFeedbackSerializer, responses={201: ComplaintFeedbackSerializer})
    def post(self, request, pk):
        complaint = selectors.get_complaint_by_id(pk, request.principal)
        if not complaint:
            raise NotFound("Complaint not found.")

        serializer = SubmitFeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            feedback = services.submit_feedback(
                complaint=complaint,
                complainant_user_id=_get_principal_user_id(request.principal),
                rating=data["rating"],
                comments=data.get("comments", ""),
            )
        except ComplaintDomainError as e:
            _handle_domain_error(e)

        return Response(ComplaintFeedbackSerializer(feedback).data, status=status.HTTP_201_CREATED)


class ComplaintCategoryListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("complaints")]
    queryset = ComplaintCategory.objects.filter(is_active=True)
    serializer_class = ComplaintCategorySerializer


class ComplaintAnnouncementListView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("complaints")]

    @extend_schema(summary="List active announcements", responses={200: ComplaintAnnouncementSerializer(many=True)})
    def get(self, request):
        category_id = request.query_params.get("category_id")
        announcements = selectors.visible_announcements(category_id=category_id)
        serializer = ComplaintAnnouncementSerializer(announcements, many=True)
        return Response(serializer.data)

    @extend_schema(summary="Publish announcement", request=ComplaintAnnouncementSerializer, responses={201: ComplaintAnnouncementSerializer})
    def post(self, request):
        if not (
            request.principal.has_permission("complaints.announcement.publish")
            or getattr(request.principal, "kind", None) == "admin"
        ):
            raise PermissionDenied("You do not have permission to publish announcements.")

        serializer = ComplaintAnnouncementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        author_name = getattr(request.principal, "display_name", f"User {_get_principal_user_id(request.principal)}")

        try:
            announcement = services.publish_announcement(
                author_user_id=_get_principal_user_id(request.principal),
                author_name=author_name,
                title=data["title"],
                content=data["content"],
                category_id=data.get("category_id"),
                pinned=data.get("pinned", False),
            )
        except ComplaintDomainError as e:
            _handle_domain_error(e)

        return Response(
            ComplaintAnnouncementSerializer(announcement).data,
            status=status.HTTP_201_CREATED,
        )


class ComplaintReportsSummaryView(APIView):
    permission_classes = [
        IsAuthenticatedPrincipal,
        HasModuleGrant("complaints"),
        HasPermission("complaints.complaint.report"),
    ]

    @extend_schema(summary="Get CMS operational summary reports", responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        summary = selectors.get_complaint_reports_summary()
        return Response(summary)


class CmsRoleAssignmentListView(APIView):
    permission_classes = [
        IsAuthenticatedPrincipal,
        HasModuleGrant("complaints"),
        HasPermission("complaints.role.manage"),
    ]

    @extend_schema(summary="Get active CMS handler and supervisor role holders", responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        roles = selectors.get_active_cms_roles()
        handler_data = CmsRoleAssignmentSerializer(roles["handler"]).data if roles["handler"] else None
        supervisor_data = CmsRoleAssignmentSerializer(roles["supervisor"]).data if roles["supervisor"] else None
        return Response({
            "active_handler": handler_data,
            "active_supervisor": supervisor_data,
        })

    @extend_schema(summary="Assign CMS role", request=CmsRoleAssignmentSerializer, responses={201: CmsRoleAssignmentSerializer})
    def post(self, request):
        serializer = CmsRoleAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            assignment = services.assign_cms_role(
                role_type=data["role_type"],
                user_id=data["user_id"],
                assigned_by_user_id=_get_principal_user_id(request.principal),
                start_date=data["start_date"],
                end_date=data["end_date"],
            )
        except ComplaintDomainError as e:
            _handle_domain_error(e)

        return Response(
            CmsRoleAssignmentSerializer(assignment).data,
            status=status.HTTP_201_CREATED,
        )
