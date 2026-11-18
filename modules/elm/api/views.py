from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import HttpResponse
import csv
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiResponse
from fusion_auth.client import IamUnavailable
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api import serializers as s
from modules.elm.domain.policy import PolicyViolation, validate_hierarchy, validate_params
from modules.elm.models import CalendarEntry, CalendarVersion, LeavePolicy, LeaveRequest, LedgerEntry, Notification, OfflineLeaveRecord
from modules.elm.services import cancellation, ledger, offline, records, requests as request_service, resumption, workflow

MODULE = HasModuleGrant("elm")
P_VIEW = "elm.leave_request.view"
P_CREATE = "elm.leave_request.create"
P_DELETE = "elm.leave_request.delete"
P_UPDATE = "elm.leave_request.update"
P_REVIEW = "elm.leave_request.review"
P_APPROVE = "elm.leave_request.approve"
P_BALANCE = "elm.leave_balance.view"
P_SUB_REVIEW = "elm.substitution.review"
P_RESUME_REVIEW = "elm.resumption.review"
P_POLICY = "elm.policy.manage"
P_CALENDAR = "elm.calendar.publish"
P_OFFLINE = "elm.offline_record.create"

class ELMView(APIView):
    permission_classes = [MODULE]
    def actor(self, request):
        return request.principal
    def roles(self, request):
        p = self.actor(request)
        return list({x for x in [p.active_role, *p.roles] if x})
    def can_view_request(self, request, req):
        p = self.actor(request)
        if req.user_id == p.user_id or p.has_permission("elm.leave_request.view_all"):
            return True
        return (req.current_role in self.roles(request)
                and p.has_any_permission(P_REVIEW, P_APPROVE))
    def error(self, exc):
        if isinstance(exc, ObjectDoesNotExist):
            return Response({"error": {"code": "not_found", "message": "The requested ELM record was not found.", "details": [], "request_id": ""}}, status=404)
        if isinstance(exc, IamUnavailable):
            return Response({"error": {"code": "identity_service_unavailable", "message": "The identity directory is temporarily unavailable. Please retry.", "details": [], "request_id": ""}}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        if isinstance(exc, PolicyViolation):
            return Response({"error": {"code": exc.code, "message": str(exc), "details": [], "request_id": ""}}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"error": {"code": "invalid_request", "message": str(exc), "details": [], "request_id": ""}}, status=status.HTTP_400_BAD_REQUEST)

class RequestListView(ELMView):
    permission_classes = [MODULE, HasPermission(P_VIEW, P_CREATE)]
    @extend_schema(responses=s.LeaveRequestSerializer(many=True))
    def get(self, request):
        p = self.actor(request)
        show_all = request.query_params.get("all", "false").lower() == "true"
        qs = (LeaveRequest.objects.all() if show_all and p.has_permission("elm.leave_request.view_all")
              else LeaveRequest.objects.filter(user_id=p.user_id))
        status_filter = request.query_params.get("status")
        category = request.query_params.get("category")
        if status_filter: qs = qs.filter(status=status_filter)
        if category: qs = qs.filter(category=category)
        return Response(s.LeaveRequestSerializer(qs.order_by("-created_at")[:200], many=True).data)
    @extend_schema(request=s.LeaveCreateSerializer, responses={201: s.LeaveRequestSerializer})
    def post(self, request):
        p = self.actor(request)
        payload = s.LeaveCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            req = request_service.create(user_id=p.user_id, actor_role=p.active_role or "employee", **payload.validated_data)
        except (IamUnavailable, PolicyViolation, ValueError) as exc:
            return self.error(exc)
        return Response(s.LeaveRequestSerializer(req).data, status=status.HTTP_201_CREATED)

class RequestDetailView(ELMView):
    permission_classes = [MODULE, HasPermission(P_VIEW)]
    @extend_schema(responses=s.LeaveRequestSerializer)
    def get(self, request, pk):
        req = LeaveRequest.objects.filter(pk=pk).first()
        if not req or not self.can_view_request(request, req):
            return Response(status=404)
        return Response(s.LeaveRequestSerializer(req).data)

class WithdrawView(ELMView):
    permission_classes = [MODULE, HasPermission(P_DELETE)]
    @extend_schema(responses=s.LeaveRequestSerializer)
    def post(self, request, pk):
        try: req = request_service.withdraw(request_id=pk, actor_user_id=self.actor(request).user_id)
        except (LeaveRequest.DoesNotExist, PolicyViolation) as exc: return self.error(exc)
        return Response(s.LeaveRequestSerializer(req).data)

class CancellationView(ELMView):
    permission_classes = [MODULE, HasPermission(P_UPDATE)]
    @extend_schema(request=s.CancellationSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk):
        payload = s.CancellationSerializer(data=request.data); payload.is_valid(raise_exception=True)
        try: req = cancellation.request_cancellation(request_id=pk, actor_user_id=self.actor(request).user_id, **payload.validated_data)
        except (LeaveRequest.DoesNotExist, PolicyViolation) as exc: return self.error(exc)
        return Response(s.LeaveRequestSerializer(req).data)

class ExtensionView(ELMView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]
    @extend_schema(request=s.ExtensionSerializer, responses={201: s.LeaveRequestSerializer})
    def post(self, request, pk):
        payload = s.ExtensionSerializer(data=request.data); payload.is_valid(raise_exception=True)
        try: req = request_service.apply_extension(request_id=pk, actor_user_id=self.actor(request).user_id, **payload.validated_data)
        except (LeaveRequest.DoesNotExist, IamUnavailable, PolicyViolation, ValueError) as exc: return self.error(exc)
        return Response(s.LeaveRequestSerializer(req).data, status=201)

class ResumptionSubmitView(ELMView):
    permission_classes = [MODULE, HasPermission(P_UPDATE)]
    @extend_schema(request=s.ResumptionSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk):
        payload = s.ResumptionSerializer(data=request.data); payload.is_valid(raise_exception=True)
        try: req = resumption.submit(request_id=pk, actor_user_id=self.actor(request).user_id, **payload.validated_data)
        except (LeaveRequest.DoesNotExist, PolicyViolation) as exc: return self.error(exc)
        return Response(s.LeaveRequestSerializer(req).data)

class SubstitutionListView(ELMView):
    permission_classes = [MODULE, HasPermission(P_SUB_REVIEW)]
    @extend_schema(responses=s.LeaveRequestSerializer(many=True))
    def get(self, request):
        p = self.actor(request)
        qs = LeaveRequest.objects.filter(substitute_user_id=p.user_id, status="awaiting_substitute", substitute_status="pending").order_by("submitted_at")
        return Response(s.LeaveRequestSerializer(qs[:200], many=True).data)

class SubstituteResponseView(ELMView):
    permission_classes = [MODULE, HasPermission(P_SUB_REVIEW)]
    @extend_schema(request=s.SubstituteResponseSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk):
        payload = s.SubstituteResponseSerializer(data=request.data); payload.is_valid(raise_exception=True)
        try: req = workflow.respond_substitute(request_id=pk, actor_user_id=self.actor(request).user_id, **payload.validated_data)
        except (LeaveRequest.DoesNotExist, PolicyViolation) as exc: return self.error(exc)
        return Response(s.LeaveRequestSerializer(req).data)

class ReplacementSubstituteView(ELMView):
    permission_classes = [MODULE, HasPermission(P_UPDATE)]
    @extend_schema(request=s.ReplacementSubstituteSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk):
        payload = s.ReplacementSubstituteSerializer(data=request.data); payload.is_valid(raise_exception=True)
        try: req = workflow.nominate_replacement(request_id=pk, actor_user_id=self.actor(request).user_id, **payload.validated_data)
        except (LeaveRequest.DoesNotExist, IamUnavailable, PolicyViolation, ValueError) as exc: return self.error(exc)
        return Response(s.LeaveRequestSerializer(req).data)

class QueueView(ELMView):
    permission_classes = [MODULE, HasPermission(P_REVIEW, P_APPROVE)]
    @extend_schema(responses=s.LeaveRequestSerializer(many=True))
    def get(self, request):
        roles = self.roles(request)
        qs = LeaveRequest.objects.filter(
            current_role__in=roles,
            status__in=("awaiting_unit_head", "awaiting_establishment", "awaiting_sanction", "awaiting_director", "cancellation_pending"),
        ).order_by("submitted_at")
        return Response(s.LeaveRequestSerializer(qs[:200], many=True).data)

class DecideView(ELMView):
    permission_classes = [MODULE, HasPermission(P_REVIEW, P_APPROVE)]
    @extend_schema(request=s.DecisionSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk):
        payload = s.DecisionSerializer(data=request.data); payload.is_valid(raise_exception=True)
        try: req = workflow.decide(request_id=pk, actor_user_id=self.actor(request).user_id, actor_roles=self.roles(request), **payload.validated_data)
        except (LeaveRequest.DoesNotExist, PolicyViolation) as exc: return self.error(exc)
        return Response(s.LeaveRequestSerializer(req).data)

class BalanceView(ELMView):
    permission_classes = [MODULE, HasPermission(P_BALANCE)]
    @extend_schema(responses=s.BalanceSerializer(many=True))
    def get(self, request):
        p = self.actor(request)
        try:
            year = int(request.query_params.get("year", timezone.localdate().year))
        except (TypeError, ValueError):
            return Response({"error": {"code": "invalid_year", "message": "year must be a four-digit year."}}, status=400)
        try:
            ledger.ensure_annual_credits(p.user_id, year)
        except IamUnavailable as exc:
            return self.error(exc)
        rows = [{"category": c, "year": year, "balance": ledger.balance(p.user_id, c, year)} for c in ("CL", "RH", "SCL", "EL", "COL", "VL")]
        return Response(rows)

class HistoryView(ELMView):
    permission_classes = [MODULE, HasPermission(P_VIEW)]
    @extend_schema(responses=s.LedgerEntrySerializer(many=True))
    def get(self, request, pk):
        req = LeaveRequest.objects.filter(pk=pk).first()
        if not req or not self.can_view_request(request, req): return Response(status=404)
        return Response(list(LedgerEntry.objects.filter(request=req).values("category", "delta", "entry_type", "year", "created_at")))

class PrintView(ELMView):
    permission_classes = [MODULE, HasPermission(P_VIEW)]
    @extend_schema(responses={
        (200, "text/html"): OpenApiResponse(response=OpenApiTypes.STR, description="Printable HTML leave application"),
        (200, "text/csv"): OpenApiResponse(response=OpenApiTypes.STR, description="Exported leave application row"),
    })
    def get(self, request, pk):
        req = LeaveRequest.objects.filter(pk=pk).first()
        if not req or not self.can_view_request(request, req):
            return Response(status=404)
        if request.query_params.get("format") == "csv":
            response = HttpResponse(content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = f'attachment; filename="elm-leave-{req.pk}.csv"'
            writer = csv.writer(response)
            writer.writerow(["request_id", "employee_id", "category", "start_date", "end_date", "days", "status", "purpose"])
            writer.writerow([req.pk, req.user_id, req.category, req.start_date, req.end_date, req.days, req.status, req.purpose])
            return response
        # Printable plain HTML is intentionally self-contained and escaped by Django.
        from django.utils.html import escape
        html = f"<!doctype html><meta charset='utf-8'><title>Leave application #{req.pk}</title><h1>Employee Leave Application</h1><dl><dt>Request</dt><dd>{req.pk}</dd><dt>Employee ID</dt><dd>{req.user_id}</dd><dt>Category</dt><dd>{escape(req.category)}</dd><dt>Dates</dt><dd>{req.start_date} – {req.end_date}</dd><dt>Days</dt><dd>{req.days}</dd><dt>Status</dt><dd>{escape(req.status)}</dd><dt>Purpose</dt><dd>{escape(req.purpose)}</dd></dl>"
        return HttpResponse(html, content_type="text/html; charset=utf-8")

class PolicyView(ELMView):
    permission_classes = [MODULE, HasPermission(P_POLICY)]
    @extend_schema(responses=s.PolicyConfigSerializer)
    def get(self, request):
        policy = ledger.current_policy()
        return Response({"params": policy.params, "hierarchy": policy.hierarchy, "updated_at": policy.updated_at})
    @extend_schema(request=s.PolicyConfigWriteSerializer, responses=s.PolicyConfigSerializer)
    @transaction.atomic
    def post(self, request):
        policy = ledger.current_policy()
        policy = LeavePolicy.objects.select_for_update().get(pk=policy.pk)
        params = request.data.get("params", policy.params)
        hierarchy = request.data.get("hierarchy", policy.hierarchy)
        try:
            validate_params(params)
            validate_hierarchy(hierarchy)
        except PolicyViolation as exc:
            return self.error(exc)
        policy.params, policy.hierarchy, policy.updated_by_user_id = params, hierarchy, self.actor(request).user_id
        policy.save(update_fields=["params", "hierarchy", "updated_by_user_id", "updated_at"])
        return Response({"params": policy.params, "hierarchy": policy.hierarchy})

class CalendarListView(ELMView):
    permission_classes = [MODULE, HasPermission(P_CALENDAR)]
    @extend_schema(responses=s.CalendarSerializer(many=True))
    def get(self, request):
        return Response(s.CalendarSerializer(CalendarVersion.objects.all(), many=True).data)
    @extend_schema(request=s.CalendarSerializer, responses={201: s.CalendarSerializer})
    @transaction.atomic
    def post(self, request):
        payload = s.CalendarSerializer(data=request.data); payload.is_valid(raise_exception=True)
        entries = payload.validated_data.pop("entries", [])
        cal = CalendarVersion.objects.create(**payload.validated_data)
        for entry in entries: CalendarEntry.objects.create(calendar=cal, **entry)
        return Response(s.CalendarSerializer(cal).data, status=201)


class CalendarDetailView(ELMView):
    permission_classes = [MODULE, HasPermission(P_CALENDAR)]
    @extend_schema(request=s.CalendarSerializer, responses=s.CalendarSerializer)
    @transaction.atomic
    def patch(self, request, pk):
        cal = CalendarVersion.objects.select_for_update().filter(pk=pk).first()
        if not cal: return Response(status=404)
        if cal.status == "published": return Response({"error": {"code": "published_calendar_immutable", "message": "Published calendars are immutable; create a replacement calendar."}}, status=409)
        payload = s.CalendarSerializer(cal, data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        entries = payload.validated_data.pop("entries", None)
        for key, value in payload.validated_data.items(): setattr(cal, key, value)
        cal.save()
        if entries is not None:
            cal.entries.all().delete()
            for entry in entries: CalendarEntry.objects.create(calendar=cal, **entry)
        return Response(s.CalendarSerializer(cal).data)

class CalendarPublishView(ELMView):
    permission_classes = [MODULE, HasPermission(P_CALENDAR)]
    @extend_schema(responses=s.CalendarSerializer)
    @transaction.atomic
    def post(self, request, pk):
        cal = CalendarVersion.objects.select_for_update().filter(pk=pk).first()
        if not cal: return Response(status=404)
        if cal.status == "published": return Response({"error": {"code": "published_calendar_immutable", "message": "Published calendars are immutable; create a replacement calendar."}}, status=409)
        if not cal.entries.exists(): return Response({"error": {"code": "calendar_empty", "message": "Add at least one calendar entry before publishing."}}, status=400)
        cal.status, cal.published_at, cal.published_by_user_id = "published", timezone.now(), self.actor(request).user_id
        cal.save(update_fields=["status", "published_at", "published_by_user_id", "updated_at"])
        return Response(s.CalendarSerializer(cal).data)

class OfflineView(ELMView):
    permission_classes = [MODULE, HasPermission(P_OFFLINE)]
    @extend_schema(responses=s.OfflineRecordOutputSerializer(many=True))
    def get(self, request): return Response(list(OfflineLeaveRecord.objects.order_by("-created_at").values()[:200]))
    @extend_schema(request=s.OfflineRecordSerializer, responses={201: s.OfflineRecordCreateResponseSerializer})
    def post(self, request):
        payload = s.OfflineRecordSerializer(data=request.data); payload.is_valid(raise_exception=True)
        try: row = offline.record(recorded_by_user_id=self.actor(request).user_id, **payload.validated_data)
        except (IamUnavailable, PolicyViolation, ValueError) as exc: return self.error(exc)
        return Response({"id": row.pk, "synced_request_id": row.synced_request_id}, status=201)

class OfflineRecordDetailView(ELMView):
    permission_classes = [MODULE, HasPermission(P_OFFLINE)]
    @extend_schema(request=s.OfflineRecordMaintenanceSerializer, responses=s.OfflineRecordMaintenanceOutputSerializer)
    def patch(self, request, pk):
        payload = s.OfflineRecordMaintenanceSerializer(data=request.data); payload.is_valid(raise_exception=True)
        try:
            row = records.maintain_offline_record(record_id=pk, actor_user_id=self.actor(request).user_id, actor_role=self.actor(request).active_role or "", **payload.validated_data)
        except (OfflineLeaveRecord.DoesNotExist, PolicyViolation) as exc:
            return self.error(exc)
        return Response({"id": row.pk, "user_id": row.user_id, "category": row.category, "start_date": row.start_date, "end_date": row.end_date, "sanction_reference": row.sanction_reference, "evidence": row.evidence, "note": row.note})

class SlaConfigView(ELMView):
    permission_classes = [MODULE, HasPermission(P_POLICY)]
    @extend_schema(responses=s.SlaConfigSerializer)
    def get(self, request):
        policy = ledger.current_policy()
        return Response((policy.params or {}).get("sla", {}))
    @extend_schema(request=s.SlaConfigSerializer, responses=s.SlaConfigSerializer)
    @transaction.atomic
    def post(self, request):
        payload = s.SlaConfigSerializer(data=request.data); payload.is_valid(raise_exception=True)
        data = payload.validated_data
        reminder = data.get("reminder_hours")
        escalation = data.get("escalation_hours")
        if reminder is not None and escalation is not None and escalation < reminder:
            return Response({"error": {"code": "invalid_sla_thresholds", "message": "Escalation threshold must not be earlier than reminder threshold."}}, status=400)
        if escalation is not None and not data.get("escalation_role", "").strip():
            return Response({"error": {"code": "invalid_sla_target", "message": "Escalation target designation is required when escalation is enabled."}}, status=400)
        policy = ledger.current_policy()
        policy = LeavePolicy.objects.select_for_update().get(pk=policy.pk)
        params = dict(policy.params or {})
        params["sla"] = {"reminder_hours": reminder, "escalation_hours": escalation, "escalation_role": data.get("escalation_role", "")}
        try:
            validate_params(params)
        except PolicyViolation as exc:
            return self.error(exc)
        policy.params = params; policy.updated_by_user_id = self.actor(request).user_id
        policy.save(update_fields=["params", "updated_by_user_id", "updated_at"])
        return Response(params["sla"])

class NotificationView(ELMView):
    permission_classes = [MODULE]
    @extend_schema(responses=s.NotificationSerializer(many=True))
    def get(self, request):
        p = self.actor(request)
        qs = Notification.objects.filter(recipient_user_id=p.user_id) | Notification.objects.filter(recipient_role__in=self.roles(request))
        return Response(s.NotificationSerializer(qs.order_by("-created_at")[:100], many=True).data)

class ResumptionQueueView(ELMView):
    permission_classes = [MODULE, HasPermission(P_RESUME_REVIEW)]
    @extend_schema(responses=s.LeaveRequestSerializer(many=True))
    def get(self, request): return Response(s.LeaveRequestSerializer(LeaveRequest.objects.filter(status="resumption_pending", current_role__in=self.roles(request))[:200], many=True).data)

class ResumptionVerifyView(ELMView):
    permission_classes = [MODULE, HasPermission(P_RESUME_REVIEW)]
    @extend_schema(request=s.NoteSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk):
        note = request.data.get("note", "")
        try: req = resumption.verify(request_id=pk, actor_user_id=self.actor(request).user_id, actor_roles=self.roles(request), note=note)
        except (LeaveRequest.DoesNotExist, PolicyViolation) as exc: return self.error(exc)
        return Response(s.LeaveRequestSerializer(req).data)
