"""ELM HTTP endpoints. Querysets scope employee data before serialization."""
from datetime import date

from django.db.models import Q
from django.db import transaction
from django.http import HttpResponse
from django.utils.html import escape
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.directory import contracts as directory
from modules.leave.api import serializers as s
from modules.leave.models import (
    EmployeeProfile, HolidayCalendar, LeaveAccountEntry, LeaveAuditEvent, LeaveBalance,
    LeaveCategory, LeavePolicy, LeaveRequest, LeaveRouteConfiguration,
    LeaveSanction, LeaveSLAConfiguration, WorkflowTask,
)
from modules.leave.services import requests as service
from modules.leave.domain.state_machine import normalize_role


class _LeaveView:
    """Common module gate; IAM owns credentials and the principal."""
    @property
    def actor(self):
        return self.request.principal

    def rule_error(self, exc):
        raise ValidationError({"detail": str(exc)}) from exc


class CategoryListView(_LeaveView, generics.ListAPIView):
    serializer_class = s.LeaveCategorySerializer
    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.request.view_self")]
    queryset = LeaveCategory.objects.all()


class EmployeeSearchView(_LeaveView, APIView):
    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.request.create")]
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if len(query) < 2:
            return Response([])
        results = []
        for user in directory.search(query, limit=25):
            if user.user_id == self.actor.user_id or user.kind not in {"faculty", "staff"}:
                continue
            if not EmployeeProfile.objects.filter(user_id=user.user_id, active=True).exists():
                continue
            results.append({"user_id": user.user_id, "label": user.display_name, "kind": user.kind})
        return Response(results)


class BalanceListView(_LeaveView, generics.ListAPIView):
    serializer_class = s.LeaveBalanceSerializer
    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.balance.view_self")]
    def get_queryset(self):
        return LeaveBalance.objects.filter(employee_id=self.actor.user_id).select_related("category").order_by("year", "category_id")


class AccountHistoryView(_LeaveView, generics.ListAPIView):
    serializer_class = s.LeaveAccountEntrySerializer if hasattr(s, "LeaveAccountEntrySerializer") else None
    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.balance.view_self")]
    def get_queryset(self):
        return LeaveAccountEntry.objects.filter(employee_id=self.actor.user_id).select_related("category").order_by("-created_at")


class RequestListCreateView(_LeaveView, generics.ListCreateAPIView):
    permission_classes = [HasModuleGrant("leave_management")]
    def get_permissions(self):
        permission = (HasPermission("leave_management.request.create") if self.request.method == "POST"
                     else HasPermission("leave_management.request.view_self", "leave_management.request.view_all"))
        return [permission(), HasModuleGrant("leave_management")()]
    def get_serializer_class(self):
        return s.LeaveDraftSerializer if self.request.method == "POST" else s.LeaveRequestSerializer
    def get_queryset(self):
        qs = LeaveRequest.objects.select_related("category", "parent_request")
        if self.actor.has_permission("leave_management.request.view_all"):
            return qs
        return qs.filter(employee_id=self.actor.user_id)
    def create(self, request, *args, **kwargs):
        payload = s.LeaveDraftSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        request_obj = LeaveRequest.objects.create(employee_id=self.actor.user_id, **payload.validated_data)
        return Response(s.LeaveRequestSerializer(request_obj).data, status=status.HTTP_201_CREATED)


class RequestDetailView(_LeaveView, generics.RetrieveAPIView):
    serializer_class = s.LeaveRequestSerializer
    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.request.view_self", "leave_management.request.view_all")]
    def get_queryset(self):
        qs = LeaveRequest.objects.select_related("category", "parent_request")
        return qs if self.actor.has_permission("leave_management.request.view_all") else qs.filter(employee_id=self.actor.user_id)


class RequestHistoryView(_LeaveView, generics.ListAPIView):
    serializer_class = s.LeaveAuditEventSerializer
    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.request.view_self", "leave_management.request.view_all")]
    def get_queryset(self):
        requests = LeaveRequest.objects.all()
        if not self.actor.has_permission("leave_management.request.view_all"):
            requests = requests.filter(employee_id=self.actor.user_id)
        request_obj = get_object_or_404(requests, pk=self.kwargs["pk"])
        return LeaveAuditEvent.objects.filter(request=request_obj).order_by("occurred_at", "id")


class SubmitView(_LeaveView, APIView):
    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.request.create")]
    def post(self, request, pk):
        try:
            obj = service.submit_request(pk, self.actor.user_id)
        except (service.LeaveRuleViolation, EmployeeProfile.DoesNotExist, LeaveRequest.DoesNotExist) as exc:
            self.rule_error(exc)
        return Response(s.LeaveRequestSerializer(obj).data)


class WithdrawView(_LeaveView, APIView):
    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.request.withdraw")]
    def post(self, request, pk):
        try:
            obj = service.withdraw_request(pk, self.actor.user_id)
        except (service.LeaveRuleViolation, LeaveRequest.DoesNotExist) as exc:
            self.rule_error(exc)
        return Response(s.LeaveRequestSerializer(obj).data)


class CancellationView(_LeaveView, APIView):
    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.request.cancel")]
    def post(self, request, pk):
        try:
            obj = service.request_cancellation(pk, self.actor.user_id)
        except (service.LeaveRuleViolation, LeaveRequest.DoesNotExist, EmployeeProfile.DoesNotExist) as exc:
            self.rule_error(exc)
        return Response(s.LeaveRequestSerializer(obj).data, status=status.HTTP_201_CREATED)


class ExtensionView(_LeaveView, APIView):
    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.request.create")]
    def post(self, request, pk):
        payload = s.LeaveExtensionInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            obj = service.request_extension(pk, self.actor.user_id, **payload.validated_data)
        except (service.LeaveRuleViolation, LeaveRequest.DoesNotExist, EmployeeProfile.DoesNotExist) as exc:
            self.rule_error(exc)
        return Response(s.LeaveRequestSerializer(obj).data, status=status.HTTP_201_CREATED)


class ResumptionView(_LeaveView, APIView):
    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.request.create")]
    def post(self, request, pk):
        payload = s.LeaveResumptionInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            obj = service.submit_resumption(pk, self.actor.user_id, **payload.validated_data)
        except (service.LeaveRuleViolation, LeaveRequest.DoesNotExist) as exc:
            self.rule_error(exc)
        return Response(s.LeaveRequestSerializer(obj).data, status=status.HTTP_201_CREATED)


class RequestPrintView(_LeaveView, APIView):
    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.request.view_self", "leave_management.request.view_all")]
    def get(self, request, pk):
        qs = LeaveRequest.objects.select_related("category")
        if not self.actor.has_permission("leave_management.request.view_all"):
            qs = qs.filter(employee_id=self.actor.user_id)
        obj = get_object_or_404(qs, pk=pk)
        rows = {
            "Employee": obj.employee_id, "Leave category": f"{obj.category_id} · {obj.category.label}",
            "Period": f"{obj.start_date} to {obj.end_date}", "Duration": f"{obj.duration_days} days",
            "Status": obj.get_status_display(), "Purpose / reason": obj.reason,
            "Station Leave": "Yes" if obj.station_leave else "No",
            "Destination": obj.station_destination or "—",
        }
        details = "".join(f"<dt>{escape(label)}</dt><dd>{escape(str(value))}</dd>" for label, value in rows.items())
        return HttpResponse(
            "<!doctype html><html><head><meta charset='utf-8'><title>Leave application</title>"
            "<style>body{font:16px system-ui;max-width:760px;margin:3rem auto;color:#172033}"
            "dt{font-weight:600;margin-top:1rem}dd{margin:.25rem 0}button{margin-top:2rem}"
            "@media print{button{display:none}body{margin:1cm}}</style></head><body>"
            f"<h1>Leave application #{obj.pk}</h1><dl>{details}</dl>"
            "<button onclick='window.print()'>Print / Save as PDF</button></body></html>",
            content_type="text/html; charset=utf-8",
        )


class SubstituteResponseView(_LeaveView, APIView):
    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.substitute.respond")]
    def post(self, request, pk):
        accepted = request.data.get("decision") == "accept"
        if request.data.get("decision") not in {"accept", "decline"}:
            raise ValidationError({"decision": "Use accept or decline."})
        try:
            obj = service.respond_to_substitute(pk, self.actor.user_id, accepted=accepted)
        except (service.LeaveRuleViolation, LeaveRequest.DoesNotExist) as exc:
            self.rule_error(exc)
        return Response(s.LeaveRequestSerializer(obj).data)


class SubstituteInboxView(_LeaveView, generics.ListAPIView):
    serializer_class = s.LeaveRequestSerializer
    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.substitute.respond")]
    def get_queryset(self):
        return LeaveRequest.objects.filter(substitute_user_id=self.actor.user_id,
                                           status=LeaveRequest.Status.AWAITING_SUBSTITUTE).select_related("category")


class ReplaceSubstituteView(_LeaveView, APIView):
    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.request.create")]
    def post(self, request, pk):
        try:
            obj = service.replace_declined_substitute(pk, self.actor.user_id,
                                                      int(request.data.get("substitute_user_id")))
        except (service.LeaveRuleViolation, LeaveRequest.DoesNotExist, TypeError, ValueError) as exc:
            self.rule_error(exc)
        return Response(s.LeaveRequestSerializer(obj).data)


class TaskListView(_LeaveView, generics.ListAPIView):
    serializer_class = s.LeaveTaskSerializer
    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.workflow.task.view")]
    def get_queryset(self):
        role_names = [normalize_role(role) for role in self.actor.roles]
        return WorkflowTask.objects.filter(state=WorkflowTask.State.PENDING).filter(
            Q(assigned_user_id=self.actor.user_id) | Q(role__in=role_names)
        ).select_related("request").order_by("created_at")


class TaskDecisionView(_LeaveView, APIView):
    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.workflow.task.decide")]
    def post(self, request, pk):
        task = get_object_or_404(WorkflowTask, pk=pk, state=WorkflowTask.State.PENDING)
        actor_roles = {normalize_role(role) for role in self.actor.roles}
        if task.assigned_user_id != self.actor.user_id and task.role not in actor_roles:
            raise PermissionDenied()
        try:
            obj = service.decide_task(pk, self.actor.user_id,
                                      decision=request.data.get("decision", ""),
                                      notes=request.data.get("notes", ""))
        except (service.LeaveRuleViolation, WorkflowTask.DoesNotExist) as exc:
            self.rule_error(exc)
        return Response(s.LeaveRequestSerializer(obj).data)


class PolicyView(_LeaveView, APIView):
    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.policy.view", "leave_management.policy.manage")]
    def get(self, request):
        policy = LeavePolicy.objects.filter(policy_key="current").first()
        return Response(s.LeavePolicySerializer(policy).data if policy else None)
    def put(self, request):
        if not self.actor.has_permission("leave_management.policy.manage"):
            raise PermissionDenied()
        policy = LeavePolicy.objects.filter(policy_key="current").first()
        payload = s.LeavePolicySerializer(policy, data=request.data, partial=policy is not None)
        payload.is_valid(raise_exception=True)
        obj = payload.save(updated_by_user_id=self.actor.user_id)
        return Response(s.LeavePolicySerializer(obj).data)


class HolidayCalendarListView(_LeaveView, generics.ListAPIView):
    serializer_class = s.HolidayCalendarSerializer
    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.calendar.view")]
    def get_queryset(self):
        return HolidayCalendar.objects.filter(state=HolidayCalendar.State.PUBLISHED).order_by("-year", "-revision")


class HolidayCalendarDraftView(_LeaveView, APIView):
    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.calendar.manage")]
    def post(self, request):
        payload = s.HolidayCalendarDraftSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        year, holidays = payload.validated_data["year"], payload.validated_data["holidays"]
        if not isinstance(holidays, list):
            raise ValidationError({"holidays": "Must be a list of calendar dates."})
        for item in holidays:
            if not isinstance(item, dict) or not item.get("date"):
                raise ValidationError({"holidays": "Each entry needs a date and description."})
            try:
                date.fromisoformat(item["date"])
            except (TypeError, ValueError) as exc:
                raise ValidationError({"holidays": "Calendar dates must use YYYY-MM-DD."}) from exc
        with transaction.atomic():
            revision = (HolidayCalendar.objects.select_for_update().filter(year=year).order_by("-revision").values_list("revision", flat=True).first() or 0) + 1
            obj = HolidayCalendar.objects.create(year=year, revision=revision, holidays=holidays)
        return Response(s.HolidayCalendarSerializer(obj).data, status=status.HTTP_201_CREATED)


class HolidayCalendarPublishView(_LeaveView, APIView):
    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.calendar.manage")]
    def post(self, request, pk):
        with transaction.atomic():
            obj = get_object_or_404(HolidayCalendar.objects.select_for_update(), pk=pk)
            if obj.state != HolidayCalendar.State.DRAFT:
                raise ValidationError({"detail": "Only a draft calendar can be published."})
            HolidayCalendar.objects.filter(year=obj.year, state=HolidayCalendar.State.PUBLISHED).update(state=HolidayCalendar.State.SUPERSEDED)
            obj.state = HolidayCalendar.State.PUBLISHED
            obj.published_by_user_id = self.actor.user_id
            obj.published_at = timezone.now()
            obj.save(update_fields=["state", "published_by_user_id", "published_at"])
        return Response(s.HolidayCalendarSerializer(obj).data)


class RouteConfigurationListView(_LeaveView, generics.ListCreateAPIView):
    serializer_class = s.LeaveRouteConfigurationSerializer
    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.routing.manage")]
    queryset = LeaveRouteConfiguration.objects.select_related("category").all()
    def perform_create(self, serializer):
        serializer.save(updated_by_user_id=self.actor.user_id)


class RouteConfigurationDetailView(_LeaveView, generics.RetrieveUpdateAPIView):
    serializer_class = s.LeaveRouteConfigurationSerializer
    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.routing.manage")]
    queryset = LeaveRouteConfiguration.objects.select_related("category").all()
    def perform_update(self, serializer):
        serializer.save(updated_by_user_id=self.actor.user_id)


class SLAConfigurationListView(_LeaveView, generics.ListCreateAPIView):
    serializer_class = s.LeaveSLAConfigurationSerializer
    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.sla.manage")]
    queryset = LeaveSLAConfiguration.objects.all()
    def perform_create(self, serializer):
        serializer.save(updated_by_user_id=self.actor.user_id)


class SLAConfigurationDetailView(_LeaveView, generics.RetrieveUpdateAPIView):
    serializer_class = s.LeaveSLAConfigurationSerializer
    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.sla.manage")]
    queryset = LeaveSLAConfiguration.objects.all()
    def perform_update(self, serializer):
        serializer.save(updated_by_user_id=self.actor.user_id)


class OfflineLeaveView(_LeaveView, APIView):
    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.records.manage")]
    def post(self, request):
        payload = s.OfflineLeaveInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        values = payload.validated_data
        try:
            obj = service.record_offline_sanctioned_leave(
                employee_id=values["employee_id"], category_code=values["category_code"].code,
                start_date=values["start_date"], end_date=values["end_date"], reason=values["reason"],
                sanction_reference=values["sanction_reference"], evidence_reference=values["evidence_reference"],
                actor_user_id=self.actor.user_id,
            )
        except (service.LeaveRuleViolation, EmployeeProfile.DoesNotExist, LeaveCategory.DoesNotExist) as exc:
            self.rule_error(exc)
        return Response(s.LeaveRequestSerializer(obj).data, status=status.HTTP_201_CREATED)


class AccountAdjustmentView(_LeaveView, APIView):
    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.records.manage")]
    def post(self, request):
        payload = s.AccountAdjustmentInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        values = payload.validated_data
        try:
            entry = service.record_account_adjustment(
                employee_id=values["employee_id"], category=values["category_code"], year=values["year"],
                amount=values["amount"], reference=values["reference"], explanation=values["explanation"],
                actor_user_id=self.actor.user_id,
            )
        except service.LeaveRuleViolation as exc:
            self.rule_error(exc)
        return Response(s.LeaveAccountEntrySerializer(entry).data, status=status.HTTP_201_CREATED)
