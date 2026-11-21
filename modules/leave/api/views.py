"""HTTP layer: parse, scope, delegate, serialise. Rows come from selectors.scoping."""
from __future__ import annotations

from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.html import escape
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.directory import contracts as directory
from modules.leave.api import serializers as s
from modules.leave.domain.categories import LABELS, Category, EmployeeKind
from modules.leave.domain.counting import Half
from modules.leave.domain.workflow import Decision, State
from modules.leave.models import (
    AuthorityRule,
    HolidayCalendar,
    LeaveNotification,
    LeavePolicy,
    LeaveRequest,
    OrgUnit,
    SlaPolicy,
    VacationPeriod,
)
from modules.leave.selectors import accounts as reads
from modules.leave.selectors import calendar, scoping
from modules.leave.services import accounts, administration, resumptions, workflow
from modules.leave.services import requests as leave

MODULE = HasModuleGrant("leave_management")
P_CREATE = "leave_management.leave_request.create"
P_VIEW = "leave_management.leave_request.view"
P_REVIEW = "leave_management.leave_request.review"
P_EXPORT = "leave_management.leave_request.export"
P_POLICY = "leave_management.policy.manage"
P_CALENDAR = "leave_management.calendar.publish"
P_IMPORT = "leave_management.leave_record.import"
P_RECORDS = "leave_management.leave_record.update"
OBJ = OpenApiTypes.OBJECT


def _int(params, name, default=None):
    raw = params.get(name)
    if raw in (None, ""):
        return default
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise BadRequestError(f"{name} must be a number.", code="invalid_filter") from exc


def _valid(serializer_class, data):
    payload = serializer_class(data=data)
    payload.is_valid(raise_exception=True)
    return payload.validated_data


def _names(rows) -> dict[int, str]:
    users = directory.get_users({r.user_id for r in rows})
    return {uid: u.display_name for uid, u in users.items()}


def _out(req, detail=False):
    cls = s.LeaveRequestDetailSerializer if detail else s.LeaveRequestSerializer
    return cls(req, context={"names": _names([req])}).data


def _applicant(p):
    return leave.applicant_for(p.user_id, p.kind)


class _Gate(APIView):
    perms: tuple[str, ...] = ()

    def get_permissions(self):
        return [MODULE(), HasPermission(*self.perms)()]


# -- Request actions -------------------------------------------------------------
def _action(perm, body, handler, *, created=False, out=s.LeaveRequestSerializer):
    """One endpoint per action; the row must be in scope first, so foreign ids 404."""
    code = status.HTTP_201_CREATED if created else status.HTTP_200_OK

    @extend_schema(request=body, responses={code: out})
    class ActionView(_Gate):
        perms = (perm,)

        def post(self, request, pk):
            get_object_or_404(scoping.requests_for(request.principal), pk=pk)
            result = handler(request.principal, pk, _valid(body, request.data))
            data = _out(result) if out is s.LeaveRequestSerializer else out(result).data
            return Response(data, status=code)

    return ActionView


def _today():
    return timezone.localdate()


WithdrawView = _action(P_CREATE, s.NoteSerializer, lambda p, pk, d: leave.withdraw(
    pk, p.user_id, d["note"]))
CancelView = _action(P_CREATE, s.NoteSerializer, lambda p, pk, d: leave.request_cancellation(
    pk, p.user_id, d["note"], _today()), created=True)
ExtendView = _action(P_CREATE, s.ExtensionSerializer, lambda p, pk, d: leave.request_extension(
    _applicant(p), pk, d["new_end_date"], d["purpose"], _today(),
    d.get("substitute_user_id")), created=True)
RenominateView = _action(P_CREATE, s.RenominateSerializer, lambda p, pk, d: leave.renominate(
    pk, p.user_id, d["substitute_user_id"]))
ResumptionSubmitView = _action(
    P_CREATE, s.ResumptionSubmitSerializer, lambda p, pk, d: resumptions.submit(
        pk, p.user_id, d["actual_date"], d["remarks"], _today()),
    created=True, out=s.ResumptionSerializer)
SubstituteView = _action(P_REVIEW, s.SubstituteResponseSerializer,
                         lambda p, pk, d: leave.respond_as_substitute(
                             pk, p.user_id, d["accept"], d["note"]))
UnitHeadReviewView = _action(P_REVIEW, s.ReviewSerializer,
                             lambda p, pk, d: workflow.review_at_unit_head(
                                 pk, p.user_id, Decision(d["decision"]), d["note"]))
EstablishmentRouteView = _action(P_REVIEW, s.NoteSerializer,
                                 lambda p, pk, d: workflow.route_at_establishment(
                                     pk, p.user_id, d["note"]))
FinalDecisionView = _action(P_REVIEW, s.FinalDecisionSerializer,
                            lambda p, pk, d: workflow.final_decision(
                                pk, p.user_id, d["approve"], d["note"]))


# -- Employee reads and apply -------------------------------------------------------
@extend_schema(responses=OBJ)
class BalancesView(_Gate):
    perms = (P_CREATE,)

    def get(self, request):
        p = request.principal
        year = _int(request.query_params, "year", _today().year)
        if p.kind in (EmployeeKind.FACULTY, EmployeeKind.STAFF):
            with transaction.atomic():
                accounts.lock(p.user_id)
                accounts.ensure_annual_credits(p.user_id, EmployeeKind(p.kind), year)
        balance, held = reads.balances(p.user_id, year), reads.held(p.user_id, year)
        return Response({"year": year, "results": [
            {"category": c.value, "label": LABELS[c], "balance": balance[c],
             "held": held[c], "available": balance[c] - held[c]} for c in Category]})


class RequestListView(generics.ListAPIView):
    serializer_class = s.LeaveRequestSerializer

    def get_permissions(self):
        return [MODULE(), HasPermission(P_VIEW)()]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveRequest.objects.none()
        p, params = self.request.principal, self.request.query_params
        qs = scoping.own_requests(p) if params.get("mine") == "1" else scoping.requests_for(p)
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        if (uid := _int(params, "user_id")) is not None:
            qs = qs.filter(user_id=uid)
        return qs.select_related("resumption").order_by("-id")

    def get_serializer(self, *args, **kwargs):
        rows = args[0] if args else []
        kwargs["context"] = {**self.get_serializer_context(), "names": _names(rows)}
        return self.serializer_class(*args, **kwargs)


@extend_schema(request=s.LeaveApplySerializer, responses={201: s.LeaveRequestSerializer})
class ApplyView(_Gate):
    perms = (P_CREATE,)

    def post(self, request):
        d = _valid(s.LeaveApplySerializer, request.data)
        req = leave.apply(_applicant(request.principal), leave.Application(
            category=Category(d["category"]), start_date=d["start_date"],
            end_date=d["end_date"], half=Half(d["half"]), purpose=d["purpose"],
            substitute_user_id=d.get("substitute_user_id"), station_leave=d["station_leave"],
            station_address=d["station_address"],
            medical_evidence_ref=d["medical_evidence_ref"]))
        return Response(_out(req), status=status.HTTP_201_CREATED)


@extend_schema(responses=s.LeaveRequestDetailSerializer)
class RequestDetailView(_Gate):
    perms = (P_VIEW,)

    def get(self, request, pk):
        req = get_object_or_404(scoping.requests_for(request.principal)
                                .prefetch_related("transitions"), pk=pk)
        return Response(_out(req, detail=True))


@extend_schema(responses={(200, "text/html"): OpenApiTypes.STR})
class PrintView(_Gate):
    """EL-UC-013: a printable page of one's own application."""

    perms = (P_EXPORT,)

    def get(self, request, pk):
        req = get_object_or_404(scoping.own_requests(request.principal), pk=pk)
        rows = [("Request", f"#{req.pk} ({req.kind})"),
                ("Applicant", request.principal.display_name),
                ("Category", LABELS[Category(req.category)]),
                ("Period", f"{req.start_date} to {req.end_date} ({req.half})"),
                ("Days", req.days), ("Purpose", req.purpose),
                ("Station leave", req.station_address if req.station_leave else "No"),
                ("Status", req.status.replace("_", " ")),
                ("Recommendation", req.recommendation or "—")]
        body = "".join(f"<tr><th>{escape(k)}</th><td>{escape(str(v))}</td></tr>"
                       for k, v in rows)
        return HttpResponse(
            f"<!doctype html><title>Leave application #{req.pk}</title><h2>IIITDM "
            f"Jabalpur — Leave Application</h2><table border=1 cellpadding=6>{body}</table>"
            "<script>window.print()</script>", content_type="text/html")


@extend_schema(responses=OBJ)
class TasksView(_Gate):
    perms = (P_REVIEW,)

    def get(self, request):
        rows = list(scoping.inbox_for(request.principal)[:200])
        pending = list(scoping.resumptions_for_review(request.principal)[:200])
        ctx = {"names": _names(rows + [r.leave for r in pending])}
        return Response({
            "requests": s.LeaveRequestSerializer(rows, many=True, context=ctx).data,
            "resumptions": s.ResumptionSerializer(pending, many=True, context=ctx).data})


@extend_schema(request=None, responses=s.ResumptionSerializer)
class ResumptionReviewView(_Gate):
    perms = (P_REVIEW,)

    def post(self, request, pk):
        get_object_or_404(scoping.resumptions_for_review(request.principal), pk=pk)
        return Response(s.ResumptionSerializer(
            resumptions.review(pk, request.principal.user_id)).data)


@extend_schema(responses=OBJ)
class NotificationsView(_Gate):
    perms = (P_VIEW,)

    def get(self, request):
        rows = LeaveNotification.objects.filter(
            user_id=request.principal.user_id).order_by("-id")[:50]
        return Response({"results": s.NotificationSerializer(rows, many=True).data})


@extend_schema(responses=OBJ)
class EmployeesView(_Gate):
    perms = (P_CREATE, P_RECORDS)

    def get(self, request):
        q = request.query_params.get("q", "")[:60]
        rows = [u for kind in ("faculty", "staff") for u in directory.search(q, kind, 15)]
        return Response({"results": [
            {"user_id": u.user_id, "display_name": u.display_name, "kind": u.kind,
             "department": u.department}
            for u in rows if u.user_id != request.principal.user_id]})


@extend_schema(responses=s.CalendarSerializer)
class CurrentCalendarView(_Gate):
    perms = (P_VIEW,)

    def get(self, request):
        cal = calendar.published(_int(request.query_params, "year", _today().year))
        return Response(s.CalendarSerializer(cal).data if cal else None)


# -- Administration ---------------------------------------------------------------
def _config(perm, rows, read, write, save, method="post"):
    """List-and-save for one piece of configuration; `save` returns the saved row."""

    @extend_schema(request=write, responses=read)
    class ConfigView(_Gate):
        perms = (perm,)

        def get(self, request):
            return Response({"results": read(rows(), many=True).data})

        def _save(self, request):
            row = save(request.principal.user_id, _valid(write, request.data))
            code = status.HTTP_201_CREATED if method == "post" else status.HTTP_200_OK
            return Response(read(row).data, status=code)

    setattr(ConfigView, method, ConfigView._save)
    return ConfigView


PoliciesView = _config(
    P_POLICY, lambda: LeavePolicy.objects.order_by("category"), s.PolicySerializer,
    s.PolicySerializer, lambda by, d: administration.set_policy(
        Category(d["category"]), d["annual_days"], d.get("requires_substitute", False),
        d.get("max_days_per_request"), by), method="put")
UnitsView = _config(
    P_POLICY, lambda: OrgUnit.objects.select_related("parent").order_by("name"),
    s.UnitSerializer, s.UnitWriteSerializer, lambda by, d: administration.save_unit(
        d["name"], d["head_user_id"], d["parent_name"]))
AuthorityRulesView = _config(
    P_POLICY, lambda: AuthorityRule.objects.select_related("unit").order_by("category", "id"),
    s.AuthorityRuleSerializer, s.AuthorityRuleWriteSerializer,
    lambda by, d: administration.save_authority_rule(
        Category(d["category"]), d["unit_name"], d["applicant_kind"],
        d["sanctioning_user_id"], d.get("establishment_user_id")))
SlaView = _config(
    P_POLICY, SlaPolicy.objects.all, s.SlaSerializer, s.SlaSerializer,
    lambda by, d: administration.set_sla(State(d["state"]), d["reminder_hours"],
                                         d["escalation_hours"], d.get("escalate_to_user_id")),
    method="put")
CalendarsView = _config(
    P_CALENDAR, lambda: HolidayCalendar.objects.prefetch_related("holidays")
    .order_by("-year", "-id")[:20], s.CalendarSerializer, s.CalendarWriteSerializer,
    lambda by, d: administration.create_calendar(d["year"], d["title"], d["holidays"], by))
VacationsView = _config(
    P_CALENDAR, lambda: VacationPeriod.objects.order_by("-start_date"), s.VacationSerializer,
    s.VacationSerializer, lambda by, d: administration.add_vacation_period(
        d["name"], d["start_date"], d["end_date"]))


@extend_schema(request=s.DirectorSerializer, responses=OBJ)
class DirectorView(_Gate):
    perms = (P_POLICY,)

    def put(self, request):
        uid = _valid(s.DirectorSerializer, request.data)["user_id"]
        return Response({"user_id": administration.set_director(uid).user_id})


@extend_schema(request=None, responses=s.CalendarSerializer)
class CalendarPublishView(_Gate):
    perms = (P_CALENDAR,)

    def post(self, request, pk):
        return Response(s.CalendarSerializer(
            administration.publish_calendar(pk, request.principal.user_id)).data)


@extend_schema(request=s.OfflineRecordSerializer, responses={201: s.LeaveRequestSerializer})
class OfflineRecordView(_Gate):
    perms = (P_IMPORT,)

    def post(self, request):
        d = _valid(s.OfflineRecordSerializer, request.data)
        req = administration.record_offline(
            request.principal.user_id, d["user_id"], Category(d["category"]),
            d["start_date"], d["end_date"], Half(d["half"]), d["purpose"], d["reference"])
        return Response(_out(req), status=status.HTTP_201_CREATED)


@extend_schema(request=s.CorrectionSerializer, responses={201: OBJ})
class CorrectionView(_Gate):
    perms = (P_RECORDS,)

    def post(self, request):
        d = _valid(s.CorrectionSerializer, request.data)
        administration.correct_balance(request.principal.user_id, d["user_id"],
                                       Category(d["category"]), d["year"], d["days"],
                                       d["note"])
        return Response({"balances": reads.balances(d["user_id"], d["year"])},
                        status=status.HTTP_201_CREATED)


@extend_schema(responses=OBJ)
class EmployeeBalancesView(_Gate):
    perms = (P_RECORDS,)

    def get(self, request, user_id):
        year = _int(request.query_params, "year", _today().year)
        return Response({"year": year, "balances": reads.balances(user_id, year)})
