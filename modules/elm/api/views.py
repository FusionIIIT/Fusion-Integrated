"""ELM endpoints. A view turns HTTP into one service call; the rules live in services/.

Permissions only open the door. Who may act on a given request is decided by the
open workflow task (services/applications.py), so a Unit Head cannot decide a
request that was never routed to them.
"""
from datetime import date

from django.db import transaction
from django.db.models import Max
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework.renderers import JSONRenderer, StaticHTMLRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from fusion_auth.permissions import HasPermission
from modules.elm.api import serializers as sz
from modules.elm.models import (
    CalendarDay,
    HierarchyRule,
    HolidayCalendar,
    LeaveAccount,
    LeavePolicy,
    LeaveRequest,
    LeaveTransaction,
    WorkflowTask,
)
from modules.elm.services import (
    accounts,
    applications,
    lifecycle,
    offline,
    policy,
    routing,
    validation,
    workflow,
)

APPLY = "elm.request.create"
VIEW_OWN = "elm.request.view_self"
VIEW_ACCOUNT = "elm.account.view_self"
TASKS = "elm.task.view"
# One inbox permission opens the task endpoints; the open task decides who may act.
SUBSTITUTE = REVIEW = VERIFY = TASKS
ADMIN = "elm.policy.manage"
HIERARCHY = "elm.hierarchy.manage"
CALENDAR = "elm.calendar.manage"
OFFLINE = "elm.offline.record"

_BAD = (applications.ApplicationError, validation.LeaveValidationError,
        policy.PolicyError, routing.RoutingError, accounts.AccountError)


def call(fn, *args, **kwargs):
    """Run a service and translate its exceptions into the platform's error envelope."""
    try:
        return fn(*args, **kwargs)
    except LeaveRequest.DoesNotExist as exc:
        raise NotFoundError("Leave request not found.") from exc
    except workflow.TransitionError as exc:
        raise ConflictError(str(exc), code="invalid_state") from exc
    except _BAD as exc:
        raise BadRequestError(str(exc), code=type(exc).__name__.lower()) from exc


def _mine(pk: int, actor: int) -> LeaveRequest:
    """The applicant's own request, or 404 (never reveal that someone else's exists)."""
    req = LeaveRequest.objects.filter(pk=pk, applicant_id=actor).first()
    if req is None:
        raise NotFoundError("Leave request not found.")
    return req


def _out(req) -> dict:
    return sz.RequestOutSerializer(req).data


# -- one POST per action -----------------------------------------------------

def _submit(actor, pk, d):
    req = LeaveRequest.objects.filter(pk=pk, applicant_id=actor).first()
    if req is None:
        raise NotFoundError("Leave request not found.")
    return applications.submit(pk, d.get("nominee_id"))


def _modify(actor, pk, d):
    changes = dict(d)
    nominee = changes.pop("nominee_id", None)
    return lifecycle.modify(pk, actor, nominee_id=nominee, **changes)


def _extend(actor, pk, d):
    return lifecycle.extend(pk, actor, d["new_end"], d.get("nominee_id"),
                            d.get("substitute_required", False))


_ACTIONS = {
    # name: (permission, serializer, handler(actor, pk, data), partial)
    "submit": (APPLY, sz.SubmitSerializer, _submit, False),
    "modify": (APPLY, sz.ModifySerializer, _modify, True),
    "withdraw": (APPLY, sz.EmptySerializer,
                 lambda a, pk, d: applications.withdraw(pk, a), False),
    "cancel": (APPLY, sz.EmptySerializer,
               lambda a, pk, d: lifecycle.request_cancellation(pk, a), False),
    "extend": (APPLY, sz.ExtendSerializer, _extend, False),
    "nominate": (APPLY, sz.NominateSerializer,
                 lambda a, pk, d: applications.nominate_substitute(pk, a, d["nominee_id"]),
                 False),
    "resume": (APPLY, sz.ResumeSerializer,
               lambda a, pk, d: lifecycle.submit_resumption(
                   pk, a, d["actual_date"], d.get("details", "")), False),
    "substitute": (SUBSTITUTE, sz.SubstituteResponseSerializer,
                   lambda a, pk, d: applications.respond_substitute(pk, a, d["accept"]), False),
    "unit-head": (REVIEW, sz.UnitHeadSerializer,
                  lambda a, pk, d: applications.unit_head_decide(
                      pk, a, d["outcome"], d.get("remarks", "")), False),
    "establishment": (REVIEW, sz.RemarksSerializer,
                      lambda a, pk, d: applications.establishment_route(
                          pk, a, d.get("remarks", "")), False),
    "final": (REVIEW, sz.FinalSerializer,
              lambda a, pk, d: applications.final_decide(
                  pk, a, d["outcome"], d.get("remarks", "")), False),
    "verify": (VERIFY, sz.VerifySerializer,
               lambda a, pk, d: lifecycle.verify_resumption(pk, a, d.get("verified", True)),
               False),
}

_APPLICANT_ACTIONS = {"submit", "modify", "withdraw", "cancel", "extend", "nominate", "resume"}


def _action_view(name, permission, serializer, handler, partial):
    @extend_schema(request=serializer, responses=sz.RequestOutSerializer)
    class ActionView(APIView):
        permission_classes = [HasPermission(permission)]

        def post(self, request, pk):
            uid = request.principal.user_id
            if name in _APPLICANT_ACTIONS and not LeaveRequest.objects.filter(
                pk=pk, applicant_id=uid
            ).exists():
                raise NotFoundError("Leave request not found.")
            ser = serializer(data=request.data, partial=partial)
            ser.is_valid(raise_exception=True)
            req = call(handler, request.principal.user_id, pk, ser.validated_data)
            return Response(_out(req))

    ActionView.__name__ = "Elm" + name.title().replace("-", "") + "View"
    return ActionView


ACTION_VIEWS = {name: _action_view(name, *spec) for name, spec in _ACTIONS.items()}


# -- requests, tasks, balances ----------------------------------------------

class RequestsView(APIView):
    """GET: the caller's own requests. POST: create a draft."""

    def get_permissions(self):
        method = getattr(getattr(self, "request", None), "method", "GET")
        return [HasPermission(APPLY if method == "POST" else VIEW_OWN)()]

    @extend_schema(responses=sz.RequestOutSerializer(many=True))
    def get(self, request):
        qs = LeaveRequest.objects.filter(applicant_id=request.principal.user_id)
        status = request.query_params.get("status")
        if status:
            qs = qs.filter(status=status)
        return Response({"results": [_out(r) for r in qs.order_by("-id")[:200]]})

    @extend_schema(request=sz.DraftSerializer, responses=sz.RequestOutSerializer)
    def post(self, request):
        ser = sz.DraftSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = dict(ser.validated_data)
        req = call(applications.create_draft, request.principal.user_id,
                   d.pop("leave_type"), d.pop("start_date"), d.pop("end_date"),
                   d.pop("reason"), **d)
        return Response(_out(req), status=201)


class RequestDetailView(APIView):
    """Visible to the applicant and to anyone who holds a task on the request."""
    permission_classes = [HasPermission(VIEW_OWN, TASKS)]

    @extend_schema(responses=sz.RequestOutSerializer)
    def get(self, request, pk):
        uid = request.principal.user_id
        req = LeaveRequest.objects.filter(pk=pk).first()
        if req is None or not (
                req.applicant_id == uid
                or WorkflowTask.objects.filter(request=req, assignee_id=uid).exists()):
            raise NotFoundError("Leave request not found.")
        data = dict(_out(req))
        data["decisions"] = list(req.decisions.order_by("id").values(
            "actor_id", "outcome", "remarks", "created_at"))
        data["substitutes"] = list(req.substitutes.order_by("id").values(
            "nominee_id", "status", "responded_at"))
        data["tasks"] = list(req.tasks.order_by("id").values(
            "id", "stage", "assignee_id", "status"))
        return Response(data)


def render_printable_html(data: dict) -> str:
    app_info = data.get("application", {})
    applicant = data.get("applicant", {})
    decisions = data.get("decisions", [])
    substitutes = data.get("substitutes", [])
    dec_rows = "".join(
        f"<tr><td>User {d.get('actor_id')}</td><td>{str(d.get('outcome', '')).upper()}</td>"
        f"<td>{d.get('remarks', '-') or '-'}</td><td>{d.get('created_at', '')}</td></tr>"
        for d in decisions
    ) or "<tr><td colspan='4'>No decisions recorded yet.</td></tr>"
    sub_rows = "".join(
        f"<tr><td>User {s.get('nominee_id')}</td><td>{str(s.get('status', '')).upper()}</td></tr>"
        for s in substitutes
    ) or "<tr><td colspan='2'>No substitute required/assigned.</td></tr>"
    s_addr = app_info.get('station_address', '-')
    s_cont = app_info.get('station_contact', '-')
    station_info = (
        f"<p><strong>Station Leave Address:</strong> {s_addr}</p>"
        f"<p><strong>Contact:</strong> {s_cont}</p>"
        if app_info.get("outside_station") else "<p>Station Leave: Not Applicable</p>"
    )
    status_str = str(app_info.get('status', '')).upper()
    user_name = applicant.get('name', '')
    user_id = applicant.get('user_id', '')
    dept = applicant.get('department', '')
    kind_title = str(applicant.get('kind', '')).title()
    l_type = app_info.get('leave_type', '')
    days_val = app_info.get('days', '')
    s_date = app_info.get('start_date', '')
    e_date = app_info.get('end_date', '')
    h_mode = app_info.get('half', '') or 'Full Day'
    reason_val = app_info.get('reason', '')
    c_at = app_info.get('created_at', '')
    app_id = app_info.get('id', '')
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Leave Application #{app_id}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
       margin: 40px; color: #222; }}
h1 {{ font-size: 1.3rem; text-align: center; margin-bottom: 4px; }}
h2 {{ font-size: 1.05rem; text-align: center; color: #555; margin-top: 0; }}
.section {{ margin-top: 20px; border-bottom: 1px solid #ccc; padding-bottom: 10px; }}
.section h3 {{ font-size: 0.95rem; color: #111; margin-bottom: 6px; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 6px; }}
th, td {{ border: 1px solid #ddd; padding: 5px 8px; font-size: 0.85rem; text-align: left; }}
th {{ background-color: #f7f7f7; }}
.badge {{ display: inline-block; padding: 2px 6px; font-weight: bold; border-radius: 4px;
          font-size: 0.8rem; background: #eee; }}
.signatures {{ display: flex; justify-content: space-between; margin-top: 40px; }}
.sig-box {{ border-top: 1px solid #333; width: 28%; text-align: center; padding-top: 4px;
            font-size: 0.8rem; }}
@media print {{ .no-print {{ display: none; }} body {{ margin: 15mm; }} }}
</style>
</head>
<body>
<div class="no-print" style="margin-bottom: 12px; text-align: right;">
  <button onclick="window.print()" style="padding: 4px 10px; cursor: pointer;">Print</button>
</div>
<h1>PDPM Indian Institute of Information Technology, Design and Manufacturing Jabalpur</h1>
<h2>Employee Leave Application Form</h2>
<div class="section">
  <h3>Application Summary</h3>
  <p><strong>Application ID:</strong> #{app_id} &nbsp;|&nbsp;
     <strong>Status:</strong> <span class="badge">{status_str}</span> &nbsp;|&nbsp;
     <strong>Created:</strong> {c_at}</p>
</div>
<div class="section">
  <h3>Applicant Details</h3>
  <table>
    <tr><th>Employee Name</th><td>{user_name}</td><th>Employee ID</th><td>{user_id}</td></tr>
    <tr><th>Department</th><td>{dept}</td><th>Category</th><td>{kind_title}</td></tr>
  </table>
</div>
<div class="section">
  <h3>Leave Particulars</h3>
  <table>
    <tr><th>Leave Type</th><td>{l_type}</td><th>Chargeable Days</th><td>{days_val}</td></tr>
    <tr><th>Period</th><td colspan="3">From {s_date} to {e_date}</td></tr>
    <tr><th>Half-Day Mode</th><td colspan="3">{h_mode}</td></tr>
    <tr><th>Reason</th><td colspan="3">{reason_val}</td></tr>
  </table>
  {station_info}
</div>
<div class="section">
  <h3>Substitute Endorsement</h3>
  <table>
    <tr><th>Nominee</th><th>Consent Status</th></tr>
    {sub_rows}
  </table>
</div>
<div class="section">
  <h3>Review and Sanction Trail</h3>
  <table>
    <tr><th>Approver / Authority</th><th>Decision</th><th>Remarks</th><th>Timestamp</th></tr>
    {dec_rows}
  </table>
</div>
<div class="signatures">
  <div class="sig-box">Applicant Signature</div>
  <div class="sig-box">Unit Head Recommendation</div>
  <div class="sig-box">Sanctioning Authority</div>
</div>
</body>
</html>"""


class PrintView(APIView):
    """Printable / exportable representation (EL-UC-013). The applicant's own only."""
    permission_classes = [HasPermission(VIEW_OWN)]
    renderer_classes = [JSONRenderer, StaticHTMLRenderer]

    @extend_schema(responses=sz.RequestOutSerializer)
    def get(self, request, pk):
        req = _mine(pk, request.principal.user_id)
        who = call(applications._profile, req.applicant_id)
        data = {
            "application": _out(req),
            "applicant": {"user_id": who.user_id, "name": who.display_name,
                          "department": who.department, "kind": who.kind},
            "decisions": list(req.decisions.order_by("id").values(
                "actor_id", "outcome", "remarks", "created_at")),
            "substitutes": list(req.substitutes.order_by("id").values(
                "nominee_id", "status")),
        }
        fmt = request.query_params.get("format", "").lower()
        accept = request.META.get("HTTP_ACCEPT", "")
        if fmt == "html" or ("text/html" in accept and "application/json" not in accept):
            html = render_printable_html(data)
            return HttpResponse(html, content_type="text/html; charset=utf-8")
        return Response(data)


class TasksView(APIView):
    """Open tasks assigned to the caller: substitute responses, reviews, verifications."""
    permission_classes = [HasPermission(TASKS)]

    def get(self, request):
        qs = (WorkflowTask.objects
              .filter(assignee_id=request.principal.user_id, status=WorkflowTask.Status.OPEN)
              .select_related("request").order_by("id"))
        stage = request.query_params.get("stage")
        if stage:
            qs = qs.filter(stage=stage)
        return Response({"results": [
            {"task_id": t.pk, "stage": t.stage, "created_at": t.created_at,
             "request": _out(t.request)} for t in qs[:200]]})


class BalancesView(APIView):
    """Current balances and leave-account history (EL-UC-012)."""
    permission_classes = [HasPermission(VIEW_ACCOUNT)]

    def get(self, request):
        try:
            year = int(request.query_params.get("year", date.today().year))
        except ValueError as exc:
            raise BadRequestError("year must be a number.", code="invalid_filter") from exc
        accts = LeaveAccount.objects.filter(
            user_id=request.principal.user_id, year=year).order_by("leave_type")
        history = (LeaveTransaction.objects.filter(account__in=accts)
                   .select_related("account").order_by("-id")[:100])
        return Response({
            "year": year,
            "accounts": [{"leave_type": a.leave_type, "balance": a.balance} for a in accts],
            "history": [{"leave_type": t.account.leave_type, "kind": t.kind,
                         "amount": t.amount, "request_id": t.request_id,
                         "note": t.note, "created_at": t.created_at} for t in history],
        })


# -- administration ----------------------------------------------------------

class PolicyView(APIView):
    permission_classes = [HasPermission(ADMIN)]

    def get(self, request):
        pol = call(policy.get_effective_policy)
        return Response({"version": pol.version, "effective_from": pol.effective_from,
                         "params": pol.params})

    @extend_schema(request=sz.PolicySerializer)
    @transaction.atomic
    def post(self, request):
        ser = sz.PolicySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        version = (LeavePolicy.objects.aggregate(m=Max("version"))["m"] or 0) + 1
        pol = LeavePolicy.objects.create(
            version=version, params=d["params"], effective_from=d["effective_from"])
        if d["publish"]:
            call(policy.publish_policy, pol)   # a bad policy rolls everything back
        return Response({"version": pol.version, "status": pol.status}, status=201)


class CalendarView(APIView):
    permission_classes = [HasPermission(CALENDAR)]

    @extend_schema(request=sz.CalendarSerializer)
    @transaction.atomic
    def post(self, request):
        ser = sz.CalendarSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        version = (HolidayCalendar.objects.filter(year=d["year"])
                   .aggregate(m=Max("version"))["m"] or 0) + 1
        cal = HolidayCalendar.objects.create(year=d["year"], version=version)
        CalendarDay.objects.bulk_create(
            [CalendarDay(calendar=cal, **day) for day in d["days"]])
        if d["publish"]:
            call(policy.publish_calendar, cal)
        return Response({"year": cal.year, "version": cal.version, "status": cal.status},
                        status=201)


class HierarchyView(APIView):
    permission_classes = [HasPermission(HIERARCHY)]

    def get(self, request):
        rows = HierarchyRule.objects.filter(status="published").order_by("stage", "id")
        return Response({"results": list(rows.values(
            "id", "stage", "unit", "applicant_kind", "leave_type", "approver_id"))})

    @extend_schema(request=sz.HierarchySerializer)
    def post(self, request):
        ser = sz.HierarchySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        rule = HierarchyRule.objects.create(status="published", **ser.validated_data)
        return Response({"id": rule.pk}, status=201)


class OfflineView(APIView):
    permission_classes = [HasPermission(OFFLINE)]

    @extend_schema(request=sz.OfflineSerializer, responses=sz.RequestOutSerializer)
    def post(self, request):
        ser = sz.OfflineSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        req = call(offline.record_offline, request.principal.user_id, d["applicant_id"],
                   d["leave_type"], d["start_date"], d["end_date"], d["reference"],
                   d["sanctioned_by"], d["sanctioned_on"], half=d["half"],
                   reason=d["reason"])
        return Response(_out(req), status=201)
