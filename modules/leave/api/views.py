"""API views for Employee Leave Management (ELM)."""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasPermission
from modules.leave.api.serializers import (
    HolidayCalendarSerializer,
    LeaveApplicationCreateSerializer,
    LeaveApplicationSerializer,
    LeaveBalanceSerializer,
    LeaveCancellationRequestSerializer,
    LeaveCancellationReviewSerializer,
    LeaveReplacementSubstituteSerializer,
    LeaveResumptionReviewSerializer,
    LeaveResumptionSubmitSerializer,
    LeaveReviewActionSerializer,
    LeaveSubstituteResponseSerializer,
    LeaveTypeSerializer,
    LeaveWithdrawSerializer,
)
from modules.leave.models import (
    HolidayCalendar,
    LeaveApplication,
    LeaveBalance,
    LeaveType,
)
from modules.leave.services import (
    get_or_create_balance,
    nominate_replacement_substitute,
    request_approved_leave_cancellation,
    respond_to_substitute_request,
    review_by_sanctioning_authority,
    review_by_unit_head,
    review_cancellation_request,
    review_resumption_submission,
    submit_leave_application,
    submit_resumption_of_duty,
    withdraw_leave_application,
)


def _get_principal_username(request) -> str:
    principal = getattr(request, "principal", None)
    return getattr(principal, "username", "unknown") if principal else "unknown"


def _is_director(request) -> bool:
    principal = getattr(request, "principal", None)
    roles = getattr(principal, "roles", []) if principal else []
    return "Director" in roles


class LeaveTypeListView(generics.ListAPIView):
    """List active institute leave categories."""

    queryset = LeaveType.objects.filter(is_active=True)
    serializer_class = LeaveTypeSerializer
    permission_classes = [HasPermission("leave.application.view")]


class HolidayCalendarListView(generics.ListAPIView):
    """List published holidays and restricted holidays."""

    serializer_class = HolidayCalendarSerializer
    permission_classes = [HasPermission("leave.application.view")]

    def get_queryset(self):
        year = self.request.query_params.get("year", timezone.now().year)
        return HolidayCalendar.objects.filter(year=year)


class LeaveBalanceListView(generics.ListAPIView):
    """Retrieve leave balances for the authenticated employee."""

    serializer_class = LeaveBalanceSerializer
    permission_classes = [HasPermission("leave.application.view")]

    def get_queryset(self):
        username = _get_principal_username(self.request)
        year = int(self.request.query_params.get("year", timezone.now().year))
        for lt in LeaveType.objects.filter(is_active=True):
            get_or_create_balance(username, lt, year)
        return LeaveBalance.objects.filter(
            employee_id=username, year=year
        ).select_related("leave_type")


class LeaveApplicationListCreateView(generics.ListCreateAPIView):
    """List own applications or pending review queue; submit new leave application."""

    def get_serializer_class(self):
        if self.request.method == "POST":
            return LeaveApplicationCreateSerializer
        return LeaveApplicationSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [HasPermission("leave.application.apply")()]
        return [HasPermission("leave.application.view")()]

    def get_queryset(self):
        user_id = _get_principal_username(self.request)
        queue = self.request.query_params.get("queue")
        qs = LeaveApplication.objects.select_related("leave_type").prefetch_related("history")

        if queue == "approvals":
            return qs.filter(
                Q(
                    status__in=[
                        LeaveApplication.STATUS_AWAITING_UNIT_HEAD,
                        LeaveApplication.STATUS_AWAITING_SANCTION,
                        LeaveApplication.STATUS_AWAITING_DIRECTOR,
                        LeaveApplication.STATUS_CANCELLATION_REQUESTED,
                    ]
                )
                | Q(resumption_status=LeaveApplication.RESUMPTION_PENDING)
            )

        if queue == "substitute":
            return qs.filter(
                substitute_id=user_id,
                status=LeaveApplication.STATUS_AWAITING_SUBSTITUTE,
            )

        principal = getattr(self.request, "principal", None)
        can_approve = (
            principal.has_any_permission("leave.application.approve") if principal else False
        )
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)

        if not can_approve:
            qs = qs.filter(Q(applicant_id=user_id) | Q(substitute_id=user_id))

        return qs

    def create(self, request, *args, **kwargs):
        serializer = LeaveApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        applicant_id = _get_principal_username(request)

        try:
            app = submit_leave_application(
                applicant_id=applicant_id,
                leave_type=data["leave_type"],
                start_date=data["start_date"],
                end_date=data["end_date"],
                reason=data["reason"],
                is_half_day=data.get("is_half_day", False),
                half_day_period=data.get("half_day_period", ""),
                substitute_id=data.get("substitute_id", ""),
                station_leave_required=data.get("station_leave_required", False),
                departure_date=data.get("departure_date"),
                arrival_date=data.get("arrival_date"),
                station_address=data.get("station_address", ""),
                emergency_contact=data.get("emergency_contact", ""),
                is_director=_is_director(request),
            )
        except DjangoValidationError as exc:
            msg = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
            raise DRFValidationError(msg) from exc

        return Response(
            LeaveApplicationSerializer(app).data, status=status.HTTP_201_CREATED
        )


class LeaveApplicationDetailView(generics.RetrieveAPIView):
    """Retrieve full leave application details and audit trail."""

    queryset = LeaveApplication.objects.select_related("leave_type").prefetch_related("history")
    serializer_class = LeaveApplicationSerializer
    permission_classes = [HasPermission("leave.application.view")]


class SubstituteResponseView(APIView):
    """Accept or decline responsibility as nominated substitute."""

    permission_classes = [HasPermission("leave.application.view")]
    serializer_class = LeaveSubstituteResponseSerializer

    def post(self, request, pk):
        try:
            app = LeaveApplication.objects.get(pk=pk)
        except LeaveApplication.DoesNotExist:
            return Response({"detail": "Application not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = LeaveSubstituteResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        substitute_id = _get_principal_username(request)

        try:
            updated = respond_to_substitute_request(
                application=app,
                substitute_id=substitute_id,
                action=serializer.validated_data["response"],
                remarks=serializer.validated_data.get("remarks", ""),
                is_director=_is_director(request),
            )
        except DjangoValidationError as exc:
            msg = exc.messages if hasattr(exc, "messages") else str(exc)
            raise DRFValidationError(msg) from exc

        return Response(LeaveApplicationSerializer(updated).data)


class ReplacementSubstituteView(APIView):
    """Nominate replacement substitute after previous decline."""

    permission_classes = [HasPermission("leave.application.apply")]
    serializer_class = LeaveReplacementSubstituteSerializer

    def post(self, request, pk):
        try:
            app = LeaveApplication.objects.get(pk=pk)
        except LeaveApplication.DoesNotExist:
            return Response({"detail": "Application not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = LeaveReplacementSubstituteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        applicant_id = _get_principal_username(request)

        try:
            updated = nominate_replacement_substitute(
                application=app,
                applicant_id=applicant_id,
                new_substitute_id=serializer.validated_data["substitute_id"],
                remarks=serializer.validated_data.get("remarks", ""),
            )
        except DjangoValidationError as exc:
            msg = exc.messages if hasattr(exc, "messages") else str(exc)
            raise DRFValidationError(msg) from exc

        return Response(LeaveApplicationSerializer(updated).data)


class LeaveApplicationReviewView(APIView):
    """Approve, reject, or recommend leave request based on authority level."""

    permission_classes = [HasPermission("leave.application.approve")]
    serializer_class = LeaveReviewActionSerializer

    def post(self, request, pk):
        try:
            app = LeaveApplication.objects.get(pk=pk)
        except LeaveApplication.DoesNotExist:
            return Response({"detail": "Application not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = LeaveReviewActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data["review_action"]
        rec = serializer.validated_data.get("recommendation", "")
        remarks = serializer.validated_data.get("remarks", "")
        reviewer_id = _get_principal_username(request)

        try:
            if app.status == LeaveApplication.STATUS_AWAITING_UNIT_HEAD:
                updated = review_by_unit_head(
                    application=app,
                    unit_head_id=reviewer_id,
                    action=action,
                    recommendation=rec,
                    remarks=remarks,
                )
            elif app.status in (
                LeaveApplication.STATUS_AWAITING_SANCTION,
                LeaveApplication.STATUS_AWAITING_DIRECTOR,
            ):
                updated = review_by_sanctioning_authority(
                    application=app,
                    authority_id=reviewer_id,
                    action=action,
                    remarks=remarks,
                )
            else:
                return Response(
                    {"detail": f"Application in state '{app.status}' cannot be reviewed."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except DjangoValidationError as exc:
            msg = exc.messages if hasattr(exc, "messages") else str(exc)
            raise DRFValidationError(msg) from exc

        return Response(LeaveApplicationSerializer(updated).data)


class LeaveApplicationWithdrawView(APIView):
    """Immediate withdrawal of pending request before approval."""

    permission_classes = [HasPermission("leave.application.apply")]
    serializer_class = LeaveWithdrawSerializer

    def post(self, request, pk):
        try:
            app = LeaveApplication.objects.get(pk=pk)
        except LeaveApplication.DoesNotExist:
            return Response({"detail": "Application not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = LeaveWithdrawSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        applicant_id = _get_principal_username(request)

        try:
            updated = withdraw_leave_application(
                application=app,
                applicant_id=applicant_id,
                remarks=serializer.validated_data.get("remarks", ""),
            )
        except DjangoValidationError as exc:
            msg = exc.messages if hasattr(exc, "messages") else str(exc)
            raise DRFValidationError(msg) from exc

        return Response(LeaveApplicationSerializer(updated).data)


class LeaveApplicationCancelView(APIView):
    """Request pre-start cancellation of approved leave."""

    permission_classes = [HasPermission("leave.application.apply")]
    serializer_class = LeaveCancellationRequestSerializer

    def post(self, request, pk):
        try:
            app = LeaveApplication.objects.get(pk=pk)
        except LeaveApplication.DoesNotExist:
            return Response({"detail": "Application not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = LeaveCancellationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        applicant_id = _get_principal_username(request)

        try:
            updated = request_approved_leave_cancellation(
                application=app,
                applicant_id=applicant_id,
                reason=serializer.validated_data["reason"],
            )
        except DjangoValidationError as exc:
            msg = exc.messages if hasattr(exc, "messages") else str(exc)
            raise DRFValidationError(msg) from exc

        return Response(LeaveApplicationSerializer(updated).data)


class LeaveApplicationCancellationReviewView(APIView):
    """Review requested cancellation of approved leave."""

    permission_classes = [HasPermission("leave.application.approve")]
    serializer_class = LeaveCancellationReviewSerializer

    def post(self, request, pk):
        try:
            app = LeaveApplication.objects.get(pk=pk)
        except LeaveApplication.DoesNotExist:
            return Response({"detail": "Application not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = LeaveCancellationReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reviewer_id = _get_principal_username(request)

        try:
            updated = review_cancellation_request(
                application=app,
                reviewer_id=reviewer_id,
                action=serializer.validated_data["approval_action"],
                remarks=serializer.validated_data.get("remarks", ""),
            )
        except DjangoValidationError as exc:
            msg = exc.messages if hasattr(exc, "messages") else str(exc)
            raise DRFValidationError(msg) from exc

        return Response(LeaveApplicationSerializer(updated).data)


class LeaveApplicationResumptionView(APIView):
    """Submit actual resumption date following return from duty."""

    permission_classes = [HasPermission("leave.application.apply")]
    serializer_class = LeaveResumptionSubmitSerializer

    def post(self, request, pk):
        try:
            app = LeaveApplication.objects.get(pk=pk)
        except LeaveApplication.DoesNotExist:
            return Response({"detail": "Application not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = LeaveResumptionSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        applicant_id = _get_principal_username(request)

        try:
            updated = submit_resumption_of_duty(
                application=app,
                applicant_id=applicant_id,
                resumption_date=serializer.validated_data["resumption_date"],
                remarks=serializer.validated_data.get("remarks", ""),
            )
        except DjangoValidationError as exc:
            msg = exc.messages if hasattr(exc, "messages") else str(exc)
            raise DRFValidationError(msg) from exc

        return Response(LeaveApplicationSerializer(updated).data)


class LeaveApplicationResumptionReviewView(APIView):
    """Review resumption submission and reconcile leave balance."""

    permission_classes = [HasPermission("leave.application.approve")]
    serializer_class = LeaveResumptionReviewSerializer

    def post(self, request, pk):
        try:
            app = LeaveApplication.objects.get(pk=pk)
        except LeaveApplication.DoesNotExist:
            return Response({"detail": "Application not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = LeaveResumptionReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reviewer_id = _get_principal_username(request)

        try:
            updated = review_resumption_submission(
                application=app,
                reviewer_id=reviewer_id,
                action=serializer.validated_data["approval_action"],
                remarks=serializer.validated_data.get("remarks", ""),
            )
        except DjangoValidationError as exc:
            msg = exc.messages if hasattr(exc, "messages") else str(exc)
            raise DRFValidationError(msg) from exc

        return Response(LeaveApplicationSerializer(updated).data)
