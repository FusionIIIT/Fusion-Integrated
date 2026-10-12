"""HTTP layer: parse, scope, delegate, serialise.

Every list takes its queryset from `selectors.scoping`, so authorisation is
never re-derived per endpoint. Services own the rules; a view only translates.
"""
from __future__ import annotations

import csv

from django.http import HttpResponse
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api import serializers as s
from modules.elm.domain import enums as e
from modules.elm.models import LeaveRequest
from modules.elm.selectors import scoping
from modules.elm.services import accounts as account_service
from modules.elm.services import approvals, calendars, config, offline, resumption, sla, substitutes
from modules.elm.services import requests as request_service

MODULE = HasModuleGrant("elm")

P_VIEW_ALL = "elm.leave_request.view"
P_VIEW_SELF = "elm.leave_request.view_self"
P_CREATE = "elm.leave_request.create"
P_WITHDRAW = "elm.leave_request.withdraw"
P_CANCEL = "elm.leave_request.cancel"
P_EXTENSION = "elm.leave_request.extension"
P_RESUMPTION = "elm.leave_request.resumption"
P_REVIEW = "elm.leave_request.review"
P_ESTABLISHMENT = "elm.leave_request.establishment"
P_SANCTION = "elm.leave_request.sanction"
P_PRINT = "elm.leave_request.print"
P_SUBSTITUTE = "elm.substitute.respond"
P_ACCOUNT = "elm.leave_account.view"
P_POLICY = "elm.policy.manage"
P_CALENDAR = "elm.calendar.manage"
P_RECORD = "elm.record.manage"
P_OFFLINE = "elm.offline.record"
P_SLA = "elm.sla.manage"

STAFF_TASKS = (P_REVIEW, P_ESTABLISHMENT, P_SANCTION, P_SUBSTITUTE)


def _actor(request):
    return getattr(request, "principal", None)


def _owned_request(request, pk: int) -> LeaveRequest:
    obj = scoping.requests_for(_actor(request)).filter(pk=pk).first()
    if obj is None:
        raise NotFoundError("No such leave request.")
    return obj


# -- Requests ------------------------------------------------------------------
class RequestListView(generics.ListAPIView):
    serializer_class = s.LeaveRequestSerializer
    permission_classes = [MODULE, HasPermission(P_VIEW_ALL, P_VIEW_SELF)]

    def get_queryset(self):
        qs = scoping.requests_for(_actor(self.request))
        state = self.request.query_params.get("status")
        category = self.request.query_params.get("category")
        if state:
            qs = qs.filter(status=state)
        if category:
            qs = qs.filter(category=category)
        return qs


class RequestCreateView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]
    throttle_scope = "apply"

    def post(self, request):
        payload = s.LeaveRequestCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        obj = request_service.submit_new(actor=_actor(request),
                                         **payload.validated_data)
        return Response(s.LeaveRequestSerializer(obj).data,
                        status=status.HTTP_201_CREATED)


class RequestDetailView(generics.RetrieveAPIView):
    serializer_class = s.LeaveRequestSerializer
    permission_classes = [MODULE, HasPermission(P_VIEW_ALL, P_VIEW_SELF)]

    def get_queryset(self):
        return scoping.requests_for(_actor(self.request))


class WithdrawView(APIView):
    permission_classes = [MODULE, HasPermission(P_WITHDRAW)]

    def post(self, request, pk):
        payload = s.NoteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        obj = request_service.withdraw(actor=_actor(request), request_id=pk,
                                       reason=payload.validated_data["note"])
        return Response(s.LeaveRequestSerializer(obj).data)


class CancelView(APIView):
    permission_classes = [MODULE, HasPermission(P_CANCEL)]

    def post(self, request, pk):
        obj = request_service.request_cancellation(actor=_actor(request),
                                                   request_id=pk)
        return Response(s.LeaveRequestSerializer(obj).data,
                        status=status.HTTP_201_CREATED)


class ExtendView(APIView):
    permission_classes = [MODULE, HasPermission(P_EXTENSION)]

    def post(self, request, pk):
        payload = s.ExtensionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        obj = request_service.request_extension(actor=_actor(request),
                                                request_id=pk,
                                                **payload.validated_data)
        return Response(s.LeaveRequestSerializer(obj).data,
                        status=status.HTTP_201_CREATED)


class NominateView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]

    def post(self, request, pk):
        payload = s.NominateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        obj = request_service.nominate_replacement(
            actor=_actor(request), request_id=pk,
            substitute_user_id=payload.validated_data["substitute_user_id"])
        return Response(s.LeaveRequestSerializer(obj).data)


class ResumptionSubmitView(APIView):
    permission_classes = [MODULE, HasPermission(P_RESUMPTION)]

    def post(self, request, pk):
        payload = s.ResumptionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        record = resumption.submit(actor=_actor(request), request_id=pk,
                                   **payload.validated_data)
        return Response(s.ResumptionRecordSerializer(record).data,
                        status=status.HTTP_201_CREATED)


class ResumptionReviewView(APIView):
    permission_classes = [MODULE, HasPermission(P_REVIEW)]

    def post(self, request, pk):
        record = resumption.review(actor=_actor(request), record_id=pk)
        return Response(s.ResumptionRecordSerializer(record).data)


# -- Approval chain ------------------------------------------------------------
class UnitHeadReviewView(APIView):
    permission_classes = [MODULE, HasPermission(P_REVIEW)]

    def post(self, request, pk):
        payload = s.DecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        obj = approvals.unit_head_decide(actor=_actor(request), request_id=pk,
                                         **payload.validated_data)
        return Response(s.LeaveRequestSerializer(obj).data)


class EstablishmentView(APIView):
    permission_classes = [MODULE, HasPermission(P_ESTABLISHMENT)]

    def post(self, request, pk):
        payload = s.NoteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        obj = approvals.establishment_forward(
            actor=_actor(request), request_id=pk,
            note=payload.validated_data["note"])
        return Response(s.LeaveRequestSerializer(obj).data)


class SanctionView(APIView):
    permission_classes = [MODULE, HasPermission(P_SANCTION)]

    def post(self, request, pk):
        payload = s.DecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        actor = _actor(request)
        role = e.DIRECTOR if request_service.is_director(actor) else e.SANCTION
        obj = approvals.final_sanction(actor=actor, request_id=pk, role=role,
                                       **payload.validated_data)
        return Response(s.LeaveRequestSerializer(obj).data)


class RequestsExportView(APIView):
    """A CSV of the request the actor may already see (BR-EL-034)."""

    permission_classes = [MODULE, HasPermission(P_PRINT)]

    def get(self, request):
        rows = scoping.requests_for(_actor(request))[:5000]
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="leave.csv"'
        writer = csv.writer(response)
        writer.writerow(["id", "applicant", "category", "kind", "start", "end",
                         "days", "status", "decision"])
        for r in rows:
            writer.writerow([r.pk, r.user_id, r.category, r.kind, r.start_date,
                             r.end_date, r.days, r.status, r.final_decision])
        return response


# -- Tasks and substitutions ---------------------------------------------------
class TaskQueueView(generics.ListAPIView):
    serializer_class = s.WorkflowTaskSerializer
    permission_classes = [MODULE, HasPermission(*STAFF_TASKS)]

    def get_queryset(self):
        return scoping.work_queue_for(_actor(self.request))


class SubstitutionListView(generics.ListAPIView):
    serializer_class = s.SubstituteAssignmentSerializer
    permission_classes = [MODULE, HasPermission(P_SUBSTITUTE)]

    def get_queryset(self):
        return scoping.substitute_assignments_for(_actor(self.request))


class SubstitutionRespondView(APIView):
    permission_classes = [MODULE, HasPermission(P_SUBSTITUTE)]

    def post(self, request, pk):
        payload = s.SubstituteResponseSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        assignment = substitutes.respond(actor=_actor(request), assignment_id=pk,
                                         **payload.validated_data)
        return Response(s.SubstituteAssignmentSerializer(assignment).data)


# -- Accounts ------------------------------------------------------------------
class AccountListView(generics.ListAPIView):
    serializer_class = s.LeaveAccountSerializer
    permission_classes = [MODULE, HasPermission(P_ACCOUNT)]

    def get_queryset(self):
        year = int(self.request.query_params.get("year") or
                   config.settings_row().current_year)
        return scoping.accounts_for(_actor(self.request), year=year)


class LedgerListView(generics.ListAPIView):
    serializer_class = s.LeaveTransactionSerializer
    permission_classes = [MODULE, HasPermission(P_ACCOUNT)]

    def get_queryset(self):
        user_id = self.request.query_params.get("user_id")
        year = self.request.query_params.get("year")
        qs = account_service.transactions_for(
            user_id=int(user_id) if user_id else _actor(self.request).user_id,
            year=int(year) if year else config.settings_row().current_year)
        actor = _actor(self.request)
        target = int(user_id) if user_id else actor.user_id
        if not scoping.may_read_account(actor, target):
            return qs.none()
        return qs


# -- Policy --------------------------------------------------------------------
class PolicyView(APIView):
    permission_classes = [MODULE, HasPermission(P_POLICY)]

    def get(self, request):
        types = [s.LeaveTypeConfigSerializer(t).data
                 for t in config.all_type_configs().values()]
        return Response({"leave_types": types,
                         "settings": s.SettingsSerializer(
                             config.settings_row()).data})

    def put(self, request, category):
        payload = s.LeaveTypeConfigSerializer(data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        row = config.update_policy(category=category,
                                   **payload.validated_data)
        return Response(s.LeaveTypeConfigSerializer(row).data)


# -- Calendar ------------------------------------------------------------------
class CalendarListView(APIView):
    permission_classes = [MODULE, HasPermission(P_CALENDAR)]

    def get(self, request):
        rows = scoping.calendars_for(_actor(request))
        return Response(s.HolidayCalendarSerializer(rows, many=True).data)

    def post(self, request):
        payload = s.CalendarCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = calendars.create_calendar(**payload.validated_data)
        return Response(s.HolidayCalendarSerializer(row).data,
                        status=status.HTTP_201_CREATED)


class CalendarHolidayView(APIView):
    permission_classes = [MODULE, HasPermission(P_CALENDAR)]

    def post(self, request, pk):
        payload = s.HolidayWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        cal = scoping.calendars_for(_actor(request)).filter(pk=pk).first()
        if cal is None:
            raise NotFoundError("No such calendar.")
        row = calendars.add_holiday(calendar=cal, **payload.validated_data)
        return Response(s.HolidaySerializer(row).data,
                        status=status.HTTP_201_CREATED)


class CalendarPublishView(APIView):
    permission_classes = [MODULE, HasPermission(P_CALENDAR)]

    def post(self, request, pk):
        cal = scoping.calendars_for(_actor(request)).filter(pk=pk).first()
        if cal is None:
            raise NotFoundError("No such calendar.")
        row = calendars.publish_calendar(calendar=cal,
                                         actor_user_id=_actor(request).user_id)
        return Response(s.HolidayCalendarSerializer(row).data)


class VacationListView(APIView):
    permission_classes = [MODULE, HasPermission(P_CALENDAR)]

    def get(self, request):
        return Response(s.VacationPeriodSerializer(
            calendars.list_vacation_periods(), many=True).data)

    def post(self, request):
        payload = s.VacationPeriodSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = calendars.add_vacation_period(**payload.validated_data)
        return Response(s.VacationPeriodSerializer(row).data,
                        status=status.HTTP_201_CREATED)


# -- Records -------------------------------------------------------------------
class RecordListView(generics.ListAPIView):
    serializer_class = s.LeaveRequestSerializer
    permission_classes = [MODULE, HasPermission(P_RECORD)]

    def get_queryset(self):
        return scoping.records_for(_actor(self.request))


class OfflineRecordView(APIView):
    permission_classes = [MODULE, HasPermission(P_OFFLINE)]

    def post(self, request):
        payload = s.OfflineRecordSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        obj = offline.record(actor=_actor(request), **payload.validated_data)
        return Response(s.LeaveRequestSerializer(obj).data,
                        status=status.HTTP_201_CREATED)


class YearEndView(APIView):
    permission_classes = [MODULE, HasPermission(P_POLICY)]

    def post(self, request):
        year = int(request.data.get("year") or
                   config.settings_row().current_year)
        report = account_service.year_end(year, actor_user_id=_actor(request).user_id)
        return Response(report)


# -- SLA -----------------------------------------------------------------------
class SlaListView(APIView):
    permission_classes = [MODULE, HasPermission(P_SLA)]

    def get(self, request):
        from modules.elm.models import SlaConfig
        rows = SlaConfig.objects.all()
        return Response(s.SlaConfigSerializer(rows, many=True).data)


class SlaUpdateView(APIView):
    permission_classes = [MODULE, HasPermission(P_SLA)]

    def put(self, request, task_type):
        payload = s.SlaConfigSerializer(data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        row = config.update_sla(task_type=task_type, **payload.validated_data)
        return Response(s.SlaConfigSerializer(row).data)


class SlaProcessView(APIView):
    permission_classes = [MODULE, HasPermission(P_SLA)]

    def post(self, request):
        report = sla.process()
        return Response({"reminded": report.reminded,
                         "escalated": report.escalated})
