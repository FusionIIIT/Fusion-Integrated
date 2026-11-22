"""HTTP layer: parse, scope, delegate, serialise. Two gates on every endpoint."""
from __future__ import annotations

from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api import csv as csv_export
from core.api.exceptions import BadRequestError, NotFoundError
from core.api.pagination import CursorPagination
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.iaa.api import serializers as s
from modules.iaa.domain import state_machine as sm
from modules.iaa.models import BudgetEntry, FinancialYear, PolicyVersion
from modules.iaa.selectors import notifications as notification_selectors
from modules.iaa.selectors import records as record_selectors
from modules.iaa.selectors import scoping
from modules.iaa.services import anomalies as anomaly_service
from modules.iaa.services import configuration as config_service
from modules.iaa.services import decisions as decision_service
from modules.iaa.services import observations as observation_service
from modules.iaa.services import processing as processing_service
from modules.iaa.services import records as record_service
from modules.iaa.services import reports as report_service
from modules.iaa.services import review as review_service

MODULE = HasModuleGrant("iaa")

P_VIEW = "iaa.request.view"
P_CREATE = "iaa.request.create"
P_RESPOND = "iaa.clarification.update"
P_REVIEW = "iaa.request.review"
P_APPROVE = "iaa.request.approve"
P_PROCESS = "iaa.processing.create"
P_ANOMALY_VIEW = "iaa.anomaly.view"
P_ANOMALY_CREATE = "iaa.anomaly.create"
P_ANOMALY_REVIEW = "iaa.anomaly.review"
P_OBS_VIEW = "iaa.observation.view"
P_OBS_CREATE = "iaa.observation.create"
P_OBS_RESPOND = "iaa.observation.update"
P_OBS_REVIEW = "iaa.observation.review"
P_REPORT = "iaa.report.view"
P_EXPORT = "iaa.report.export"
P_NOTIFY = "iaa.notification.view"
P_CONFIG_VIEW = "iaa.configuration.view"
P_CONFIG = "iaa.configuration.update"

QUEUES = ("finance_review", "to_record", "pending_approval")


def _actor(request):
    return getattr(request, "principal", None)


def _int_param(params, name):
    raw = params.get(name)
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise BadRequestError(f"{name} must be a number.", code="invalid_filter") from exc


def _choice_param(params, name, choices):
    raw = params.get(name)
    if raw in (None, ""):
        return None
    if raw not in choices:
        raise BadRequestError(f"{name} must be one of: {', '.join(choices)}.",
                              code="invalid_filter")
    return raw


def _valid(serializer_cls, data):
    ser = serializer_cls(data=data)
    ser.is_valid(raise_exception=True)
    return ser.validated_data


def _paged(view, request, qs, serializer_cls):
    paginator = CursorPagination()
    page = paginator.paginate_queryset(qs, request, view=view)
    return paginator.get_paginated_response(serializer_cls(page, many=True).data)


def _detail(actor, pk):
    record = record_selectors.visible_record(actor, pk)
    if record is None:
        raise NotFoundError("That request or claim does not exist, or is not visible to you.")
    return Response(s.RecordDetailSerializer(record).data)


class _ByMethod(APIView):
    """Module grant first, then the permission that this HTTP method needs."""

    read: tuple[str, ...] = ()
    write: tuple[str, ...] = ()

    def get_permissions(self):
        codes = self.read if self.request.method in ("GET", "HEAD", "OPTIONS") else self.write
        return [MODULE(), HasPermission(*codes)()]


def _example(name, value):
    return OpenApiExample(name, value=value)


RECORD_EXAMPLE = _example("record", {
    "id": 12, "kind": "expense", "status": "submitted", "user_id": 41, "department": "CSE",
    "request_type": "voucher", "title": "Lab consumables", "description": "Soldering kits",
    "amount": "12500.00", "financial_year": "2026-27"})


class RecordListView(_ByMethod):
    read, write = (P_VIEW,), (P_CREATE,)

    @extend_schema(responses=s.RecordSerializer(many=True), examples=[RECORD_EXAMPLE])
    def get(self, request):
        actor = _actor(request)
        qs = scoping.records_for(actor)
        params = request.query_params
        kind = _choice_param(params, "kind", sm.KINDS)
        state = _choice_param(params, "status", sm.RECORD_STATES)
        queue = _choice_param(params, "queue", QUEUES)
        if kind:
            qs = qs.filter(kind=kind)
        if state:
            qs = qs.filter(status=state)
        if queue == "finance_review":
            qs = qs.filter(status__in=[sm.SUBMITTED, sm.QUERY_RESPONDED, sm.QUERY_RAISED])
        elif queue == "to_record":
            qs = qs.filter(status__in=[sm.APPROVED, sm.VERIFIED])
        elif queue == "pending_approval":
            qs = qs.filter(pk__in=scoping.pending_steps_for(actor).values("record_id"))
        return _paged(self, request, qs, s.RecordSerializer)

    @extend_schema(request=s.CreateRecordSerializer, responses={201: s.RecordSerializer},
                   examples=[_example("expense draft", {"kind": "expense", "title": "Lab kits",
                                                        "department": "CSE"}), RECORD_EXAMPLE])
    def post(self, request):
        data = _valid(s.CreateRecordSerializer, request.data)
        actor = _actor(request)
        if data["kind"] == sm.TA:
            record = record_service.create_ta(
                actor, department=data.get("department", ""), amount=data.get("amount"),
                purpose=data.get("purpose", ""), trip_start=data.get("trip_start"),
                trip_end=data.get("trip_end"), documents=data.get("documents", []))
        else:
            record = record_service.create_expense(
                actor, department=data.get("department", ""),
                request_type=data.get("request_type", ""), title=data.get("title", ""),
                description=data.get("description", ""), amount=data.get("amount"))
        return Response(s.RecordSerializer(record).data, status=status.HTTP_201_CREATED)


class RecordDetailView(_ByMethod):
    read, write = (P_VIEW,), (P_CREATE,)

    @extend_schema(responses=s.RecordDetailSerializer, examples=[RECORD_EXAMPLE])
    def get(self, request, pk):
        return _detail(_actor(request), pk)

    @extend_schema(request=s.ExpenseDraftSerializer, responses=s.RecordDetailSerializer,
                   examples=[_example("edit draft", {"amount": "9800.00"}), RECORD_EXAMPLE])
    def patch(self, request, pk):
        data = _valid(s.ExpenseDraftSerializer, request.data)
        record_service.update_draft(_actor(request), pk, **data)
        return _detail(_actor(request), pk)


class RecordDocumentsView(_ByMethod):
    write = (P_CREATE, P_RESPOND)

    @extend_schema(request=s.DocumentInSerializer, responses={201: s.DocumentSerializer},
                   examples=[_example("document", {"title": "Bill",
                                                   "link": "https://drive.google.com/x"})])
    def post(self, request, pk):
        data = _valid(s.DocumentInSerializer, request.data)
        doc = record_service.add_document(_actor(request), pk, **data)
        return Response(s.DocumentSerializer(doc).data, status=status.HTTP_201_CREATED)


class RecordSubmitView(_ByMethod):
    write = (P_CREATE,)

    @extend_schema(request=None, responses=s.RecordDetailSerializer, examples=[RECORD_EXAMPLE])
    def post(self, request, pk):
        record_service.submit(_actor(request), pk)
        return _detail(_actor(request), pk)


class RecordQueryView(_ByMethod):
    write = (P_REVIEW,)

    @extend_schema(request=s.TextSerializer, responses=s.RecordDetailSerializer,
                   examples=[_example("question", {"text": "Attach the original bill."})])
    def post(self, request, pk):
        data = _valid(s.TextSerializer, request.data)
        review_service.raise_query(_actor(request), pk, question=data["text"])
        return _detail(_actor(request), pk)


class RecordQueryResponseView(_ByMethod):
    write = (P_RESPOND,)

    @extend_schema(request=s.TextSerializer, responses=s.RecordDetailSerializer,
                   examples=[_example("answer", {"text": "Bill attached."})])
    def post(self, request, pk):
        data = _valid(s.TextSerializer, request.data)
        record_service.respond_query(_actor(request), pk, response=data["text"])
        return _detail(_actor(request), pk)


class RecordValidateView(_ByMethod):
    write = (P_REVIEW,)

    @extend_schema(request=s.ValidateSerializer, responses=s.RecordDetailSerializer,
                   examples=[_example("verify", {"decision": "verify", "remarks": ""})])
    def post(self, request, pk):
        data = _valid(s.ValidateSerializer, request.data)
        review_service.validate(_actor(request), pk, decision=data["decision"],
                                remarks=data["remarks"])
        return _detail(_actor(request), pk)


class RecordDecisionView(_ByMethod):
    write = (P_APPROVE,)

    @extend_schema(request=s.DecisionSerializer, responses=s.RecordDetailSerializer,
                   examples=[_example("approve", {"decision": "approve",
                                                  "remarks": "Within budget."})])
    def post(self, request, pk):
        data = _valid(s.DecisionSerializer, request.data)
        decision_service.decide(_actor(request), pk, decision=data["decision"],
                                remarks=data["remarks"])
        return _detail(_actor(request), pk)


class RecordProcessingView(_ByMethod):
    write = (P_PROCESS,)

    @extend_schema(request=s.ProcessingSerializer, responses=s.RecordDetailSerializer,
                   examples=[_example("record", {"reference": "VCH/2026/118", "note": ""})])
    def post(self, request, pk):
        data = _valid(s.ProcessingSerializer, request.data)
        processing_service.record(_actor(request), pk, reference=data["reference"],
                                  note=data["note"])
        return _detail(_actor(request), pk)


class RecordHistoryView(_ByMethod):
    read = (P_VIEW,)

    @extend_schema(responses=s.TrailSerializer(many=True),
                   examples=[_example("trail", [{"action": "submit", "from_status": "draft",
                                                 "to_status": "submitted",
                                                 "actor_role": "faculty"}])])
    def get(self, request, pk):
        if not scoping.records_for(_actor(request)).filter(pk=pk).exists():
            raise NotFoundError("That request or claim does not exist, or is not visible to you.")
        return Response(s.TrailSerializer(record_selectors.trail("record", pk), many=True).data)


class AnomalyListView(_ByMethod):
    read, write = (P_ANOMALY_VIEW,), (P_ANOMALY_CREATE,)

    @extend_schema(responses=s.AnomalySerializer(many=True),
                   examples=[_example("anomaly", {"id": 3, "category": "budget",
                                                  "status": "open"})])
    def get(self, request):
        qs = scoping.anomalies_for(_actor(request))
        state = _choice_param(request.query_params, "status", sm.ANOMALY_STATES)
        if state:
            qs = qs.filter(status=state)
        return _paged(self, request, qs, s.AnomalySerializer)

    @extend_schema(request=s.FlagAnomalySerializer, responses={201: s.AnomalySerializer},
                   examples=[_example("flag", {"category": "policy", "record_id": 12,
                                               "description": "Split bills."})])
    def post(self, request):
        data = _valid(s.FlagAnomalySerializer, request.data)
        anomaly = anomaly_service.flag(_actor(request), category=data["category"],
                                       description=data["description"],
                                       record_id=data.get("record_id"))
        return Response(s.AnomalySerializer(anomaly).data, status=status.HTTP_201_CREATED)


class AnomalyActionView(_ByMethod):
    write = (P_ANOMALY_REVIEW,)

    @extend_schema(request=s.TextSerializer, responses=s.AnomalySerializer,
                   examples=[_example("resolve", {"text": "Budget re-allocated."})])
    def post(self, request, pk, action):
        data = _valid(s.TextSerializer, request.data)
        if action == "resolve":
            anomaly = anomaly_service.resolve(_actor(request), pk, resolution=data["text"])
        else:
            anomaly = anomaly_service.escalate(_actor(request), pk, remarks=data["text"])
        return Response(s.AnomalySerializer(anomaly).data)


class ObservationListView(_ByMethod):
    read, write = (P_OBS_VIEW,), (P_OBS_CREATE,)

    @extend_schema(responses=s.ObservationSerializer(many=True),
                   examples=[_example("observation", {"id": 5, "status": "open"})])
    def get(self, request):
        qs = scoping.observations_for(_actor(request)).prefetch_related("responses")
        state = _choice_param(request.query_params, "status", sm.OBSERVATION_STATES)
        if state:
            qs = qs.filter(status=state)
        return _paged(self, request, qs, s.ObservationSerializer)

    @extend_schema(request=s.RaiseObservationSerializer, responses={201: s.ObservationSerializer},
                   examples=[_example("raise", {"title": "Missing GST invoice",
                                                "detail": "…", "record_id": 12})])
    def post(self, request):
        data = _valid(s.RaiseObservationSerializer, request.data)
        obs = observation_service.raise_observation(
            _actor(request), title=data["title"], detail=data["detail"],
            record_id=data.get("record_id"), respondent_user_id=data.get("respondent_user_id"))
        return Response(s.ObservationSerializer(obs).data, status=status.HTTP_201_CREATED)


class ObservationRespondView(_ByMethod):
    write = (P_OBS_RESPOND,)

    @extend_schema(request=s.RespondObservationSerializer, responses=s.ObservationSerializer,
                   examples=[_example("respond", {"corrective_action": "Invoice obtained.",
                                                  "evidence_link": "https://drive.google.com/y"})])
    def post(self, request, pk):
        data = _valid(s.RespondObservationSerializer, request.data)
        obs = observation_service.respond(_actor(request), pk, **data)
        return Response(s.ObservationSerializer(obs).data)


class ObservationReviewView(_ByMethod):
    write = (P_OBS_REVIEW,)

    @extend_schema(request=s.ReviewObservationSerializer, responses=s.ObservationSerializer,
                   examples=[_example("close", {"verdict": "satisfactory", "remarks": ""})])
    def post(self, request, pk):
        data = _valid(s.ReviewObservationSerializer, request.data)
        obs = observation_service.review(_actor(request), pk, **data)
        return Response(s.ObservationSerializer(obs).data)


class ReportSummaryView(_ByMethod):
    read = (P_REPORT,)

    @extend_schema(responses=dict, examples=[_example("summary", {
        "records": [{"kind": "expense", "status": "submitted", "count": 4}],
        "approval_turnaround": [], "anomalies": [], "observations": []})])
    def get(self, request):
        year = _int_param(request.query_params, "financial_year_id")
        return Response(report_service.summary(_actor(request), financial_year_id=year))


class ReportExportView(_ByMethod):
    read = (P_EXPORT,)
    throttle_scope = "export"

    @extend_schema(responses={(200, "text/csv"): str},
                   examples=[_example("csv", "id,kind,status\n12,expense,recorded\n")])
    def get(self, request):
        rows = report_service.export_rows(_actor(request))
        header = next(rows)
        return csv_export.stream(filename="iaa-report.csv", header=header, rows=rows)


class NotificationsView(_ByMethod):
    read = (P_NOTIFY,)

    @extend_schema(responses=dict, examples=[_example("dashboard", {
        "pending": {"to_review": 2}, "notifications": [{"kind": "submitted",
                                                        "message": "…"}]})])
    def get(self, request):
        actor = _actor(request)
        return Response({
            "pending": notification_selectors.pending_actions(actor),
            "notifications": s.NotificationSerializer(
                notification_selectors.recent(actor), many=True).data,
        })


class PolicyView(_ByMethod):
    read, write = (P_CONFIG_VIEW,), (P_CONFIG,)

    @extend_schema(responses=s.PolicySerializer(many=True),
                   examples=[_example("versions", [{"id": 1, "approval_timeout_hours": 48}])])
    def get(self, request):
        return Response(s.PolicySerializer(PolicyVersion.objects.all()[:20], many=True).data)

    @extend_schema(request=s.PublishPolicySerializer, responses={201: s.PolicySerializer},
                   examples=[_example("policy", {
                       "approval_timeout_hours": 48, "ta_high_value_threshold": "25000",
                       "budget_check_required": True, "request_types": ["voucher"],
                       "required_documents": {"expense": 1, "ta": 1},
                       "routes": [{"kind": "expense", "levels": ["iaa_hod"],
                                   "escalation_designation": "iaa_dean"}],
                       "anomaly_resolvers": {"budget": ["iaa_finance_staff"]}})])
    def post(self, request):
        data = dict(_valid(s.PublishPolicySerializer, request.data))
        start = data.pop("effective_from", None)
        data["ta_high_value_threshold"] = str(data["ta_high_value_threshold"])
        version = config_service.publish_policy(_actor(request), data, effective_from=start)
        return Response(s.PolicySerializer(version).data, status=status.HTTP_201_CREATED)


class FinancialYearView(_ByMethod):
    read, write = (P_CONFIG_VIEW,), (P_CONFIG,)

    @extend_schema(responses=s.FinancialYearSerializer(many=True),
                   examples=[_example("years", [{"code": "2026-27", "starts_on": "2026-04-01",
                                                 "ends_on": "2027-03-31"}])])
    def get(self, request):
        return Response(s.FinancialYearSerializer(FinancialYear.objects.all(), many=True).data)

    @extend_schema(request=s.FinancialYearSerializer, responses={201: s.FinancialYearSerializer},
                   examples=[_example("year", {"code": "2026-27", "starts_on": "2026-04-01",
                                               "ends_on": "2027-03-31"})])
    def post(self, request):
        data = _valid(s.FinancialYearSerializer, request.data)
        year = config_service.add_financial_year(_actor(request), **data)
        return Response(s.FinancialYearSerializer(year).data, status=status.HTTP_201_CREATED)


class BudgetEntryView(_ByMethod):
    read, write = (P_CONFIG_VIEW,), (P_CONFIG,)

    @extend_schema(responses=s.BudgetEntrySerializer(many=True),
                   examples=[_example("ledger", [{"department": "CSE", "kind": "allocation",
                                                  "amount": "500000.00"}])])
    def get(self, request):
        qs = BudgetEntry.objects.select_related("financial_year")
        year = _int_param(request.query_params, "financial_year_id")
        if year is not None:
            qs = qs.filter(financial_year_id=year)
        return _paged(self, request, qs, s.BudgetEntrySerializer)

    @extend_schema(request=s.BudgetEntryInSerializer, responses={201: s.BudgetEntrySerializer},
                   examples=[_example("allocate", {"financial_year_id": 1, "department": "CSE",
                                                   "kind": "allocation", "amount": "500000"})])
    def post(self, request):
        data = _valid(s.BudgetEntryInSerializer, request.data)
        entry = config_service.add_budget_entry(_actor(request), **data)
        return Response(s.BudgetEntrySerializer(entry).data, status=status.HTTP_201_CREATED)


