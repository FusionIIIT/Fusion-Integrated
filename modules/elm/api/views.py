"""DRF API views for Employee Leave Management (ELM)."""
from datetime import date
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..domain.errors import ElmDomainError
from ..selectors import leaves as selectors
from ..services import leaves as services
from .permissions import (
    RequireElmModule,
    RequireLeaveAdmin,
    RequireLeaveApply,
    RequireLeaveReview,
    RequireLeaveSubstitute,
    RequireLeaveView,
)
from .serializers import (
    ApprovalDecisionSerializer,
    ApprovalStepSerializer,
    ExtensionRequestSerializer,
    HolidayCalendarSerializer,
    LeaveApplicationCreateSerializer,
    LeaveApplicationReadSerializer,
    LeaveBalanceSerializer,
    LeavePolicySerializer,
    OfflineSanctionSerializer,
    ResumptionRequestSerializer,
    SubstituteResponseSerializer,
)


class LeaveBalanceListView(generics.ListAPIView):
    permission_classes = [RequireElmModule, RequireLeaveView]
    serializer_class = LeaveBalanceSerializer

    def get_queryset(self):
        user_id = self.request.principal.erp_user_id
        year = int(self.request.query_params.get("year", date.today().year))
        return selectors.get_user_balances(user_id=user_id, year=year)


class LeavePolicyListView(generics.ListAPIView):
    permission_classes = [RequireElmModule, RequireLeaveView]
    serializer_class = LeavePolicySerializer

    def get_queryset(self):
        return selectors.get_leave_policies()


class HolidayCalendarListView(generics.ListAPIView):
    permission_classes = [RequireElmModule, RequireLeaveView]
    serializer_class = HolidayCalendarSerializer

    def get_queryset(self):
        year = int(self.request.query_params.get("year", date.today().year))
        return selectors.get_holiday_calendar(year=year)


class LeaveApplicationListCreateView(APIView):
    permission_classes = [RequireElmModule, RequireLeaveView]

    def get(self, request):
        user_id = request.principal.erp_user_id
        apps = selectors.get_user_applications(user_id)
        serializer = LeaveApplicationReadSerializer(apps, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = LeaveApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user_id = request.principal.erp_user_id
        user_role = getattr(request.principal, "designation", "staff")

        try:
            app = services.apply_leave(
                user_id=user_id,
                user_role=user_role,
                category=data["category"],
                leave_start=data["leave_start"],
                leave_end=data["leave_end"],
                purpose=data["purpose"],
                is_half_day=data.get("is_half_day", False),
                half_day=data.get("half_day", ""),
                station_leave_required=data.get("station_leave_required", False),
                station_leave_city=data.get("station_leave_city", ""),
                station_leave_purpose=data.get("station_leave_purpose", ""),
                substitute_user_id=data.get("substitute_user_id"),
                unit_head_id=data.get("unit_head_id", 2),
            )
            return Response(LeaveApplicationReadSerializer(app).data, status=status.HTTP_201_CREATED)
        except ElmDomainError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class LeaveApplicationDetailView(APIView):
    permission_classes = [RequireElmModule, RequireLeaveView]

    def get(self, request, pk: int):
        user_id = request.principal.erp_user_id
        app = selectors.get_application_detail(pk, user_id=user_id)
        if not app:
            return Response({"detail": "Application not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(LeaveApplicationReadSerializer(app).data)


class LeaveWithdrawView(APIView):
    permission_classes = [RequireElmModule, RequireLeaveApply]

    def post(self, request, pk: int):
        user_id = request.principal.erp_user_id
        try:
            app = services.withdraw_leave(application_id=pk, user_id=user_id)
            return Response(LeaveApplicationReadSerializer(app).data)
        except ElmDomainError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class LeaveCancelView(APIView):
    permission_classes = [RequireElmModule, RequireLeaveApply]

    def post(self, request, pk: int):
        user_id = request.principal.erp_user_id
        try:
            app = services.request_cancellation(application_id=pk, user_id=user_id)
            return Response(LeaveApplicationReadSerializer(app).data)
        except ElmDomainError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class LeaveExtensionView(APIView):
    permission_classes = [RequireElmModule, RequireLeaveApply]

    def post(self, request, pk: int):
        serializer = ExtensionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = request.principal.erp_user_id

        try:
            app = services.request_extension(
                original_application_id=pk,
                user_id=user_id,
                extended_end_date=serializer.validated_data["extended_end_date"],
                purpose=serializer.validated_data["purpose"],
            )
            return Response(LeaveApplicationReadSerializer(app).data, status=status.HTTP_201_CREATED)
        except ElmDomainError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class LeaveResumptionView(APIView):
    permission_classes = [RequireElmModule, RequireLeaveApply]

    def post(self, request, pk: int):
        serializer = ResumptionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = request.principal.erp_user_id

        try:
            app = services.record_resumption(
                application_id=pk,
                user_id=user_id,
                actual_resumption_date=serializer.validated_data["actual_resumption_date"],
            )
            return Response(LeaveApplicationReadSerializer(app).data)
        except ElmDomainError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PendingApprovalsListView(generics.ListAPIView):
    permission_classes = [RequireElmModule, RequireLeaveReview]
    serializer_class = ApprovalStepSerializer

    def get_queryset(self):
        user_id = self.request.principal.erp_user_id
        return selectors.get_pending_approval_steps(approver_user_id=user_id)


class ApprovalStepActionView(APIView):
    permission_classes = [RequireElmModule, RequireLeaveReview]

    def post(self, request, pk: int):
        serializer = ApprovalDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = request.principal.erp_user_id

        try:
            step = services.process_approval_step(
                step_id=pk,
                decided_by_user_id=user_id,
                decision=serializer.validated_data["decision"],
                comment=serializer.validated_data.get("comment", ""),
            )
            return Response(ApprovalStepSerializer(step).data)
        except ElmDomainError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PendingSubstituteListView(generics.ListAPIView):
    permission_classes = [RequireElmModule, RequireLeaveSubstitute]
    serializer_class = LeaveApplicationReadSerializer

    def get_queryset(self):
        user_id = self.request.principal.erp_user_id
        return selectors.get_pending_substitute_requests(substitute_user_id=user_id)


class SubstituteResponseView(APIView):
    permission_classes = [RequireElmModule, RequireLeaveSubstitute]

    def post(self, request, pk: int):
        serializer = SubstituteResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = request.principal.erp_user_id

        try:
            app = services.respond_to_substitute(
                application_id=pk,
                substitute_user_id=user_id,
                accept=serializer.validated_data["accept"],
            )
            return Response(LeaveApplicationReadSerializer(app).data)
        except ElmDomainError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class OfflineSanctionCreateView(APIView):
    permission_classes = [RequireElmModule, RequireLeaveAdmin]

    def post(self, request):
        serializer = OfflineSanctionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        admin_user_id = request.principal.erp_user_id

        try:
            app = services.record_offline_sanction(
                user_id=data["user_id"],
                category=data["category"],
                leave_start=data["leave_start"],
                leave_end=data["leave_end"],
                reference=data["reference"],
                sanctioned_by_user_id=admin_user_id,
            )
            return Response(LeaveApplicationReadSerializer(app).data, status=status.HTTP_201_CREATED)
        except ElmDomainError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
