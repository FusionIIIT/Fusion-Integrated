"""API views for ELM."""
from __future__ import annotations

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.directory import contracts as directory
from modules.elm.api import serializers as s
from modules.elm.models import (
    ApprovalHierarchy,
    HolidayCalendar,
    LeaveApplication,
    LeaveAuditLog,
    SlaThresholdConfig,
    VacationPeriod,
)
from modules.elm.selectors.balances import (
    get_balance_history,
    get_balances_for_user,
)
from modules.elm.selectors.config import get_active_policy_config
from modules.elm.selectors.leaves import (
    get_application_for_user,
    get_user_applications,
)
from modules.elm.selectors.tasks import get_pending_tasks_for_user
from modules.elm.services import (
    admin as admin_service,
)
from modules.elm.services import (
    cancellation as cancellation_service,
)
from modules.elm.services import (
    extension as extension_service,
)
from modules.elm.services import (
    leaves as leave_service,
)
from modules.elm.services import (
    resumption as resumption_service,
)
from modules.elm.services import (
    sla as sla_service,
)
from modules.elm.services import (
    substitute as substitute_service,
)
from modules.elm.services import (
    workflow as workflow_service,
)
from modules.elm.services import (
    year_end as year_end_service,
)


class LeaveBalanceListView(APIView):
    """View current leave balances and transaction history (EL-UC-012, CFR-EL-022)."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.view_self")]

    @extend_schema(
        operation_id="elm_leave_balance_list",
        responses=s.LeaveBalanceResponseSerializer,
    )
    def get(self, request):
        p = request.principal
        year_param = request.query_params.get("year")
        year = int(year_param) if year_param else timezone.now().year

        balances = get_balances_for_user(p.user_id, year)
        history = get_balance_history(p.user_id, year)

        return Response({
            "user_id": p.user_id,
            "year": year,
            "balances": {k: str(v) for k, v in balances.items()},
            "transactions": s.LeaveBalanceTransactionSerializer(history, many=True).data,
        })


class LeaveApplicationListCreateView(APIView):
    """List or submit leave applications (EL-UC-001, EL-UC-012)."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.view_self")]

    @extend_schema(
        operation_id="elm_application_list",
        responses=s.LeaveApplicationDetailSerializer(many=True),
    )
    def get(self, request):
        p = request.principal
        can_view_all = p.has_permission("elm.leave.view_all")
        year = request.query_params.get("year")
        year_val = int(year) if year else None

        if can_view_all and request.query_params.get("all") == "true":
            qs = LeaveApplication.objects.all().order_by("-created_at")
            if year_val:
                qs = qs.filter(start_date__year=year_val)
        else:
            qs = get_user_applications(p.user_id, year=year_val)

        return Response(s.LeaveApplicationDetailSerializer(qs, many=True).data)

    @extend_schema(
        operation_id="elm_application_create",
        request=s.LeaveApplicationCreateSerializer,
        responses={201: s.LeaveApplicationDetailSerializer},
    )
    def post(self, request):
        p = request.principal
        if not p.has_permission("elm.leave.apply"):
            return Response(
                {"error": "Missing elm.leave.apply permission"},
                status=status.HTTP_403_FORBIDDEN,
            )

        ser = s.LeaveApplicationCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        user_info = directory.get_users([p.user_id]).get(p.user_id)
        department = user_info.department if user_info else ""
        designation = p.active_role or (p.roles[0] if p.roles else "")

        app = leave_service.apply_leave(
            user_id=p.user_id,
            user_kind=p.kind,
            user_roles=p.roles,
            category=data["category"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            purpose=data["purpose"],
            is_half_day=data.get("is_half_day", False),
            half_day_session=data.get("half_day_session", ""),
            medical_certificate=data.get("medical_certificate", ""),
            is_station_leave=data.get("is_station_leave", False),
            station_leave_departure=data.get("station_leave_departure"),
            station_leave_return=data.get("station_leave_return"),
            station_destination=data.get("station_destination", ""),
            station_address=data.get("station_address", ""),
            station_emergency_contact=data.get("station_emergency_contact", ""),
            requires_substitute=data.get("requires_substitute", False),
            substitute_user_id=data.get("substitute_user_id"),
            user_department=department,
            user_designation=designation,
        )

        return Response(
            s.LeaveApplicationDetailSerializer(app).data,
            status=status.HTTP_201_CREATED,
        )


class LeaveApplicationDetailView(APIView):
    """Retrieve details of a specific leave application (EL-UC-012)."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.view_self")]

    @extend_schema(
        operation_id="elm_application_detail",
        responses=s.LeaveApplicationDetailSerializer,
    )
    def get(self, request, pk: int):
        p = request.principal
        can_view_all = p.has_permission("elm.leave.view_all")
        app = get_application_for_user(pk, p.user_id, is_admin=can_view_all, is_reviewer=True)
        if not app:
            raise NotFoundError(f"Leave application #{pk} not found.")

        audit_logs = LeaveAuditLog.objects.filter(leave_application=app).order_by("created_at")

        res_data = None
        if hasattr(app, "resumption"):
            res_data = s.LeaveResumptionSerializer(app.resumption).data

        return Response({
            "application": s.LeaveApplicationDetailSerializer(app).data,
            "audit_trail": s.LeaveAuditLogSerializer(audit_logs, many=True).data,
            "extensions": s.LeaveExtensionSerializer(app.extensions.all(), many=True).data,
            "resumption": res_data,
        })


class LeaveApplicationExportView(APIView):
    """Obtain printable/exportable representation of a leave application (EL-UC-013, CFR-EL-023)."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.view_self")]

    @extend_schema(
        operation_id="elm_application_export",
        responses=s.LeaveApplicationExportSerializer,
    )
    def get(self, request, pk: int):
        p = request.principal
        can_view_all = p.has_permission("elm.leave.view_all")
        app = get_application_for_user(pk, p.user_id, is_admin=can_view_all, is_reviewer=True)
        if not app:
            raise NotFoundError(f"Leave application #{pk} not found.")

        user_info = directory.get_users([app.user_id]).get(app.user_id)
        applicant_name = user_info.display_name if user_info else f"User {app.user_id}"

        sub_resp_at = (
            str(app.substitute_responded_at) if app.substitute_responded_at else None
        )
        fin_dec_at = str(app.final_decision_at) if app.final_decision_at else None
        dep_at = str(app.station_leave_departure) if app.station_leave_departure else None
        ret_at = str(app.station_leave_return) if app.station_leave_return else None

        export_data = {
            "document_type": "ELM_LEAVE_APPLICATION_RECORD",
            "application_id": app.id,
            "generated_at": timezone.now().isoformat(),
            "applicant": {
                "user_id": app.user_id,
                "name": applicant_name,
                "department": user_info.department if user_info else "",
            },
            "leave_details": {
                "category": app.category,
                "start_date": str(app.start_date),
                "end_date": str(app.end_date),
                "is_half_day": app.is_half_day,
                "half_day_session": app.half_day_session,
                "chargeable_days": str(app.chargeable_days),
                "purpose": app.purpose,
                "status": app.status,
                "final_decision": app.final_decision,
                "final_decision_at": fin_dec_at,
            },
            "station_leave": {
                "is_station_leave": app.is_station_leave,
                "destination": app.station_destination,
                "address": app.station_address,
                "emergency_contact": app.station_emergency_contact,
                "departure": dep_at,
                "return": ret_at,
            },
            "substitute": {
                "requires_substitute": app.requires_substitute,
                "substitute_user_id": app.substitute_user_id,
                "status": app.substitute_status,
                "responded_at": sub_resp_at,
            },
            "review_trail": {
                "unit_head_recommendation": app.unit_head_recommendation,
                "unit_head_remarks": app.unit_head_remarks,
                "establishment_remarks": app.establishment_remarks,
                "final_decision_remarks": app.final_decision_remarks,
            },
        }
        return Response(export_data)


class LeaveApplicationWithdrawView(APIView):
    """Immediately withdraw pending leave application before final approval (EL-UC-007)."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.withdraw")]

    @extend_schema(
        operation_id="elm_application_withdraw",
        request=s.LeaveWithdrawSerializer,
        responses=s.LeaveApplicationDetailSerializer,
    )
    def post(self, request, pk: int):
        p = request.principal
        ser = s.LeaveWithdrawSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        reason = ser.validated_data.get("reason", "")
        app = leave_service.withdraw_leave(pk, p.user_id, reason=reason)
        return Response(s.LeaveApplicationDetailSerializer(app).data)


class SubstituteResponseView(APIView):
    """Substitute accepts or declines responsibility assignment (EL-UC-002, BR-EL-015)."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.substitute.respond")]

    @extend_schema(
        operation_id="elm_substitute_respond",
        request=s.SubstituteResponseSerializer,
        responses=s.LeaveApplicationDetailSerializer,
    )
    def post(self, request, pk: int):
        p = request.principal
        ser = s.SubstituteResponseSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = substitute_service.respond_substitute(
            application_id=pk,
            substitute_user_id=p.user_id,
            accepted=ser.validated_data["accepted"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(s.LeaveApplicationDetailSerializer(app).data)


class SubstituteReplaceView(APIView):
    """Nominate replacement substitute after decline (EL-UC-019, BR-EL-014)."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.apply")]

    @extend_schema(
        operation_id="elm_substitute_replace",
        request=s.SubstituteReplaceSerializer,
        responses=s.LeaveApplicationDetailSerializer,
    )
    def post(self, request, pk: int):
        p = request.principal
        ser = s.SubstituteReplaceSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = substitute_service.replace_substitute(
            application_id=pk,
            applicant_user_id=p.user_id,
            new_substitute_user_id=ser.validated_data["new_substitute_user_id"],
        )
        return Response(s.LeaveApplicationDetailSerializer(app).data)


class UnitHeadReviewView(APIView):
    """Record Unit Head review outcome (EL-UC-003, BR-EL-016, BR-EL-017)."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.review.unit_head")]

    @extend_schema(
        operation_id="elm_unit_head_review",
        request=s.UnitHeadReviewSerializer,
        responses=s.LeaveApplicationDetailSerializer,
    )
    def post(self, request, pk: int):
        p = request.principal
        ser = s.UnitHeadReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = workflow_service.review_unit_head(
            application_id=pk,
            reviewer_user_id=p.user_id,
            outcome=ser.validated_data["outcome"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(s.LeaveApplicationDetailSerializer(app).data)


class EstablishmentRouteView(APIView):
    """Establishment verifies and forwards higher-sanction request (EL-UC-004, CFR-EL-014)."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.review.establishment")]

    @extend_schema(
        operation_id="elm_establishment_route",
        request=s.EstablishmentRouteSerializer,
        responses=s.LeaveApplicationDetailSerializer,
    )
    def post(self, request, pk: int):
        p = request.principal
        ser = s.EstablishmentRouteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = workflow_service.route_establishment(
            application_id=pk,
            establishment_user_id=p.user_id,
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(s.LeaveApplicationDetailSerializer(app).data)


class SanctionDecisionView(APIView):
    """Final sanction decision by competent authority or Director self-sanction (EL-UC-005)."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.sanction.decide")]

    @extend_schema(
        operation_id="elm_sanction_decision",
        request=s.SanctionDecisionSerializer,
        responses=s.LeaveApplicationDetailSerializer,
    )
    def post(self, request, pk: int):
        p = request.principal
        ser = s.SanctionDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = workflow_service.sanction_decision(
            application_id=pk,
            sanctioner_user_id=p.user_id,
            decision=ser.validated_data["decision"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(s.LeaveApplicationDetailSerializer(app).data)


class CancellationRequestView(APIView):
    """Request pre-start cancellation of approved leave (EL-UC-008, BR-EL-023)."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.cancel")]

    @extend_schema(
        operation_id="elm_cancellation_request",
        request=s.CancellationRequestSerializer,
        responses=s.LeaveApplicationDetailSerializer,
    )
    def post(self, request, pk: int):
        p = request.principal
        ser = s.CancellationRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = cancellation_service.request_cancellation(
            application_id=pk,
            user_id=p.user_id,
            reason=ser.validated_data["reason"],
        )
        return Response(s.LeaveApplicationDetailSerializer(app).data)


class CancellationUnitHeadReviewView(APIView):
    """Review cancellation request at Unit Head level."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.review.unit_head")]

    @extend_schema(
        operation_id="elm_cancellation_unit_head_review",
        request=s.CancellationReviewSerializer,
        responses=s.LeaveApplicationDetailSerializer,
    )
    def post(self, request, pk: int):
        p = request.principal
        ser = s.CancellationReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = cancellation_service.review_cancellation_unit_head(
            application_id=pk,
            reviewer_user_id=p.user_id,
            outcome=ser.validated_data["outcome"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(s.LeaveApplicationDetailSerializer(app).data)


class CancellationEstablishmentRouteView(APIView):
    """Forward cancellation request at Establishment level."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.review.establishment")]

    @extend_schema(
        operation_id="elm_cancellation_establishment_route",
        request=s.EstablishmentRouteSerializer,
        responses=s.LeaveApplicationDetailSerializer,
    )
    def post(self, request, pk: int):
        p = request.principal
        ser = s.EstablishmentRouteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = cancellation_service.review_cancellation_establishment(
            application_id=pk,
            establishment_user_id=p.user_id,
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(s.LeaveApplicationDetailSerializer(app).data)


class CancellationFinalDecisionView(APIView):
    """Final decision on cancellation request."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.sanction.decide")]

    @extend_schema(
        operation_id="elm_cancellation_final_decision",
        request=s.SanctionDecisionSerializer,
        responses=s.LeaveApplicationDetailSerializer,
    )
    def post(self, request, pk: int):
        p = request.principal
        ser = s.SanctionDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = cancellation_service.review_cancellation_final(
            application_id=pk,
            sanctioner_user_id=p.user_id,
            decision=ser.validated_data["decision"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(s.LeaveApplicationDetailSerializer(app).data)


class ExtensionRequestView(APIView):
    """Request extension of ongoing EL/COL/VL (EL-UC-009, BR-EL-025)."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.extend")]

    @extend_schema(
        operation_id="elm_extension_request",
        request=s.ExtensionRequestSerializer,
        responses={201: s.LeaveExtensionSerializer},
    )
    def post(self, request, pk: int):
        p = request.principal
        ser = s.ExtensionRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ext = extension_service.request_extension(
            application_id=pk,
            applicant_user_id=p.user_id,
            extended_end_date=ser.validated_data["extended_end_date"],
            reason=ser.validated_data["reason"],
            requires_substitute=ser.validated_data.get("requires_substitute", False),
            substitute_user_id=ser.validated_data.get("substitute_user_id"),
        )
        return Response(s.LeaveExtensionSerializer(ext).data, status=status.HTTP_201_CREATED)


class ExtensionUnitHeadReviewView(APIView):
    """Review extension at Unit Head."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.review.unit_head")]

    @extend_schema(
        operation_id="elm_extension_unit_head_review",
        request=s.ExtensionReviewSerializer,
        responses=s.LeaveExtensionSerializer,
    )
    def post(self, request, pk: int):
        p = request.principal
        ser = s.ExtensionReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ext = extension_service.review_extension_unit_head(
            extension_id=pk,
            reviewer_user_id=p.user_id,
            outcome=ser.validated_data["outcome"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(s.LeaveExtensionSerializer(ext).data)


class ExtensionFinalDecisionView(APIView):
    """Final decision on extension."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.sanction.decide")]

    @extend_schema(
        operation_id="elm_extension_final_decision",
        request=s.SanctionDecisionSerializer,
        responses=s.LeaveExtensionSerializer,
    )
    def post(self, request, pk: int):
        p = request.principal
        ser = s.SanctionDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ext = extension_service.review_extension_final(
            extension_id=pk,
            sanctioner_user_id=p.user_id,
            decision=ser.validated_data["decision"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(s.LeaveExtensionSerializer(ext).data)


class ResumptionSubmitView(APIView):
    """Submit resumption of duty after EL/COL/VL (EL-UC-010, BR-EL-027)."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.resume")]

    @extend_schema(
        operation_id="elm_resumption_submit",
        request=s.ResumptionSubmitSerializer,
        responses={201: s.LeaveResumptionSerializer},
    )
    def post(self, request, pk: int):
        p = request.principal
        ser = s.ResumptionSubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        resumption = resumption_service.submit_resumption(
            application_id=pk,
            applicant_user_id=p.user_id,
            actual_resumption_date=ser.validated_data["actual_resumption_date"],
            resumption_details=ser.validated_data["resumption_details"],
        )
        return Response(
            s.LeaveResumptionSerializer(resumption).data,
            status=status.HTTP_201_CREATED,
        )


class ResumptionReviewView(APIView):
    """Review resumption by Sanctioning Authority (EL-UC-011, BR-EL-028)."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.sanction.decide")]

    @extend_schema(
        operation_id="elm_resumption_review",
        request=s.ResumptionReviewSerializer,
        responses=s.LeaveResumptionSerializer,
    )
    def post(self, request, pk: int):
        p = request.principal
        ser = s.ResumptionReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        resumption = resumption_service.review_resumption(
            resumption_id=pk,
            reviewer_user_id=p.user_id,
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(s.LeaveResumptionSerializer(resumption).data)


class WorkflowTaskListView(APIView):
    """List pending actionable tasks assigned to caller (CFR-EL-030)."""

    permission_classes = [HasModuleGrant("elm")]

    @extend_schema(
        operation_id="elm_workflow_task_list",
        responses=s.WorkflowTaskSerializer(many=True),
    )
    def get(self, request):
        p = request.principal
        tasks = get_pending_tasks_for_user(p.user_id)
        return Response(s.WorkflowTaskSerializer(tasks, many=True).data)


# --- Admin Endpoints ---


class AdminPolicyConfigView(APIView):
    """Maintain policy parameters (EL-UC-014, BR-EL-030)."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.admin.manage")]

    @extend_schema(
        operation_id="elm_admin_policy_get",
        responses=s.LeavePolicyConfigSerializer,
    )
    def get(self, request):
        cfg = get_active_policy_config()
        return Response(s.LeavePolicyConfigSerializer(cfg).data)

    @extend_schema(
        operation_id="elm_admin_policy_update",
        request=s.LeavePolicyConfigSerializer,
        responses=s.LeavePolicyConfigSerializer,
    )
    def put(self, request):
        p = request.principal
        serializer = s.LeavePolicyConfigSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        cfg = admin_service.update_policy_config(p.user_id, **serializer.validated_data)
        return Response(s.LeavePolicyConfigSerializer(cfg).data)


class AdminHolidayCalendarView(APIView):
    """Maintain holiday calendars (EL-UC-015, BR-EL-031)."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.admin.manage")]

    @extend_schema(
        operation_id="elm_admin_calendars_list",
        responses=s.HolidayCalendarSerializer(many=True),
    )
    def get(self, request):
        cals = HolidayCalendar.objects.all().prefetch_related("holidays")
        return Response(s.HolidayCalendarSerializer(cals, many=True).data)

    @extend_schema(
        operation_id="elm_admin_calendars_create",
        request=s.HolidayCalendarSerializer,
        responses={201: s.HolidayCalendarSerializer},
    )
    def post(self, request):
        year = request.data.get("year")
        label = request.data.get("label", "")
        if not year:
            raise BadRequestError("Year is required.")
        cal = admin_service.create_or_update_holiday_calendar(int(year), label=label)
        return Response(s.HolidayCalendarSerializer(cal).data, status=status.HTTP_201_CREATED)


class AdminHolidayCalendarPublishView(APIView):
    """Publish replacement holiday calendar (EL-UC-015, BR-EL-031)."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.admin.manage")]

    @extend_schema(
        operation_id="elm_admin_calendar_publish",
        request=None,
        responses=s.HolidayCalendarSerializer,
    )
    def post(self, request, pk: int):
        p = request.principal
        cal = admin_service.publish_holiday_calendar(pk, p.user_id)
        return Response(s.HolidayCalendarSerializer(cal).data)


class AdminHolidayCreateView(APIView):
    """Add a holiday to a calendar."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.admin.manage")]

    @extend_schema(
        operation_id="elm_admin_holiday_create",
        request=s.HolidaySerializer,
        responses={201: s.HolidaySerializer},
    )
    def post(self, request, pk: int):
        h = admin_service.add_holiday(
            calendar_id=pk,
            holiday_date=request.data["date"],
            name=request.data["name"],
            holiday_type=request.data["holiday_type"],
            description=request.data.get("description", ""),
        )
        return Response(s.HolidaySerializer(h).data, status=status.HTTP_201_CREATED)


class AdminVacationPeriodView(APIView):
    """Manage vacation periods from Academic Calendar (BR-EL-006, EXT-01)."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.admin.manage")]

    @extend_schema(
        operation_id="elm_admin_vacation_periods_list",
        responses=s.VacationPeriodSerializer(many=True),
    )
    def get(self, request):
        vps = VacationPeriod.objects.filter(is_active=True).order_by("start_date")
        return Response(s.VacationPeriodSerializer(vps, many=True).data)

    @extend_schema(
        operation_id="elm_admin_vacation_periods_create",
        request=s.VacationPeriodSerializer,
        responses={201: s.VacationPeriodSerializer},
    )
    def post(self, request):
        vp = admin_service.create_vacation_period(
            academic_year=request.data["academic_year"],
            name=request.data["name"],
            start_date=request.data["start_date"],
            end_date=request.data["end_date"],
        )
        return Response(s.VacationPeriodSerializer(vp).data, status=status.HTTP_201_CREATED)


class AdminApprovalHierarchyView(APIView):
    """Manage approval hierarchies (EL-UC-014, BR-EL-019)."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.admin.manage")]

    @extend_schema(
        operation_id="elm_admin_hierarchies_list",
        responses=s.ApprovalHierarchySerializer(many=True),
    )
    def get(self, request):
        hierarchies = ApprovalHierarchy.objects.filter(is_active=True)
        return Response(s.ApprovalHierarchySerializer(hierarchies, many=True).data)

    @extend_schema(
        operation_id="elm_admin_hierarchies_create",
        request=s.ApprovalHierarchySerializer,
        responses={201: s.ApprovalHierarchySerializer},
    )
    def post(self, request):
        h = admin_service.configure_approval_hierarchy(**request.data)
        return Response(s.ApprovalHierarchySerializer(h).data, status=status.HTTP_201_CREATED)


class AdminSlaThresholdView(APIView):
    """Configure SLA thresholds (EL-UC-018, BR-EL-038)."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.admin.manage")]

    @extend_schema(
        operation_id="elm_admin_sla_thresholds_list",
        responses=s.SlaThresholdConfigSerializer(many=True),
    )
    def get(self, request):
        configs = SlaThresholdConfig.objects.filter(is_active=True)
        return Response(s.SlaThresholdConfigSerializer(configs, many=True).data)

    @extend_schema(
        operation_id="elm_admin_sla_thresholds_update",
        request=s.SlaThresholdConfigSerializer,
        responses=s.SlaThresholdConfigSerializer,
    )
    def put(self, request):
        cfg = admin_service.configure_sla_threshold(
            task_type=request.data["task_type"],
            reminder_hours=int(request.data["reminder_threshold_hours"]),
            escalation_hours=int(request.data["escalation_threshold_hours"]),
            escalation_action=request.data.get("escalation_action", "notify_only"),
            escalation_target_role=request.data.get("escalation_target_role", ""),
        )
        return Response(s.SlaThresholdConfigSerializer(cfg).data)


class AdminOfflineLeaveView(APIView):
    """Record already-sanctioned offline leave (EL-UC-016, CFR-EL-027, BR-EL-029)."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.admin.manage")]

    @extend_schema(
        operation_id="elm_admin_offline_leave_create",
        request=s.OfflineLeaveCreateSerializer,
        responses={201: s.LeaveApplicationDetailSerializer},
    )
    def post(self, request):
        p = request.principal
        ser = s.OfflineLeaveCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        user_info = directory.get_users([data["employee_user_id"]]).get(data["employee_user_id"])
        user_kind = user_info.kind if user_info else "staff"

        app = admin_service.record_offline_leave(
            employee_user_id=data["employee_user_id"],
            user_kind=user_kind,
            category=data["category"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            purpose=data["purpose"],
            offline_reference_no=data["offline_reference_no"],
            offline_sanction_date=data["offline_sanction_date"],
            offline_sanctioning_authority=data["offline_sanctioning_authority"],
            recorded_by_user_id=p.user_id,
            is_half_day=data.get("is_half_day", False),
            half_day_session=data.get("half_day_session", ""),
        )
        return Response(
            s.LeaveApplicationDetailSerializer(app).data,
            status=status.HTTP_201_CREATED,
        )


class AdminRecordMaintenanceView(APIView):
    """Maintain or correct leave record without creating new sanction (EL-UC-017, BR-EL-037)."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.admin.manage")]

    @extend_schema(
        operation_id="elm_admin_record_maintenance",
        request=s.AdminMaintenanceSerializer,
        responses=s.LeaveApplicationDetailSerializer,
    )
    def patch(self, request, pk: int):
        p = request.principal
        ser = s.AdminMaintenanceSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        app = admin_service.maintain_leave_record(
            application_id=pk,
            admin_user_id=p.user_id,
            reason_note=data["reason_note"],
            new_purpose=data.get("new_purpose"),
            new_medical_certificate=data.get("new_medical_certificate"),
        )
        return Response(s.LeaveApplicationDetailSerializer(app).data)


class AdminYearEndProcessView(APIView):
    """Execute year-end leave balance processing (EL-UC-020, CFR-EL-028)."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.admin.manage")]

    @extend_schema(
        operation_id="elm_admin_year_end_process",
        request=s.AdminYearEndProcessRequestSerializer,
        responses={201: s.YearEndRunSerializer},
    )
    def post(self, request):
        p = request.principal
        year = request.data.get("year", timezone.now().year)
        run = year_end_service.execute_year_end_processing(
            int(year), executed_by_user_id=p.user_id
        )
        return Response(s.YearEndRunSerializer(run).data, status=status.HTTP_201_CREATED)


class AdminProcessSlaView(APIView):
    """Process SLA reminders and escalations (EL-UC-021, CFR-EL-031, CFR-EL-032)."""

    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.admin.manage")]

    @extend_schema(
        operation_id="elm_admin_process_sla",
        request=None,
        responses=s.AdminProcessSlaResponseSerializer,
    )
    def post(self, request):
        counts = sla_service.process_sla_events()
        return Response(counts)
