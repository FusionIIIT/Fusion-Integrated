from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave import contracts
from modules.leave.api.serializers import (
    ActionSerializer,
    ApplicationCreateSerializer,
    ApplicationReadSerializer,
    AuthorityRouteSerializer,
    CalendarCreateSerializer,
    CalendarReadSerializer,
    CancellationSerializer,
    CorrectionReadSerializer,
    CorrectionSerializer,
    ExtensionSerializer,
    OfflineLeaveSerializer,
    PolicySerializer,
    ResumptionCreateSerializer,
    ResumptionReadSerializer,
    SlaSerializer,
    TransactionSerializer,
)
from modules.leave.domain.workflow import LEAVE_TYPES
from modules.leave.models import (
    AuthorityRoute,
    HolidayCalendar,
    LeaveNotification,
    LeavePolicy,
    ResumptionRecord,
    SlaConfiguration,
)
from modules.leave.selectors.leave import account_transactions, assigned_tasks, visible_applications
from modules.leave.services import accounts, administration, applications
from modules.leave.services.errors import DependencyUnavailable


class LeaveAPIView(APIView):
    required_permission = "leave.application.view"

    def get_permissions(self):
        return [HasModuleGrant("leave")(), HasPermission(self.required_permission)()]


class ApplicationListView(LeaveAPIView):
    @extend_schema(responses=ApplicationReadSerializer(many=True), tags=["leave"])
    def get(self, request):
        rows = visible_applications(
            request.principal, status=request.query_params.get("status", ""),
            request_kind=request.query_params.get("request_kind", ""),
        ).order_by("-created_at", "-pk")
        return Response(ApplicationReadSerializer(rows, many=True).data)

    @extend_schema(request=ApplicationCreateSerializer, responses=ApplicationReadSerializer,
                   tags=["leave"])
    def post(self, request):
        self.check_permissions(request)
        self.required_permission = "leave.application.create"
        self.check_permissions(request)
        serializer = ApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row = applications.submit_leave(request.principal, serializer.validated_data)
        return Response(ApplicationReadSerializer(row).data, status=201)


class ApplicationDetailView(LeaveAPIView):
    @extend_schema(responses=ApplicationReadSerializer, tags=["leave"])
    def get(self, request, pk: int):
        row = get_object_or_404(visible_applications(request.principal), pk=pk)
        return Response(ApplicationReadSerializer(row).data)


class ApplicationActionView(LeaveAPIView):
    required_permission = "leave.application.view"

    def get_permissions(self):
        event = self.request.data.get("event", "") if self.request.method == "POST" else ""
        codes = {
            "accept_substitute": "leave.substitute.update",
            "decline_substitute": "leave.substitute.update",
            "replace_substitute": "leave.application.update",
            "unit_head_decision": "leave.application.review",
            "unit_head_cancel": "leave.application.review",
            "route": "leave.application.review",
            "sanction": "leave.application.approve",
            "director_sanction": "leave.application.approve",
            "withdraw": "leave.application.delete",
        }
        return [HasModuleGrant("leave")(), HasPermission(codes.get(event, "leave.application.view"))()]

    @extend_schema(request=ActionSerializer, responses=ApplicationReadSerializer,
                   tags=["leave"])
    def post(self, request, pk: int):
        serializer = ActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row = get_object_or_404(visible_applications(request.principal), pk=pk)
        values = dict(serializer.validated_data)
        event = values.pop("event")
        substitute_user_id = values.pop("substitute_user_id", None)
        row = applications.act_on_application(
            request.principal, row, event=event,
            outcome=values.pop("outcome", ""), note=values.pop("note", ""),
            substitute_user_id=substitute_user_id,
        )
        return Response(ApplicationReadSerializer(row).data)


class CancellationView(LeaveAPIView):
    required_permission = "leave.application.delete"

    @extend_schema(request=CancellationSerializer, responses=ApplicationReadSerializer,
                   tags=["leave"])
    def post(self, request):
        serializer = CancellationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        original = get_object_or_404(visible_applications(request.principal),
                                     pk=serializer.validated_data["original_application_id"])
        child = applications.request_cancellation(request.principal, original)
        return Response(ApplicationReadSerializer(child).data, status=201)


class ExtensionView(LeaveAPIView):
    required_permission = "leave.application.create"

    @extend_schema(request=ExtensionSerializer, responses=ApplicationReadSerializer,
                   tags=["leave"])
    def post(self, request):
        serializer = ExtensionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        original = get_object_or_404(visible_applications(request.principal),
                                     pk=values["original_application_id"])
        child = applications.request_extension(
            request.principal, original, values["end_date"],
            values.get("purpose", ""), values.get("substitute_user_id"),
        )
        return Response(ApplicationReadSerializer(child).data, status=201)


class AssignedTasksView(LeaveAPIView):
    required_permission = "leave.application.review"

    def get_permissions(self):
        return [HasModuleGrant("leave")(), HasPermission(
            "leave.application.review", "leave.application.approve",
            "leave.substitute.update", "leave.resumption.review")()]

    @extend_schema(responses=ApplicationReadSerializer(many=True), tags=["leave"])
    def get(self, request):
        rows = assigned_tasks(request.principal)
        return Response(ApplicationReadSerializer(rows, many=True).data)


class BalanceView(LeaveAPIView):
    required_permission = "leave.balance.view"

    @extend_schema(responses=dict, tags=["leave"])
    def get(self, request):
        try:
            people = contracts.get_employees([request.principal.user_id])
        except Exception as exc:
            raise DependencyUnavailable("IAM employee directory is unavailable.") from exc
        person = people.get(request.principal.user_id)
        if not person:
            raise ValidationError("Employee profile is not available from IAM.")
        try:
            year = int(request.query_params.get("year", timezone.localdate().year))
        except (TypeError, ValueError) as exc:
            raise ValidationError({"year": "Year must be a number."}) from exc
        balances = []
        for leave_type in LEAVE_TYPES:
            accounts.ensure_annual_credit(
                user_id=person.user_id, leave_type=leave_type, year=year,
                employee_kind=person.kind)
            policy = accounts.policy_for(leave_type)
            balances.append({
                "leave_type": leave_type, "year": year,
                "entitlement": str(policy.annual_entitlement),
                "available": str(accounts.balance(person.user_id, leave_type, year)),
                "carry_forward": policy.carry_forward,
            })
        transactions = account_transactions(person.user_id).order_by("-created_at")
        return Response({"balances": balances,
                         "history": TransactionSerializer(transactions, many=True).data})


class ApplicationExportView(LeaveAPIView):
    required_permission = "leave.application.export"

    @extend_schema(responses={(200, "text/html"): None}, tags=["leave"])
    def get(self, request, pk: int):
        from html import escape

        row = get_object_or_404(visible_applications(request.principal), pk=pk)
        values = [
            ("Request", str(row.pk)), ("Leave category", row.leave_type),
            ("Period", f"{row.start_date} to {row.end_date}"),
            ("Days", str(row.requested_days)), ("Status", row.status),
            ("Purpose", row.purpose),
        ]
        body = "".join(f"<dt>{escape(k)}</dt><dd>{escape(v)}</dd>" for k, v in values)
        return HttpResponse(f"<!doctype html><title>Leave request</title><dl>{body}</dl>",
                            content_type="text/html; charset=utf-8")


class PolicyView(LeaveAPIView):
    required_permission = "leave.policy.manage"

    @extend_schema(responses=PolicySerializer(many=True), tags=["leave"])
    def get(self, request):
        return Response(PolicySerializer(LeavePolicy.objects.all(), many=True).data)

    @extend_schema(request=PolicySerializer, responses=PolicySerializer, tags=["leave"])
    def post(self, request):
        serializer = PolicySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        policy = administration.save_policy(
            actor_user_id=request.principal.user_id, data=serializer.validated_data)
        return Response(PolicySerializer(policy).data, status=201)


class AuthorityRouteView(LeaveAPIView):
    required_permission = "leave.policy.manage"

    @extend_schema(responses=AuthorityRouteSerializer(many=True), tags=["leave"])
    def get(self, request):
        return Response(AuthorityRouteSerializer(AuthorityRoute.objects.all(), many=True).data)

    @extend_schema(request=AuthorityRouteSerializer, responses=AuthorityRouteSerializer,
                   tags=["leave"])
    def post(self, request):
        serializer = AuthorityRouteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        route = administration.save_route(
            actor_user_id=request.principal.user_id, data=serializer.validated_data)
        return Response(AuthorityRouteSerializer(route).data, status=201)


class CalendarView(LeaveAPIView):
    required_permission = "leave.calendar.manage"

    @extend_schema(responses=CalendarReadSerializer(many=True), tags=["leave"])
    def get(self, request):
        return Response(CalendarReadSerializer(
            HolidayCalendar.objects.prefetch_related("dates").all(), many=True).data)

    @extend_schema(request=CalendarCreateSerializer, responses=CalendarReadSerializer,
                   tags=["leave"])
    def post(self, request):
        serializer = CalendarCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        calendar = administration.create_calendar(
            actor_user_id=request.principal.user_id, name=values["name"],
            effective_from=values["effective_from"], effective_to=values.get("effective_to"),
            dates=values["dates"],
        )
        return Response(CalendarReadSerializer(calendar).data, status=201)


class CalendarPublishView(LeaveAPIView):
    required_permission = "leave.calendar.publish"
    serializer_class = CalendarReadSerializer

    @extend_schema(responses=CalendarReadSerializer, tags=["leave"])
    def post(self, request, pk: int):
        calendar = get_object_or_404(HolidayCalendar, pk=pk)
        return Response(CalendarReadSerializer(
            administration.publish_calendar(calendar)).data)


class OfflineLeaveView(LeaveAPIView):
    required_permission = "leave.record.import"

    @extend_schema(request=OfflineLeaveSerializer, responses=ApplicationReadSerializer,
                   tags=["leave"])
    def post(self, request):
        serializer = OfflineLeaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row = administration.record_offline_leave(
            actor_user_id=request.principal.user_id, data=serializer.validated_data)
        return Response(ApplicationReadSerializer(row).data, status=201)


class RecordCorrectionView(LeaveAPIView):
    required_permission = "leave.record.update"

    @extend_schema(request=CorrectionSerializer, responses=CorrectionReadSerializer,
                   tags=["leave"])
    def post(self, request):
        serializer = CorrectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        correction = administration.correct_record(
            actor_user_id=request.principal.user_id, data=serializer.validated_data)
        return Response(CorrectionReadSerializer(correction).data, status=201)


class SlaConfigurationView(LeaveAPIView):
    required_permission = "leave.sla.manage"

    @extend_schema(responses=SlaSerializer(many=True), tags=["leave"])
    def get(self, request):
        return Response(SlaSerializer(SlaConfiguration.objects.all(), many=True).data)

    @extend_schema(request=SlaSerializer, responses=SlaSerializer, tags=["leave"])
    def post(self, request):
        serializer = SlaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task_kind = serializer.validated_data["task_kind"]
        configuration = administration.save_sla(
            actor_user_id=request.principal.user_id, task_kind=task_kind,
            data=serializer.validated_data)
        return Response(SlaSerializer(configuration).data, status=201)


class ResumptionListCreateView(LeaveAPIView):
    required_permission = "leave.application.view"

    def get_permissions(self):
        if self.request.method == "POST":
            return [HasModuleGrant("leave")(), HasPermission("leave.application.create")()]
        return [HasModuleGrant("leave")(), HasPermission(
            "leave.application.view", "leave.resumption.review")()]

    @extend_schema(responses=ResumptionReadSerializer(many=True), tags=["leave"])
    def get(self, request):
        rows = ResumptionRecord.objects.filter(
            employee_user_id=request.principal.user_id)
        if request.principal.has_permission("leave.resumption.review"):
            rows = ResumptionRecord.objects.filter(
                application__final_authority_user_id=request.principal.user_id)
        return Response(ResumptionReadSerializer(rows, many=True).data)

    @extend_schema(request=ResumptionCreateSerializer, responses=ResumptionReadSerializer,
                   tags=["leave"])
    def post(self, request):
        serializer = ResumptionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = get_object_or_404(visible_applications(request.principal),
                                         pk=serializer.validated_data["application_id"])
        row = applications.record_resumption(
            request.principal, application, serializer.validated_data["actual_resumption_date"])
        return Response(ResumptionReadSerializer(row).data, status=201)


class ResumptionReviewView(LeaveAPIView):
    required_permission = "leave.resumption.review"
    serializer_class = ResumptionReadSerializer

    @extend_schema(responses=ResumptionReadSerializer, tags=["leave"])
    def post(self, request, pk: int):
        record = get_object_or_404(ResumptionRecord, pk=pk)
        return Response(ResumptionReadSerializer(
            applications.review_resumption(request.principal, record)).data)


class NotificationStatusView(LeaveAPIView):
    required_permission = "leave.application.view"

    @extend_schema(responses=dict, tags=["leave"])
    def get(self, request):
        rows = LeaveNotification.objects.filter(
            recipient_user_id=request.principal.user_id).order_by("-created_at")[:100]
        return Response({"notifications": [
            {"topic": row.topic, "status": row.status, "created_at": row.created_at}
            for row in rows
        ]})
