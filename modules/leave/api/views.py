"""DRF API views for the Leave module."""

from datetime import date

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.api import serializers as s
from modules.leave.selectors import applications as app_selectors
from modules.leave.selectors import approvals as approval_selectors
from modules.leave.selectors import balances as balance_selectors
from modules.leave.selectors import calendar as calendar_selectors
from modules.leave.selectors import substitutes as substitute_selectors
from modules.leave.services import applications as app_services
from modules.leave.services import approvals as approval_services
from modules.leave.services import balances as balance_services
from modules.leave.services import cancellations as cancellation_services
from modules.leave.services import extensions as extension_services
from modules.leave.services import offline as offline_services
from modules.leave.services import resumptions as resumption_services
from modules.leave.services import sla as sla_services
from modules.leave.services import substitutes as substitute_services
from modules.leave.services import yearend as yearend_services

MODULE = HasModuleGrant("leave")


class LeaveApplicationListCreateView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.view", "leave.request.view_self")]

    @extend_schema(
        operation_id="leave_applications_list",
        summary="List visible leave applications",
        tags=["leave"],
        responses=s.ApplicationListResponseSerializer,
    )
    def get(self, request):
        status_filter = request.query_params.get("status")
        type_filter = request.query_params.get("leave_type")
        qs = app_selectors.visible_applications(
            request.principal, status=status_filter, leave_type=type_filter
        )
        serializer = s.LeaveApplicationReadSerializer(qs[:100], many=True)
        return Response({"results": serializer.data})

    @extend_schema(
        operation_id="leave_applications_create",
        summary="Submit a new leave application",
        tags=["leave"],
        request=s.LeaveApplicationCreateSerializer,
        responses={201: s.LeaveApplicationReadSerializer},
    )
    def post(self, request):
        ser = s.LeaveApplicationCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = app_services.submit_application(request.principal, ser.validated_data)
        return Response(s.LeaveApplicationReadSerializer(app).data, status=status.HTTP_201_CREATED)


class LeaveApplicationDetailView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.view_self")]

    @extend_schema(
        operation_id="leave_applications_detail",
        summary="Get leave application detail and audit logs",
        tags=["leave"],
        responses=s.LeaveApplicationReadSerializer,
    )
    def get(self, request, pk: int):
        app = app_selectors.get_application_or_404(pk, principal=request.principal)
        return Response(s.LeaveApplicationReadSerializer(app).data)


class LeaveApplicationWithdrawView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.delete")]

    @extend_schema(
        summary="Withdraw a pending leave application",
        tags=["leave"],
        request=None,
        responses=s.LeaveApplicationReadSerializer,
    )
    def post(self, request, pk: int):
        app = app_services.withdraw_application(pk, request.principal)
        return Response(s.LeaveApplicationReadSerializer(app).data)


class LeaveApplicationCancelView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.delete")]

    @extend_schema(
        summary="Request cancellation of approved leave before start",
        tags=["leave"],
        request=s.CancellationRequestSerializer,
        responses=s.LeaveApplicationReadSerializer,
    )
    def post(self, request, pk: int):
        ser = s.CancellationRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = cancellation_services.request_cancellation(
            application_id=pk,
            principal=request.principal,
            reason=ser.validated_data["reason"],
        )
        return Response(s.LeaveApplicationReadSerializer(app).data)


class LeaveApplicationCancellationReviewView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.approve")]

    @extend_schema(
        summary="Review cancellation request",
        tags=["leave"],
        request=s.DecisionSerializer,
        responses=s.LeaveApplicationReadSerializer,
    )
    def post(self, request, pk: int):
        ser = s.DecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = cancellation_services.review_cancellation(
            application_id=pk,
            principal=request.principal,
            decision=ser.validated_data["decision"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(s.LeaveApplicationReadSerializer(app).data)


class LeaveApplicationExtendView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.create")]

    @extend_schema(
        summary="Request extension for ongoing EL/COL/VL",
        tags=["leave"],
        request=s.ExtensionRequestSerializer,
        responses={201: s.LeaveApplicationReadSerializer},
    )
    def post(self, request, pk: int):
        ser = s.ExtensionRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = extension_services.request_extension(
            parent_application_id=pk,
            principal=request.principal,
            new_end_date=ser.validated_data["new_end_date"],
            reason=ser.validated_data["reason"],
            substitute_user_id=ser.validated_data.get("substitute_user_id"),
        )
        return Response(s.LeaveApplicationReadSerializer(app).data, status=status.HTTP_201_CREATED)


class LeaveApplicationResumptionView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.create")]

    @extend_schema(
        summary="Submit resumption of duty declaration",
        tags=["leave"],
        request=s.ResumptionSubmitSerializer,
        responses=s.LeaveApplicationReadSerializer,
    )
    def post(self, request, pk: int):
        ser = s.ResumptionSubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = resumption_services.submit_resumption(
            application_id=pk,
            principal=request.principal,
            actual_resumption_date=ser.validated_data["actual_resumption_date"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(s.LeaveApplicationReadSerializer(app).data)


class LeaveApplicationResumptionReviewView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.approve")]

    @extend_schema(
        summary="Review resumption of duty and adjust balance",
        tags=["leave"],
        request=s.RemarksSerializer,
        responses=s.LeaveApplicationReadSerializer,
    )
    def post(self, request, pk: int):
        ser = s.RemarksSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = resumption_services.review_resumption(
            application_id=pk,
            principal=request.principal,
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(s.LeaveApplicationReadSerializer(app).data)


class SubstitutePendingListView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.substitute")]

    @extend_schema(
        summary="List pending substitute tasks for caller",
        tags=["leave"],
        responses=s.ApplicationListResponseSerializer,
    )
    def get(self, request):
        qs = substitute_selectors.pending_substitute_tasks(request.principal.user_id)
        return Response({"results": s.LeaveApplicationReadSerializer(qs, many=True).data})


class SubstituteRespondView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.substitute")]

    @extend_schema(
        summary="Accept or decline substitute responsibility",
        tags=["leave"],
        request=s.SubstituteRespondSerializer,
        responses=s.LeaveApplicationReadSerializer,
    )
    def post(self, request, pk: int):
        ser = s.SubstituteRespondSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = substitute_services.respond_substitute(
            application_id=pk,
            principal=request.principal,
            accept=ser.validated_data["accept"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(s.LeaveApplicationReadSerializer(app).data)


class SubstituteReplaceView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.create")]

    @extend_schema(
        summary="Nominate replacement substitute after decline",
        tags=["leave"],
        request=s.ReplaceSubstituteSerializer,
        responses=s.LeaveApplicationReadSerializer,
    )
    def post(self, request, pk: int):
        ser = s.ReplaceSubstituteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = substitute_services.replace_substitute(
            application_id=pk,
            principal=request.principal,
            new_substitute_id=ser.validated_data["new_substitute_id"],
        )
        return Response(s.LeaveApplicationReadSerializer(app).data)


class ApprovalsPendingListView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.approve")]

    @extend_schema(
        summary="List requests pending caller approval/review",
        tags=["leave"],
        responses=s.ApplicationListResponseSerializer,
    )
    def get(self, request):
        qs = approval_selectors.pending_approvals_for_principal(request.principal)
        return Response({"results": s.LeaveApplicationReadSerializer(qs, many=True).data})


class UnitHeadReviewView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.approve")]

    @extend_schema(
        summary="Unit Head review (Approve/Reject for CL/RH, Recommend for others)",
        tags=["leave"],
        request=s.DecisionSerializer,
        responses=s.LeaveApplicationReadSerializer,
    )
    def post(self, request, pk: int):
        ser = s.DecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = approval_services.review_at_unit_head(
            application_id=pk,
            principal=request.principal,
            decision=ser.validated_data["decision"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(s.LeaveApplicationReadSerializer(app).data)


class EstablishmentRouteView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.approve")]

    @extend_schema(
        summary="Establishment verification and routing step",
        tags=["leave"],
        request=s.RemarksSerializer,
        responses=s.LeaveApplicationReadSerializer,
    )
    def post(self, request, pk: int):
        ser = s.RemarksSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = approval_services.route_at_establishment(
            application_id=pk,
            principal=request.principal,
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(s.LeaveApplicationReadSerializer(app).data)


class SanctionDecisionView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.approve")]

    @extend_schema(
        summary="Final sanctioning decision (Dean/Registrar/Director)",
        tags=["leave"],
        request=s.DecisionSerializer,
        responses=s.LeaveApplicationReadSerializer,
    )
    def post(self, request, pk: int):
        ser = s.DecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = approval_services.final_sanction(
            application_id=pk,
            principal=request.principal,
            decision=ser.validated_data["decision"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(s.LeaveApplicationReadSerializer(app).data)


class LeaveBalanceListView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.view_self")]

    @extend_schema(
        summary="List leave balances for caller or specified user",
        tags=["leave"],
        responses=s.BalanceListResponseSerializer,
    )
    def get(self, request):
        target_uid = request.principal.user_id
        if request.query_params.get("user_id") and request.principal.has_permission(
            "leave.type.manage"
        ):
            target_uid = int(request.query_params["user_id"])

        year = int(request.query_params.get("year", date.today().year))
        balance_services.ensure_user_balances_initialized(target_uid, year, request.principal.kind)
        balances = balance_selectors.list_user_balances(target_uid, year)
        return Response({"results": s.LeaveBalanceSerializer(balances, many=True).data})


class LeaveBalanceAdjustView(APIView):
    permission_classes = [MODULE, HasPermission("leave.balance.update")]

    @extend_schema(
        summary="Adjust a user leave balance (Admin/Establishment)",
        tags=["leave"],
        request=s.BalanceAdjustSerializer,
        responses=s.LeaveBalanceSerializer,
    )
    def post(self, request):
        ser = s.BalanceAdjustSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        bal = balance_services.adjust_balance(
            user_id=data["user_id"],
            year=data["year"],
            leave_type=data["leave_type"],
            delta=data["delta"],
            is_credit=data["is_credit"],
        )
        return Response(s.LeaveBalanceSerializer(bal).data)


class HolidayCalendarListView(APIView):
    permission_classes = [MODULE, HasPermission("leave.calendar.view")]

    @extend_schema(
        summary="List holiday calendar entries",
        tags=["leave"],
        responses=s.HolidayListResponseSerializer,
    )
    def get(self, request):
        year = int(request.query_params.get("year", date.today().year))
        qs = calendar_selectors.list_holidays(year, published_only=False)
        return Response({"results": s.HolidayCalendarSerializer(qs, many=True).data})

    @extend_schema(
        summary="Add holiday calendar entry (Admin)",
        tags=["leave"],
        request=s.HolidayCalendarSerializer,
        responses={201: s.HolidayCalendarSerializer},
    )
    def post(self, request):
        if not request.principal.has_permission("leave.type.manage"):
            raise BadRequestError("Permission denied.")
        ser = s.HolidayCalendarSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        h = ser.save()
        return Response(s.HolidayCalendarSerializer(h).data, status=status.HTTP_201_CREATED)


class VacationPeriodListView(APIView):
    permission_classes = [MODULE, HasPermission("leave.calendar.view")]

    @extend_schema(
        summary="List academic vacation periods",
        tags=["leave"],
        responses=s.VacationListResponseSerializer,
    )
    def get(self, request):
        year = int(request.query_params.get("year", date.today().year))
        qs = calendar_selectors.list_vacations(year, published_only=False)
        return Response({"results": s.VacationPeriodSerializer(qs, many=True).data})

    @extend_schema(
        summary="Add vacation period (Admin)",
        tags=["leave"],
        request=s.VacationPeriodSerializer,
        responses={201: s.VacationPeriodSerializer},
    )
    def post(self, request):
        if not request.principal.has_permission("leave.type.manage"):
            raise BadRequestError("Permission denied.")
        ser = s.VacationPeriodSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.save()
        return Response(s.VacationPeriodSerializer(v).data, status=status.HTTP_201_CREATED)


class OfflineLeaveCreateView(APIView):
    permission_classes = [MODULE, HasPermission("leave.offline.record")]

    @extend_schema(
        summary="Record already-sanctioned offline leave",
        tags=["leave"],
        request=s.OfflineLeaveCreateSerializer,
        responses={201: s.LeaveApplicationReadSerializer},
    )
    def post(self, request):
        ser = s.OfflineLeaveCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        app = offline_services.record_offline_leave(
            admin_principal=request.principal,
            applicant_user_id=d["applicant_user_id"],
            applicant_kind=d.get("applicant_kind", "staff"),
            leave_type=d["leave_type"],
            start_date=d["start_date"],
            end_date=d["end_date"],
            reason=d["reason"],
            sanction_ref=d["sanction_ref"],
            sanction_date=d["sanction_date"],
            sanctioned_by=d["sanctioned_by"],
            half_day_type=d.get("half_day_type", "FULL"),
        )
        return Response(s.LeaveApplicationReadSerializer(app).data, status=status.HTTP_201_CREATED)


class YearEndProcessingView(APIView):
    permission_classes = [MODULE, HasPermission("leave.type.manage")]

    @extend_schema(
        summary="Trigger Year-End processing (EL-UC-020)",
        tags=["leave"],
        request=s.YearEndRequestSerializer,
        responses=s.YearEndResponseSerializer,
    )
    def post(self, request):
        ser = s.YearEndRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        year = ser.validated_data.get("year", date.today().year)
        res = yearend_services.execute_year_end_processing(year)
        return Response(res)


class SLAProcessingView(APIView):
    permission_classes = [MODULE, HasPermission("leave.type.manage")]

    @extend_schema(
        summary="Trigger SLA threshold checking (EL-UC-021)",
        tags=["leave"],
        request=None,
        responses=s.SLAResponseSerializer,
    )
    def post(self, request):
        res = sla_services.process_sla_thresholds()
        return Response(res)
