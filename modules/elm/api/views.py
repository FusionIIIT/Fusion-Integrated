from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api import csv as csv_api
from core.api.exceptions import ConflictError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api import serializers as s
from modules.elm.models import (
    ApprovalRoute,
    EmployeeProfile,
    Holiday,
    HolidayCalendar,
    LeavePolicy,
    LeaveRequest,
    OrgUnit,
    VacationPeriod,
    WorkflowTask,
)
from modules.elm.selectors import requests as selectors
from modules.elm.services import leave as service
from modules.elm.services.records import maintain_leave_record
from modules.elm.services.year_end import process_year_end

MODULE = HasModuleGrant("employee_leave")
P_BALANCE_SELF = "employee_leave.balance.view_self"
P_CREATE = "employee_leave.request.create"
P_VIEW_SELF = "employee_leave.request.view_self"
P_VIEW_QUEUE = "employee_leave.request.view"
P_DECIDE = "employee_leave.task.decide"
P_SUBSTITUTE = "employee_leave.substitute.respond"
P_PROCESS = "employee_leave.request.process"
P_YEAR_END = "employee_leave.year_end.process"
P_CALENDAR = "employee_leave.calendar.manage"
P_POLICY = "employee_leave.policy.manage"
P_EMPLOYEE = "employee_leave.employee.manage"
P_REPORT = "employee_leave.report.view"


def _actor_id(request):
    return request.principal.user_id


class MyBalanceView(APIView):
    permission_classes = [MODULE, HasPermission(P_BALANCE_SELF)]

    @extend_schema(responses=s.LeaveBalanceSerializer(many=True))
    def get(self, request):
        accounts = service.balances_for(_actor_id(request))
        return Response([
            {
                "category": account.category,
                "year": account.year,
                "entitlement": account.entitlement,
                "carry_forward": account.carry_forward,
                "used": account.used,
                "balance": account.balance,
            }
            for account in accounts
        ])


class MyLeaveRequestListView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]
    serializer_class = s.LeaveRequestSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveRequest.objects.none()
        return selectors.for_applicant(_actor_id(self.request))


class LeaveRequestCreateView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]

    @extend_schema(
        request=s.LeaveRequestCreateSerializer,
        responses={status.HTTP_201_CREATED: s.LeaveRequestSerializer},
    )
    def post(self, request):
        payload = s.LeaveRequestCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave_request = service.submit_leave(
            applicant_user_id=_actor_id(request),
            **payload.validated_data,
        )
        return Response(
            s.LeaveRequestSerializer(leave_request).data,
            status=status.HTTP_201_CREATED,
        )


class RecordOfflineLeaveView(APIView):
    permission_classes = [MODULE, HasPermission(P_PROCESS)]

    @extend_schema(
        request=s.OfflineLeaveSerializer,
        responses={status.HTTP_201_CREATED: s.LeaveRequestSerializer},
    )
    def post(self, request):
        payload = s.OfflineLeaveSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave_request = service.record_offline_leave(
            actor_id=_actor_id(request), **payload.validated_data)
        return Response(
            s.LeaveRequestSerializer(leave_request).data,
            status=status.HTTP_201_CREATED,
        )


class MyLeaveRequestDetailView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    @extend_schema(responses=s.LeaveRequestSerializer)
    def get(self, request, pk):
        leave_request = get_object_or_404(
            selectors.applicant_request(pk, _actor_id(request)),
        )
        return Response(s.LeaveRequestSerializer(leave_request).data)


class ExportMyLeaveRequestView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    @extend_schema(
        responses={200: OpenApiResponse(
            response=OpenApiTypes.BINARY, description="CSV leave application export")},
    )
    def get(self, request, pk):
        leave_request = get_object_or_404(
            selectors.applicant_request(pk, _actor_id(request)))
        return csv_api.stream(
            filename=f"elm-leave-request-{leave_request.pk}.csv",
            header=[
                "request_id", "applicant_user_id", "category", "request_type",
                "status", "starts_on", "ends_on", "requested_days", "purpose",
                "station_leave", "station_destination", "station_contact",
                "substitute_user_id", "offline_reference", "offline_sanctioned_on",
                "submitted_at", "decided_at", "decision_note",
            ],
            rows=[[
                leave_request.pk, leave_request.applicant_user_id,
                leave_request.category, leave_request.request_type,
                leave_request.status, leave_request.starts_on,
                leave_request.ends_on, leave_request.requested_days,
                leave_request.purpose, leave_request.station_leave,
                leave_request.station_destination, leave_request.station_contact,
                leave_request.substitute_user_id, leave_request.offline_reference,
                leave_request.offline_sanctioned_on, leave_request.submitted_at,
                leave_request.decided_at, leave_request.decision_note,
            ]],
        )


class MaintainLeaveRecordView(APIView):
    permission_classes = [MODULE, HasPermission(P_PROCESS)]

    @extend_schema(
        request=s.LeaveRecordMaintenanceSerializer,
        responses=s.LeaveRequestSerializer,
    )
    def post(self, request, pk):
        payload = s.LeaveRecordMaintenanceSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)
        reason = data.pop("reason")
        leave_request = maintain_leave_record(
            request_id=pk, actor_id=_actor_id(request),
            reason=reason, changes=data)
        return Response(s.LeaveRequestSerializer(leave_request).data)


class WithdrawRequestView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]

    @extend_schema(request=None, responses=s.LeaveRequestSerializer)
    def post(self, request, pk):
        leave_request = service.withdraw_request(
            request_id=pk, applicant_id=_actor_id(request))
        return Response(s.LeaveRequestSerializer(leave_request).data)


class CancelLeaveView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]

    @extend_schema(
        request=s.LeaveFollowUpSerializer,
        responses={status.HTTP_201_CREATED: s.LeaveRequestSerializer},
    )
    def post(self, request, pk):
        payload = s.LeaveFollowUpSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave_request = service.request_cancellation(
            request_id=pk, applicant_id=_actor_id(request),
            purpose=payload.validated_data["purpose"])
        return Response(s.LeaveRequestSerializer(leave_request).data,
                        status=status.HTTP_201_CREATED)


class ExtendLeaveView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]

    @extend_schema(
        request=s.ExtensionSerializer,
        responses={status.HTTP_201_CREATED: s.LeaveRequestSerializer},
    )
    def post(self, request, pk):
        payload = s.ExtensionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave_request = service.request_extension(
            request_id=pk, applicant_id=_actor_id(request),
            **payload.validated_data)
        return Response(s.LeaveRequestSerializer(leave_request).data,
                        status=status.HTTP_201_CREATED)


class ResumeLeaveView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]

    @extend_schema(
        request=s.ResumptionSerializer,
        responses={status.HTTP_201_CREATED: s.LeaveRequestSerializer},
    )
    def post(self, request, pk):
        payload = s.ResumptionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave_request = service.request_resumption(
            request_id=pk, applicant_id=_actor_id(request),
            **payload.validated_data)
        return Response(s.LeaveRequestSerializer(leave_request).data,
                        status=status.HTTP_201_CREATED)


class ReplaceSubstituteView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]

    @extend_schema(
        request=s.ReplaceSubstituteSerializer,
        responses=s.LeaveRequestSerializer,
    )
    def post(self, request, pk):
        payload = s.ReplaceSubstituteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave_request = service.replace_substitute(
            request_id=pk, applicant_id=_actor_id(request),
            **payload.validated_data)
        return Response(s.LeaveRequestSerializer(leave_request).data)


class SubstituteRequestListView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission(P_SUBSTITUTE)]
    serializer_class = s.LeaveRequestSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveRequest.objects.none()
        return selectors.for_substitute(_actor_id(self.request))


class SubstituteResponseView(APIView):
    permission_classes = [MODULE, HasPermission(P_SUBSTITUTE)]

    @extend_schema(
        request=s.SubstituteResponseSerializer,
        responses=s.LeaveRequestSerializer,
    )
    def post(self, request, pk):
        payload = s.SubstituteResponseSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave_request = service.respond_to_substitute(
            request_id=pk, actor_id=_actor_id(request),
            **payload.validated_data)
        return Response(s.LeaveRequestSerializer(leave_request).data)


class TaskQueueView(generics.ListAPIView):
    permission_classes = [
        MODULE, HasPermission(P_DECIDE, P_VIEW_QUEUE, require_all=False),
    ]
    serializer_class = s.WorkflowTaskQueueSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return WorkflowTask.objects.none()
        return selectors.assigned_pending_tasks(_actor_id(self.request))


class DecideTaskView(APIView):
    permission_classes = [MODULE, HasPermission(P_DECIDE)]

    @extend_schema(
        request=s.TaskDecisionSerializer,
        responses=s.LeaveRequestSerializer,
    )
    def post(self, request, request_id, task_id):
        payload = s.TaskDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave_request = service.decide_task(
            request_id=request_id, task_id=task_id,
            actor_id=_actor_id(request), **payload.validated_data)
        return Response(s.LeaveRequestSerializer(leave_request).data)


class ProcessYearEndView(APIView):
    permission_classes = [MODULE, HasPermission(P_YEAR_END)]

    @extend_schema(
        request=None,
        responses={status.HTTP_201_CREATED: s.YearEndResultSerializer},
    )
    def post(self, request, year):
        run = process_year_end(year=year, actor_user_id=_actor_id(request))
        return Response({
            "year": run.year,
            "processed_accounts": run.processed_accounts,
            "completed_at": run.completed_at,
        }, status=status.HTTP_201_CREATED)


class LeavePolicyListView(generics.ListCreateAPIView):
    permission_classes = [MODULE, HasPermission(P_POLICY)]
    serializer_class = s.LeavePolicySerializer
    queryset = LeavePolicy.objects.order_by("-year")


class LeavePolicyDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [MODULE, HasPermission(P_POLICY)]
    serializer_class = s.LeavePolicySerializer
    queryset = LeavePolicy.objects.all()


class ApprovalRouteListView(generics.ListCreateAPIView):
    permission_classes = [MODULE, HasPermission(P_POLICY)]
    serializer_class = s.ApprovalRouteSerializer
    queryset = ApprovalRoute.objects.select_related("unit").order_by(
        "category", "unit_id", "designation")


class ApprovalRouteDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [MODULE, HasPermission(P_POLICY)]
    serializer_class = s.ApprovalRouteSerializer
    queryset = ApprovalRoute.objects.select_related("unit")


class HolidayCalendarListView(generics.ListCreateAPIView):
    permission_classes = [MODULE, HasPermission(P_CALENDAR)]
    serializer_class = s.HolidayCalendarSerializer
    queryset = HolidayCalendar.objects.order_by("-year", "-created_at")


class HolidayCalendarHolidaysView(generics.ListCreateAPIView):
    permission_classes = [MODULE, HasPermission(P_CALENDAR)]
    serializer_class = s.HolidaySerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Holiday.objects.none()
        return Holiday.objects.filter(calendar_id=self.kwargs["calendar_id"]).order_by(
            "date", "name")

    @transaction.atomic
    def perform_create(self, serializer):
        calendar = get_object_or_404(
            HolidayCalendar.objects.select_for_update(),
            pk=self.kwargs["calendar_id"], status="draft")
        serializer.save(calendar=calendar)


class VacationPeriodListCreateView(generics.ListCreateAPIView):
    permission_classes = [MODULE, HasPermission(P_CALENDAR)]
    serializer_class = s.VacationPeriodSerializer
    queryset = VacationPeriod.objects.order_by("starts_on", "label")


class PublishHolidayCalendarView(APIView):
    permission_classes = [MODULE, HasPermission(P_CALENDAR)]

    @extend_schema(
        request=None,
        responses=s.HolidayCalendarSerializer,
    )
    @transaction.atomic
    def post(self, request, pk):
        calendar = get_object_or_404(
            HolidayCalendar.objects.select_for_update(), pk=pk)
        if calendar.status != "draft":
            raise ConflictError("Only a draft holiday calendar can be published.",
                                code="calendar_not_draft")
        HolidayCalendar.objects.filter(
            year=calendar.year, status="published").exclude(pk=calendar.pk).update(
                status="superseded")
        calendar.status = "published"
        calendar.published_at = timezone.now()
        calendar.published_by_user_id = _actor_id(request)
        calendar.save(update_fields=(
            "status", "published_at", "published_by_user_id", "updated_at"))
        return Response(s.HolidayCalendarSerializer(calendar).data)


class OrgUnitListView(generics.ListCreateAPIView):
    permission_classes = [MODULE, HasPermission(P_EMPLOYEE)]
    serializer_class = s.OrgUnitSerializer
    queryset = OrgUnit.objects.order_by("name")


class EmployeeProfileDetailView(APIView):
    permission_classes = [MODULE, HasPermission(P_PROCESS)]

    @extend_schema(responses=s.EmployeeProfileSerializer)
    def get(self, request, user_id):
        profile = get_object_or_404(
            EmployeeProfile.objects.select_related("unit"),
            user_id=user_id,
        )
        return Response({
            "user_id": profile.user_id,
            "employee_kind": profile.employee_kind,
            "unit_id": profile.unit_id,
            "designation": profile.designation,
            "requires_substitute": profile.requires_substitute,
            "is_director": profile.is_director,
            "is_active": profile.is_active,
        })


class MaintainEmployeeProfileView(APIView):
    permission_classes = [MODULE, HasPermission(P_EMPLOYEE)]

    @extend_schema(
        request=s.EmployeeProfileUpdateSerializer,
        responses=s.EmployeeProfileSerializer,
    )
    def put(self, request, user_id):
        payload = s.EmployeeProfileUpdateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        profile, _ = EmployeeProfile.objects.update_or_create(
            user_id=user_id, defaults=payload.validated_data)
        return Response({
            "user_id": profile.user_id,
            "employee_kind": profile.employee_kind,
            "unit_id": profile.unit_id,
            "designation": profile.designation,
            "requires_substitute": profile.requires_substitute,
            "is_director": profile.is_director,
            "is_active": profile.is_active,
        })


class LeaveReportSummaryView(APIView):
    permission_classes = [MODULE, HasPermission(P_REPORT)]

    @extend_schema(responses=s.LeaveReportSummarySerializer)
    def get(self, request):
        return Response({
            "requests_by_status": list(
                LeaveRequest.objects.values("status").annotate(
                    count=Count("id")).order_by("status")),
            "requests_by_category": list(
                LeaveRequest.objects.filter(request_type="leave").values(
                    "category").annotate(count=Count("id")).order_by("category")),
        })


class HealthView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    @extend_schema(responses=s.ModuleHealthSerializer)
    def get(self, request):
        return Response({"module": "employee_leave", "status": "available"})
