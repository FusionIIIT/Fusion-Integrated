"""ELM HTTP layer: parse, scope, delegate, serialise.

Authorization is the platform's two gates —
``HasModuleGrant("elm")`` plus the ``elm.*``
permission for the action — and the office-holder
check (the *right* Unit Head, the *right*
Sanctioning Authority) lives in the services, so a
Celery task or a command path cannot skip it.
"""
from __future__ import annotations

from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiTypes,
    extend_schema,
)
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import ConflictError, NotFoundError
from core.api.pagination import CursorPagination
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api import serializers as s
from modules.elm.domain.leave_types import (
    AWAITING_DIRECTOR_SELF_SANCTION,
    AWAITING_ESTABLISHMENT_ROUTING,
    AWAITING_EXTENSION_UNIT_HEAD,
    AWAITING_FINAL_SANCTION_DECISION,
    AWAITING_UNIT_HEAD_REVIEW,
    CANCELLATION_PENDING_ESTABLISHMENT,
    CANCELLATION_PENDING_FINAL,
    CANCELLATION_PENDING_UNIT_HEAD,
    EXTENSION_PENDING_ESTABLISHMENT,
    EXTENSION_PENDING_FINAL,
)
from modules.elm.models import (
    LeaveRequest,
    LeaveTask,
    Resumption,
    SubstituteNomination,
)
from modules.elm.selectors import balances as balance_selectors
from modules.elm.selectors import queues
from modules.elm.selectors import requests as request_selectors
from modules.elm.services import (
    admin as admin_service,
)
from modules.elm.services import applications as application_service
from modules.elm.services import authz, lifecycle, workflow
from modules.elm.services import offline as offline_service
from modules.elm.services import sla as sla_service
from modules.elm.services import year_end as year_end_service

MODULE = HasModuleGrant("elm")

P_APPLY = "elm.leave.apply"
P_VIEW_SELF = "elm.leave.view_self"
P_WITHDRAW = "elm.leave.withdraw"
P_NOMINATE = "elm.leave.nominate"
P_CANCEL = "elm.leave.cancel"
P_EXTEND = "elm.leave.extend"
P_RESUME = "elm.leave.resume"
P_SUBSTITUTE = "elm.substitute.respond"
P_REVIEW_UNIT_HEAD = "elm.review.unit_head"
P_REVIEW_ESTABLISHMENT = "elm.review.establishment"
P_SANCTION = "elm.sanction.final"
P_RESUME_REVIEW = "elm.resume.review"
P_RECORDS_VIEW = "elm.records.view"
P_RECORDS_OFFLINE = "elm.records.offline"
P_RECORDS_MAINTAIN = "elm.records.maintain"
P_CONFIG_POLICY = "elm.config.policy"
P_CONFIG_HIERARCHY = "elm.config.hierarchy"
P_CONFIG_CALENDAR = "elm.config.calendar"
P_CONFIG_UNITS = "elm.config.units"
P_CONFIG_VACATION = "elm.config.vacation"
P_CONFIG_SLA = "elm.config.sla"
P_YEAREND = "elm.yearend.run"

#: Any of the three decision seats may answer a
#: decision endpoint; the service then checks the
#: caller is the *right* office-holder.
P_DECIDE_ANY = (P_REVIEW_UNIT_HEAD,
                P_REVIEW_ESTABLISHMENT, P_SANCTION)

UNIT_HEAD_STATES = frozenset({
    AWAITING_UNIT_HEAD_REVIEW,
    CANCELLATION_PENDING_UNIT_HEAD,
    AWAITING_EXTENSION_UNIT_HEAD,
})
ESTABLISHMENT_STATES = frozenset({
    AWAITING_ESTABLISHMENT_ROUTING,
    CANCELLATION_PENDING_ESTABLISHMENT,
    EXTENSION_PENDING_ESTABLISHMENT,
})
FINAL_STATES = frozenset({
    AWAITING_FINAL_SANCTION_DECISION,
    CANCELLATION_PENDING_FINAL,
    EXTENSION_PENDING_FINAL,
    AWAITING_DIRECTOR_SELF_SANCTION,
})


def _actor(request):
    return getattr(request, "principal", None)


def _own_request(request, pk) -> LeaveRequest:
    """One of the caller's own requests — or one they
    have a live task on. Anything else is a 404, so
    the existence of other people's requests never
    leaks."""
    principal = _actor(request)
    own = request_selectors.request_for_user(
        pk, principal.user_id)
    if own is not None:
        return own
    participant = request_selectors.request_for_participant(
        pk, principal.user_id)
    if participant is not None:
        return participant
    raise NotFoundError()


def _dispatch_decide(request_obj, principal, *,
                         outcome: str, reason: str):
    """Route a decision to the seat the request's
    current state belongs to."""
    if request_obj.status in UNIT_HEAD_STATES:
        return workflow.unit_head_decide(
            request_obj, principal, outcome=outcome,
            reason=reason)
    if request_obj.status in ESTABLISHMENT_STATES:
        if outcome != "forward":
            raise ConflictError(
                "Establishment processing routes the "
                "request; it does not decide it.",
                code="invalid_outcome")
        return workflow.establishment_forward(
            request_obj, principal, reason=reason)
    if request_obj.status in FINAL_STATES:
        return workflow.final_decide(
            request_obj, principal, outcome=outcome,
            reason=reason)
    raise ConflictError(
        "No decision is awaited on this request.",
        code="invalid_transition")


# -- employee self-service -------------------------------------------


class MeView(APIView):
    """The caller's ELM context: their projection,
    their unit, and whether they hold a Unit Head
    seat."""

    permission_classes = [MODULE,
                          HasPermission(P_VIEW_SELF)]

    @extend_schema(responses=s.ElmContextSerializer)
    def get(self, request):
        principal = _actor(request)
        profile = authz.employee_profile(
            principal.user_id)
        unit = authz.applicant_unit(
            principal.user_id)
        return Response({
            "user_id": principal.user_id,
            "username": principal.username,
            "display_name": principal.display_name,
            "employee_kind": (
                profile.employee_kind
                if profile else None),
            "designation_name": (
                profile.designation_name
                if profile else None),
            "unit": (
                {"code": unit.code,
                 "name": unit.name,
                 "unit_type": unit.unit_type}
                if unit else None),
            "is_unit_head": bool(
                unit and unit.head_user_id
                == principal.user_id),
        })


class BalanceListView(APIView):
    """My current balances, with pending
    reservations already netted out."""

    permission_classes = [MODULE,
                          HasPermission(P_VIEW_SELF)]

    @extend_schema(responses=s.BalanceDTOSerializer(many=True))
    def get(self, request):
        principal = _actor(request)
        from modules.elm.services import policy as policy_service

        leave_year = (
            request.query_params.get("leave_year")
            or policy_service.leave_year_for(
                timezone.now().date()))
        balances = (
            balance_selectors.balances_for(
                {principal.user_id},
                leave_year).get(
                    principal.user_id, []))
        return Response(
            [{"user_id": b.user_id,
              "leave_year": b.leave_year,
              "category": b.category,
              "opening_days": str(b.opening_days),
              "entitled_days": str(b.entitled_days),
              "used_days": str(b.used_days),
              "pending_days": str(b.pending_days),
              "available_days": str(
                  b.available_days)}
             for b in balances])


class ApplicationListView(
        generics.ListCreateAPIView):
    """My applications. Creating one drafts it;
    ``submit: true`` (the default) validates and
    submits in one call."""

    permission_classes = [MODULE]
    pagination_class = CursorPagination

    def get_permissions(self):
        if self.request.method == "POST":
            return [HasPermission(P_APPLY)()]
        # During schema generation there is no principal; assume the broader requirement.
        principal = _actor(self.request)
        if principal is None:
            return [HasPermission(P_APPLY, P_VIEW_SELF)()]
        return [HasPermission(P_VIEW_SELF)()]

    def get_queryset(self):
        principal = _actor(self.request)
        if principal is None:
            # Schema generation holds no principal.
            return LeaveRequest.objects.none()
        qs = (
            request_selectors.my_requests(
                principal.user_id))
        category = self.request.query_params.get(
            "category")
        status_filter = self.request.query_params.get(
            "status")
        if category:
            qs = qs.filter(category=category)
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def get_serializer_class(self):
        if self.request.method == "POST":
            return s.ApplicationWriteSerializer
        return s.LeaveRequestSerializer

    @extend_schema(request=s.ApplicationWriteSerializer,
                   responses={201: s.LeaveRequestSerializer})
    def create(self, request, *args, **kwargs):
        principal = _actor(request)
        payload = s.ApplicationWriteSerializer(
            data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)
        submit = data.pop("submit", True)
        application = application_service.create_draft(
            principal, **data)
        if submit:
            application = application_service.submit(
                application, principal)
        return Response(
            s.LeaveRequestSerializer(
                application).data,
            status=status.HTTP_201_CREATED)


class ApplicationDetailView(APIView):
    permission_classes = [MODULE,
                          HasPermission(P_VIEW_SELF)]

    @extend_schema(responses=s.LeaveRequestSerializer)
    def get(self, request, pk):
        return Response(
            s.LeaveRequestSerializer(
                _own_request(request, pk)).data)


class ApplicationSubmitView(APIView):
    """Submit a draft — with the substitute
    nomination when coverage is required."""

    permission_classes = [MODULE,
                          HasPermission(P_APPLY)]

    @extend_schema(request=s.SubmitSerializer,
                   responses=s.LeaveRequestSerializer)
    def post(self, request, pk):
        principal = _actor(request)
        application = _own_request(request, pk)
        payload = s.SubmitSerializer(
            data=request.data)
        payload.is_valid(raise_exception=True)
        application = application_service.submit(
            application, principal,
            **payload.validated_data)
        return Response(
            s.LeaveRequestSerializer(
                application).data)


class ApplicationWithdrawView(APIView):
    permission_classes = [MODULE,
                          HasPermission(P_WITHDRAW)]

    @extend_schema(request=s.WithdrawalSerializer,
                   responses=s.LeaveRequestSerializer)
    def post(self, request, pk):
        principal = _actor(request)
        application = _own_request(request, pk)
        payload = s.WithdrawalSerializer(
            data=request.data)
        payload.is_valid(raise_exception=True)
        application = workflow.withdraw(
            application, principal,
            **payload.validated_data)
        return Response(
            s.LeaveRequestSerializer(
                application).data)


class ApplicationSubstituteView(APIView):
    """Nominate (or replace) the substitute on a
    request awaiting one."""

    permission_classes = [MODULE,
                          HasPermission(P_NOMINATE)]

    @extend_schema(request=s.SubstituteSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk):
        principal = _actor(request)
        application = _own_request(request, pk)
        payload = s.SubstituteSerializer(
            data=request.data)
        payload.is_valid(raise_exception=True)
        from modules.elm.services.applications import _validate_nominee

        _validate_nominee(
            application,
            payload.validated_data["nominee_user_id"])
        # A declined nomination is superseded; a
        # pending one is replaced.
        active = workflow._active_nomination(
            application)
        if active is not None:
            active.is_active = False
            active.status = "superseded"
            active.save()
        SubstituteNomination.objects.create(
            request=application,
            nominee_user_id=(
                payload.validated_data[
                    "nominee_user_id"]),
        )
        # Re-entering the awaiting state re-spawns
        # the substitute task for the new nominee.
        if application.status in (
                "applicant_action_required",
                "extension_applicant_action_required"):
            workflow.apply_transition(
                application,
                actor="employee",
                guard="replacement_nominated",
                outcome="replacement_nominated",
                reason=(
                    payload.validated_data.get(
                        "reason", "")),
                principal=principal)
        else:
            workflow.spawn_tasks(application)
        return Response(
            s.LeaveRequestSerializer(
                application).data)


# -- substitute / responsibility holder -------------------------------


class SubstituteTaskListView(APIView):
    """My pending substitute assignments."""

    permission_classes = [MODULE,
                          HasPermission(P_SUBSTITUTE)]

    @extend_schema(responses=s.TaskWithRequestSerializer(many=True))
    def get(self, request):
        principal = _actor(request)
        tasks = queues.substitute_assignments(
            principal.user_id)
        return Response(
            s.TaskWithRequestSerializer(
                tasks, many=True).data)


class SubstituteTaskRespondView(APIView):
    permission_classes = [MODULE,
                          HasPermission(P_SUBSTITUTE)]

    @extend_schema(request=s.SubstituteResponseSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk):
        principal = _actor(request)
        try:
            task = LeaveTask.objects.get(
                id=pk, assignee_user_id=principal.user_id,
                status="pending",
                task_class="substitute_response")
        except LeaveTask.DoesNotExist as exc:
            raise NotFoundError() from exc
        payload = s.SubstituteResponseSerializer(
            data=request.data)
        payload.is_valid(raise_exception=True)
        application = workflow.respond_substitute(
            task.request, principal,
            **payload.validated_data)
        return Response(
            s.LeaveRequestSerializer(
                application).data)


# -- decision seats ------------------------------------------------------


class QueueListView(APIView):
    """Everything actionable for the caller —
    Unit Head reviews, Establishment routing,
    sanctioning decisions and substitute
    assignments, in one queue."""

    permission_classes = [MODULE,
                          HasPermission(P_VIEW_SELF)]

    @extend_schema(responses=s.TaskWithRequestSerializer(many=True))
    def get(self, request):
        principal = _actor(request)
        tasks = queues.queue_for(principal.user_id)
        return Response(
            s.TaskWithRequestSerializer(
                tasks, many=True).data)


class TaskDetailView(APIView):
    permission_classes = [MODULE,
                          HasPermission(P_VIEW_SELF)]

    @extend_schema(responses=s.TaskWithRequestSerializer)
    def get(self, request, pk):
        principal = _actor(request)
        try:
            task = LeaveTask.objects.get(
                id=pk,
                assignee_user_id=principal.user_id,
                status="pending")
        except LeaveTask.DoesNotExist as exc:
            raise NotFoundError() from exc
        return Response(
            s.TaskWithRequestSerializer(task).data)


class TaskDecideView(APIView):
    """Answer a task: the Unit Head's decision or
    recommendation, the Establishment routing, or
    the final sanctioning decision — dispatched by
    the state the request is in."""

    permission_classes = [
        MODULE,
        HasPermission(*P_DECIDE_ANY)]

    @extend_schema(request=s.DecisionSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk):
        principal = _actor(request)
        try:
            task = LeaveTask.objects.get(
                id=pk,
                assignee_user_id=principal.user_id,
                status="pending")
        except LeaveTask.DoesNotExist as exc:
            raise NotFoundError() from exc
        payload = s.DecisionSerializer(
            data=request.data)
        payload.is_valid(raise_exception=True)
        request_obj = _dispatch_decide(
            task.request, principal,
            outcome=payload.validated_data["outcome"],
            reason=payload.validated_data["reason"])
        return Response(
            s.LeaveRequestSerializer(
                request_obj).data)


class RequestDecideView(APIView):
    """Decide by request id — the same dispatch as
    the task endpoint, for the detail view."""

    permission_classes = [
        MODULE,
        HasPermission(*P_DECIDE_ANY)]

    @extend_schema(request=s.DecisionSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk):
        principal = _actor(request)
        request_obj = _own_request(request, pk)
        payload = s.DecisionSerializer(
            data=request.data)
        payload.is_valid(raise_exception=True)
        request_obj = _dispatch_decide(
            request_obj, principal,
            outcome=payload.validated_data["outcome"],
            reason=payload.validated_data["reason"])
        return Response(
            s.LeaveRequestSerializer(
                request_obj).data)


# -- cancellation and extension -------------------------------------------


class CancellationCreateView(APIView):
    permission_classes = [MODULE,
                          HasPermission(P_CANCEL)]

    @extend_schema(request=s.CancellationSerializer, responses={201: s.LeaveRequestSerializer})
    def post(self, request):
        principal = _actor(request)
        payload = s.CancellationSerializer(
            data=request.data)
        payload.is_valid(raise_exception=True)
        cancellation = lifecycle.request_cancellation(
            principal, **payload.validated_data)
        return Response(
            s.LeaveRequestSerializer(
                cancellation).data,
            status=status.HTTP_201_CREATED)


class ExtensionCreateView(APIView):
    permission_classes = [MODULE,
                          HasPermission(P_EXTEND)]

    @extend_schema(request=s.ExtensionSerializer, responses={201: s.LeaveRequestSerializer})
    def post(self, request):
        principal = _actor(request)
        payload = s.ExtensionSerializer(
            data=request.data)
        payload.is_valid(raise_exception=True)
        extension = lifecycle.request_extension(
            principal, **payload.validated_data)
        return Response(
            s.LeaveRequestSerializer(
                extension).data,
            status=status.HTTP_201_CREATED)


# -- resumption ------------------------------------------------------------


class ResumptionCreateView(APIView):
    permission_classes = [MODULE,
                          HasPermission(P_RESUME)]

    @extend_schema(request=s.ResumptionWriteSerializer, responses={201: s.ResumptionReadSerializer})
    def post(self, request):
        principal = _actor(request)
        payload = s.ResumptionWriteSerializer(
            data=request.data)
        payload.is_valid(raise_exception=True)
        resumption = lifecycle.submit_resumption(
            principal, **payload.validated_data)
        return Response(
            s.ResumptionReadSerializer(
                resumption).data,
            status=status.HTTP_201_CREATED)


class ResumptionReviewView(APIView):
    permission_classes = [MODULE,
                          HasPermission(P_RESUME_REVIEW)]

    @extend_schema(request=s.ResumptionReviewWriteSerializer, responses=s.ResumptionReadSerializer)
    def post(self, request, pk):
        principal = _actor(request)
        try:
            resumption = Resumption.objects.get(
                id=pk, status="review_pending")
        except Resumption.DoesNotExist as exc:
            raise NotFoundError() from exc
        payload = s.ResumptionReviewWriteSerializer(
            data=request.data)
        payload.is_valid(raise_exception=True)
        resumption = lifecycle.review_resumption(
            resumption, principal,
            **payload.validated_data)
        return Response(
            s.ResumptionReadSerializer(
                resumption).data)


# -- records ---------------------------------------------------------------


class RecordListView(APIView):
    """Leave records in the caller's scope: their
    own always, the whole book with
    ``elm.records.view``."""

    permission_classes = [MODULE]

    def get_permissions(self):
        principal = _actor(self.request)
        # During schema generation there is no
        # principal; assume the narrower requirement.
        if principal is not None and principal.has_permission(
                P_RECORDS_VIEW):
            return []
        return [HasPermission(P_VIEW_SELF)()]

    @extend_schema(responses=s.LeaveRecordSummarySerializer(many=True))
    def get(self, request):
        principal = _actor(request)
        may_view_all = principal.has_permission(
            P_RECORDS_VIEW)

        qs = request_selectors.records_for(
            principal.user_id,
            may_view_all=may_view_all)
        unit = request.query_params.get("unit")
        if unit and may_view_all:
            qs = qs.filter(
                user_id__in=_unit_member_ids(unit))
        category = request.query_params.get(
            "category")
        if category:
            qs = qs.filter(category=category)
        return Response(
            s.LeaveRecordSummarySerializer(
                qs[:100], many=True).data)


def _unit_member_ids(unit_code: str):
    from modules.elm.models import EmployeeProfile

    return EmployeeProfile.objects.filter(
        unit_code=unit_code,
        is_active=True).values_list(
            "user_id", flat=True)


class OfflineRecordCreateView(APIView):
    """Record an already-sanctioned leave (EL-UC-017).

    Leave Administrator only; the entry carries
    evidence and no workflow.
    """

    permission_classes = [MODULE,
                          HasPermission(P_RECORDS_OFFLINE)]

    @extend_schema(request=s.OfflineRecordSerializer,
                   responses={201: s.OfflineRecordReadSerializer})
    def post(self, request):
        principal = _actor(request)
        payload = s.OfflineRecordSerializer(
            data=request.data)
        payload.is_valid(raise_exception=True)
        entry = offline_service.record_offline(
            principal, **payload.validated_data)
        return Response(
            s.OfflineRecordReadSerializer(
                entry).data,
            status=status.HTTP_201_CREATED)


# -- calendar ------------------------------------------------------------


class CalendarView(APIView):
    """The currently effective published calendar —
    what RH requests are checked against."""

    permission_classes = [MODULE,
                          HasPermission(P_VIEW_SELF)]

    @extend_schema(responses=s.CalendarSerializer)
    def get(self, request):
        calendar = (
            request_selectors.effective_calendar())
        if calendar is None:
            return Response(
                {"published": False})
        return Response(
            s.CalendarSerializer(calendar).data)


# -- configuration ---------------------------------------------------------


class AdminPolicyView(APIView):
    permission_classes = [MODULE,
                          HasPermission(P_CONFIG_POLICY)]

    @extend_schema(responses=s.PolicySerializer)
    def get(self, request):
        return Response(
            s.PolicySerializer(
                admin_service.get_policy()).data)

    @extend_schema(request=s.PolicySerializer, responses=s.PolicySerializer)
    def put(self, request):
        principal = _actor(request)
        policy = admin_service.update_policy(
            principal, **request.data)
        return Response(
            s.PolicySerializer(policy).data)


class AdminHierarchyListView(APIView):
    permission_classes = [MODULE,
                          HasPermission(P_CONFIG_HIERARCHY)]

    @extend_schema(responses=s.HierarchySerializer(many=True))
    def get(self, request):
        return Response(
            s.HierarchySerializer(
                admin_service.hierarchy_rows(),
                many=True).data)

    @extend_schema(request=s.HierarchySerializer, responses=s.HierarchySerializer)
    def post(self, request):
        principal = _actor(request)
        row = admin_service.upsert_hierarchy(
            principal, **request.data)
        return Response(
            s.HierarchySerializer(row).data)


class AdminSlaListView(APIView):
    permission_classes = [MODULE,
                          HasPermission(P_CONFIG_SLA)]

    @extend_schema(responses=s.SlaSerializer(many=True))
    def get(self, request):
        return Response(
            s.SlaSerializer(
                admin_service.sla_rows(),
                many=True).data)

    @extend_schema(request=s.SlaSerializer, responses=s.SlaSerializer)
    def post(self, request):
        principal = _actor(request)
        row = admin_service.upsert_sla(
            principal, **request.data)
        return Response(
            s.SlaSerializer(row).data)


class AdminCalendarListView(APIView):
    permission_classes = [MODULE,
                          HasPermission(P_CONFIG_CALENDAR)]

    @extend_schema(responses=s.CalendarSerializer(many=True))
    def get(self, request):
        return Response(
            s.CalendarSerializer(
                admin_service.calendar_list(),
                many=True).data)

    @extend_schema(request=s.CalendarCreateSerializer, responses={201: s.CalendarSerializer})
    def post(self, request):
        principal = _actor(request)
        calendar = admin_service.create_calendar(
            principal, **request.data)
        return Response(
            s.CalendarSerializer(calendar).data,
            status=status.HTTP_201_CREATED)


class AdminCalendarPublishView(APIView):
    permission_classes = [MODULE,
                          HasPermission(P_CONFIG_CALENDAR)]

    @extend_schema(request=None, responses=s.CalendarSerializer)
    def post(self, request, pk):
        principal = _actor(request)
        calendar = admin_service.publish_calendar(
            principal, pk)
        return Response(
            s.CalendarSerializer(calendar).data)


class AdminHolidayUpsertView(APIView):
    permission_classes = [MODULE,
                          HasPermission(P_CONFIG_CALENDAR)]

    @extend_schema(request=s.HolidayWriteSerializer, responses=s.HolidaySerializer)
    def post(self, request, pk):
        principal = _actor(request)
        payload = s.HolidayWriteSerializer(
            data=request.data)
        payload.is_valid(raise_exception=True)
        holiday = admin_service.upsert_holiday(
            principal, calendar_id=pk,
            **payload.validated_data)
        return Response(
            s.HolidaySerializer(holiday).data)


class AdminUnitListView(APIView):
    permission_classes = [MODULE,
                          HasPermission(P_CONFIG_UNITS)]

    @extend_schema(responses=s.UnitSerializer(many=True))
    def get(self, request):
        return Response(
            s.UnitSerializer(
                admin_service.unit_list(),
                many=True).data)

    @extend_schema(request=s.UnitWriteSerializer, responses=s.UnitSerializer)
    def post(self, request):
        principal = _actor(request)
        unit = admin_service.upsert_unit(
            principal, **request.data)
        return Response(
            s.UnitSerializer(unit).data)


class AdminUnitHeadView(APIView):
    permission_classes = [MODULE,
                          HasPermission(P_CONFIG_UNITS)]

    @extend_schema(request=s.UnitHeadSerializer, responses=s.UnitSerializer)
    def post(self, request, code):
        principal = _actor(request)
        payload = s.UnitHeadSerializer(
            data=request.data)
        payload.is_valid(raise_exception=True)
        unit = admin_service.set_unit_head(
            principal, code=code,
            **payload.validated_data)
        return Response(
            s.UnitSerializer(unit).data)


class AdminProfileView(APIView):
    """Maintain the ELM projection of an employee."""

    permission_classes = [MODULE,
                          HasPermission(P_CONFIG_UNITS)]

    @extend_schema(request=s.EmployeeProfileSerializer,
                   responses={200: OpenApiTypes.OBJECT})
    def post(self, request):
        principal = _actor(request)
        payload = s.EmployeeProfileSerializer(
            data=request.data)
        payload.is_valid(raise_exception=True)
        admin_service.set_employee_profile(
            principal, **payload.validated_data)
        return Response({"status": "updated"})


class AdminVacationListView(APIView):
    permission_classes = [MODULE,
                          HasPermission(P_CONFIG_VACATION)]

    @extend_schema(responses=s.VacationSerializer(many=True))
    def get(self, request):
        return Response(
            s.VacationSerializer(
                admin_service.vacation_list(),
                many=True).data)

    @extend_schema(request=s.VacationWriteSerializer, responses=s.VacationSerializer)
    def post(self, request):
        principal = _actor(request)
        period = admin_service.upsert_vacation(
            principal, **request.data)
        return Response(
            s.VacationSerializer(period).data)


class AdminRecordMaintainView(APIView):
    """Authorized record maintenance (BR-EL-036) —
    Leave Administrator only, fully audited."""

    permission_classes = [MODULE,
                          HasPermission(P_RECORDS_MAINTAIN)]

    @extend_schema(request=s.RecordMaintainSerializer,
                   responses={200: OpenApiTypes.OBJECT})
    def post(self, request, pk):
        principal = _actor(request)
        payload = s.RecordMaintainSerializer(
            data=request.data)
        payload.is_valid(raise_exception=True)
        record, changed = admin_service.maintain_record(
            principal, record_id=pk,
            **payload.validated_data)
        return Response({
            "id": record.id, "status": record.status,
            "actual_end_date": record.actual_end_date,
            "changed": changed,
        })


class YearEndView(APIView):
    """Trigger year-end processing for a leave
    year (EL-UC-020)."""

    permission_classes = [MODULE,
                          HasPermission(P_YEAREND)]

    @extend_schema(request=s.YearEndSerializer, responses=s.YearEndRunSerializer)
    def post(self, request):
        principal = _actor(request)
        payload = s.YearEndSerializer(
            data=request.data)
        payload.is_valid(raise_exception=True)
        run = year_end_service.run_year_end(
            principal, **payload.validated_data)
        return Response({
            "leave_year": run.leave_year,
            "stats": run.stats,
            "exceptions": run.exceptions,
        })


class SlaSweepView(APIView):
    """Run one SLA sweep on demand — the beat
    runs it automatically."""

    permission_classes = [
        MODULE,
        HasPermission(P_CONFIG_SLA,
                      P_RECORDS_VIEW)]

    @extend_schema(request=None, responses=s.SlaSweepReportSerializer)
    def post(self, request):
        result = sla_service.sweep()
        return Response(result)
