"""Leave endpoints.

Two gates on every route: the module grant, then the permission. Ownership is
enforced by narrowing the queryset, so a request belonging to somebody else is
not found rather than refused.
"""
from __future__ import annotations

from datetime import date

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.directory import contracts as directory
from modules.leave.api import serializers as s
from modules.leave.domain.categories import Category
from modules.leave.domain.counting import Half
from modules.leave.models import (
    CategoryRule,
    Holiday,
    HolidayCalendar,
    LeavePolicy,
    VacationPeriod,
)
from modules.leave.selectors import balances, scoping
from modules.leave.services import administration, decisions, lifecycle
from modules.leave.services import requests as request_service

MODULE = HasModuleGrant("leave")

P_CREATE = "leave.request.create"
P_VIEW_SELF = "leave.request.view_self"
P_WITHDRAW = "leave.request.withdraw"
P_SUBSTITUTE = "leave.substitute.respond"
P_REVIEW = "leave.request.review"
P_ROUTE = "leave.request.route"
P_SANCTION = "leave.request.sanction"
P_VERIFY = "leave.resumption.verify"
P_BALANCE = "leave.balance.view"
P_POLICY = "leave.policy.manage"
P_CALENDAR = "leave.calendar.manage"
P_OFFLINE = "leave.offline.record"

#: Opening one request. Which requests, and whose, is the queryset's job:
#: any leave reader may ask, and sees only what their scope contains.
P_READ = (P_VIEW_SELF, P_REVIEW, P_ROUTE, P_SANCTION, P_VERIFY, P_BALANCE)


def _actor(request):
    return request.principal


def _unit(request) -> str:
    """The actor's department, from the directory rather than the credential.

    IAM's session carries no organisational unit, so routing and the review
    queue would silently fall back to "the whole institute" if this were read
    off the principal. An unknown department gives an empty unit, which matches
    nothing.
    """
    actor = _actor(request)
    known = directory.get_users([actor.user_id]).get(actor.user_id)
    return known.department if known else ""


def _get(request, pk):
    found = (
        scoping.visible_to(_actor(request), _unit(request)).filter(pk=pk).first()
    )
    if found is None:
        raise NotFoundError("No such leave request.")
    return found


def _mine(request, pk):
    found = scoping.mine(_actor(request).user_id).filter(pk=pk).first()
    if found is None:
        raise NotFoundError("No such leave request.")
    return found


class MyLeaveView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    @extend_schema(responses=s.LeaveRequestSerializer(many=True))
    def get(self, request):
        rows = scoping.mine(_actor(request).user_id).order_by("-starts_on")
        return Response(s.LeaveRequestSerializer(rows, many=True).data)


class ApplyView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]

    @extend_schema(request=s.ApplyLeaveSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request):
        body = s.ApplyLeaveSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data
        actor = _actor(request)
        created = request_service.submit(
            user_id=actor.user_id,
            category=Category(data["category"]),
            starts_on=data["starts_on"],
            ends_on=data["ends_on"],
            reason=data["reason"],
            faculty=getattr(actor, "kind", "") == "faculty",
            unit=_unit(request),
            half=Half(data["half"]) if data.get("half") else None,
            substitute_user_id=data.get("substitute_user_id"),
            station=data.get("station"),
        )
        return Response(
            s.LeaveRequestSerializer(created).data, status=status.HTTP_201_CREATED
        )


class LeaveDetailView(APIView):
    permission_classes = [MODULE, HasPermission(*P_READ)]

    @extend_schema(responses=s.LeaveRequestSerializer)
    def get(self, request, pk: int):
        return Response(s.LeaveRequestSerializer(_get(request, pk)).data)


class TrailView(APIView):
    permission_classes = [MODULE, HasPermission(*P_READ)]

    @extend_schema(responses=s.LeaveTransitionSerializer(many=True))
    def get(self, request, pk: int):
        found = _get(request, pk)
        rows = found.transitions.order_by("id")
        return Response(s.LeaveTransitionSerializer(rows, many=True).data)


class WithdrawView(APIView):
    permission_classes = [MODULE, HasPermission(P_WITHDRAW)]

    @extend_schema(request=s.RemarkSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk: int):
        body = s.RemarkSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        actor = _actor(request)
        updated = decisions.withdraw(
            request=_mine(request, pk),
            actor_user_id=actor.user_id,
            remark=body.validated_data.get("remark", ""),
        )
        return Response(s.LeaveRequestSerializer(updated).data)


class NominationsView(APIView):
    permission_classes = [MODULE, HasPermission(P_SUBSTITUTE)]

    @extend_schema(responses=s.LeaveRequestSerializer(many=True))
    def get(self, request):
        rows = scoping.nominations_for(_actor(request).user_id)
        return Response(
            s.LeaveRequestSerializer([n.request for n in rows], many=True).data
        )


class SubstituteRespondView(APIView):
    permission_classes = [MODULE, HasPermission(P_SUBSTITUTE)]

    @extend_schema(
        request=s.SubstituteResponseSerializer, responses=s.LeaveRequestSerializer
    )
    def post(self, request, pk: int):
        body = s.SubstituteResponseSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        actor = _actor(request)
        nomination = scoping.nominations_for(actor.user_id).filter(request_id=pk).first()
        if nomination is None:
            raise NotFoundError("No pending nomination for you on this request.")
        updated = decisions.substitute_responds(
            request=nomination.request,
            substitute_user_id=actor.user_id,
            accepted=body.validated_data["accepted"],
            remark=body.validated_data.get("remark", ""),
        )
        return Response(s.LeaveRequestSerializer(updated).data)


class ReviewQueueView(APIView):
    permission_classes = [MODULE, HasPermission(P_REVIEW)]

    @extend_schema(responses=s.LeaveRequestSerializer(many=True))
    def get(self, request):
        rows = scoping.review_queue(_unit(request))
        return Response(s.LeaveRequestSerializer(rows, many=True).data)


class ReviewDecisionView(APIView):
    permission_classes = [MODULE, HasPermission(P_REVIEW)]

    @extend_schema(request=s.DecisionSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk: int):
        body = s.DecisionSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        actor = _actor(request)
        found = _get(request, pk)
        remark = body.validated_data.get("remark", "")
        approve = body.validated_data["approve"]
        if found.state.startswith("CANCELLATION"):
            updated = lifecycle.decide_cancellation_unit_head(
                request=found, actor_user_id=actor.user_id, approve=approve, remark=remark
            )
        elif found.state.startswith("EXTENSION") and approve:
            updated = lifecycle.recommend_extension(
                request=found, actor_user_id=actor.user_id, remark=remark
            )
        else:
            updated = decisions.unit_head_decides(
                request=found, actor_user_id=actor.user_id, approve=approve, remark=remark
            )
        return Response(s.LeaveRequestSerializer(updated).data)


class RoutingQueueView(APIView):
    permission_classes = [MODULE, HasPermission(P_ROUTE)]

    @extend_schema(responses=s.LeaveRequestSerializer(many=True))
    def get(self, request):
        return Response(
            s.LeaveRequestSerializer(scoping.routing_queue(), many=True).data
        )


class RouteView(APIView):
    permission_classes = [MODULE, HasPermission(P_ROUTE)]

    @extend_schema(request=s.RemarkSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk: int):
        body = s.RemarkSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        actor = _actor(request)
        found = _get(request, pk)
        remark = body.validated_data.get("remark", "")
        if found.state.startswith("CANCELLATION"):
            updated = lifecycle.route_cancellation(
                request=found, actor_user_id=actor.user_id, remark=remark
            )
        elif found.state.startswith("EXTENSION"):
            updated = lifecycle.route_extension(
                request=found, actor_user_id=actor.user_id, remark=remark
            )
        else:
            updated = decisions.establishment_routes(
                request=found, actor_user_id=actor.user_id, remark=remark
            )
        return Response(s.LeaveRequestSerializer(updated).data)


class SanctionQueueView(APIView):
    permission_classes = [MODULE, HasPermission(P_SANCTION)]

    @extend_schema(responses=s.LeaveRequestSerializer(many=True))
    def get(self, request):
        return Response(
            s.LeaveRequestSerializer(scoping.sanction_queue(), many=True).data
        )


class SanctionView(APIView):
    permission_classes = [MODULE, HasPermission(P_SANCTION)]

    @extend_schema(request=s.DecisionSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk: int):
        body = s.DecisionSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        actor = _actor(request)
        found = _get(request, pk)
        remark = body.validated_data.get("remark", "")
        approve = body.validated_data["approve"]
        if found.state.startswith("CANCELLATION"):
            updated = lifecycle.decide_cancellation_final(
                request=found, actor_user_id=actor.user_id, approve=approve, remark=remark
            )
        elif found.state.startswith("EXTENSION"):
            updated = lifecycle.decide_extension(
                request=found, actor_user_id=actor.user_id, approve=approve, remark=remark
            )
        else:
            updated = decisions.sanction(
                request=found, actor_user_id=actor.user_id, approve=approve, remark=remark
            )
        return Response(s.LeaveRequestSerializer(updated).data)


class ExtensionView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]

    @extend_schema(request=s.ExtensionSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk: int):
        body = s.ExtensionSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        actor = _actor(request)
        updated = lifecycle.request_extension(
            request=_mine(request, pk),
            actor_user_id=actor.user_id,
            new_end=body.validated_data["new_end"],
            substitute_user_id=body.validated_data.get("substitute_user_id"),
            remark=body.validated_data.get("remark", ""),
        )
        return Response(s.LeaveRequestSerializer(updated).data)


class CancellationView(APIView):
    permission_classes = [MODULE, HasPermission(P_WITHDRAW)]

    @extend_schema(request=s.RemarkSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk: int):
        body = s.RemarkSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        actor = _actor(request)
        updated = lifecycle.request_cancellation(
            request=_mine(request, pk),
            actor_user_id=actor.user_id,
            remark=body.validated_data.get("remark", ""),
        )
        return Response(s.LeaveRequestSerializer(updated).data)


class ResumptionView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    @extend_schema(request=s.ResumptionSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk: int):
        body = s.ResumptionSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        actor = _actor(request)
        updated = lifecycle.submit_resumption(
            request=_mine(request, pk),
            actor_user_id=actor.user_id,
            resumed_on=body.validated_data["resumed_on"],
            remark=body.validated_data.get("remark", ""),
        )
        return Response(s.LeaveRequestSerializer(updated).data)


class ResumptionQueueView(APIView):
    permission_classes = [MODULE, HasPermission(P_VERIFY)]

    @extend_schema(responses=s.LeaveRequestSerializer(many=True))
    def get(self, request):
        return Response(
            s.LeaveRequestSerializer(scoping.resumption_queue(), many=True).data
        )


class VerifyResumptionView(APIView):
    permission_classes = [MODULE, HasPermission(P_VERIFY)]

    @extend_schema(request=s.DecisionSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk: int):
        body = s.DecisionSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        actor = _actor(request)
        found = _get(request, pk)
        remark = body.validated_data.get("remark", "")
        if body.validated_data["approve"]:
            updated = lifecycle.verify_resumption(
                request=found, actor_user_id=actor.user_id, remark=remark
            )
        else:
            updated = lifecycle.query_resumption(
                request=found, actor_user_id=actor.user_id, remark=remark
            )
        return Response(s.LeaveRequestSerializer(updated).data)


class MyBalanceView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    @extend_schema(responses=s.BalanceSerializer(many=True))
    def get(self, request):
        year = int(request.query_params.get("year", date.today().year))
        held = balances.balances_for(_actor(request).user_id, year)
        return Response(
            [
                {
                    "category": category.value,
                    "available": balance.available,
                    "credited": balance.credited,
                    "consumed": balance.consumed,
                    "restored": balance.restored,
                }
                for category, balance in sorted(held.items())
            ]
        )


class StatementView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    @extend_schema(responses=s.LedgerEntrySerializer(many=True))
    def get(self, request, category: str):
        year = int(request.query_params.get("year", date.today().year))
        rows = balances.statement(_actor(request).user_id, year, Category(category))
        return Response(s.LedgerEntrySerializer(rows, many=True).data)


class BalanceDirectoryView(APIView):
    permission_classes = [MODULE, HasPermission(P_BALANCE)]

    @extend_schema(responses=s.BalanceSerializer(many=True))
    def get(self, request):
        user_id = int(request.query_params["user_id"])
        year = int(request.query_params.get("year", date.today().year))
        held = balances.balances_for(user_id, year)
        return Response(
            [
                {
                    "category": category.value,
                    "available": balance.available,
                    "credited": balance.credited,
                    "consumed": balance.consumed,
                    "restored": balance.restored,
                }
                for category, balance in sorted(held.items())
            ]
        )


class PolicyAdminView(APIView):
    permission_classes = [MODULE, HasPermission(P_POLICY)]

    @extend_schema(responses=s.PolicySerializer(many=True))
    def get(self, request):
        rows = LeavePolicy.objects.order_by("-effective_from")
        return Response(s.PolicySerializer(rows, many=True).data)


class PolicyRulesView(APIView):
    permission_classes = [MODULE, HasPermission(P_POLICY)]

    @extend_schema(responses=s.CategoryRuleSerializer(many=True))
    def get(self, request, pk: int):
        rows = CategoryRule.objects.filter(policy_id=pk).order_by("category")
        return Response(s.CategoryRuleSerializer(rows, many=True).data)


class PolicyPublishView(APIView):
    permission_classes = [MODULE, HasPermission(P_POLICY)]

    @extend_schema(request=None, responses=s.PolicySerializer)
    def post(self, request, pk: int):
        policy = LeavePolicy.objects.filter(pk=pk).first()
        if policy is None:
            raise NotFoundError("No such policy version.")
        published = administration.publish_policy(
            policy=policy, actor_user_id=_actor(request).user_id
        )
        return Response(s.PolicySerializer(published).data)


class CalendarAdminView(APIView):
    permission_classes = [MODULE, HasPermission(P_CALENDAR)]

    @extend_schema(responses=s.CalendarSerializer(many=True))
    def get(self, request):
        rows = HolidayCalendar.objects.order_by("-year", "-version")
        return Response(s.CalendarSerializer(rows, many=True).data)


class CalendarHolidaysView(APIView):
    permission_classes = [MODULE, HasPermission(P_CALENDAR)]

    @extend_schema(responses=s.HolidaySerializer(many=True))
    def get(self, request, pk: int):
        rows = Holiday.objects.filter(calendar_id=pk).order_by("day")
        return Response(s.HolidaySerializer(rows, many=True).data)

    @extend_schema(request=s.HolidaySerializer, responses=s.HolidaySerializer)
    def post(self, request, pk: int):
        body = s.HolidaySerializer(data=request.data)
        body.is_valid(raise_exception=True)
        added = administration.add_holiday(
            calendar=_calendar(pk), **body.validated_data
        )
        return Response(s.HolidaySerializer(added).data, status=status.HTTP_201_CREATED)


class CalendarVacationsView(APIView):
    permission_classes = [MODULE, HasPermission(P_CALENDAR)]

    @extend_schema(responses=s.VacationPeriodSerializer(many=True))
    def get(self, request, pk: int):
        rows = VacationPeriod.objects.filter(calendar_id=pk).order_by("starts_on")
        return Response(s.VacationPeriodSerializer(rows, many=True).data)

    @extend_schema(
        request=s.VacationPeriodSerializer, responses=s.VacationPeriodSerializer
    )
    def post(self, request, pk: int):
        body = s.VacationPeriodSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        added = administration.add_vacation_period(
            calendar=_calendar(pk), **body.validated_data
        )
        return Response(
            s.VacationPeriodSerializer(added).data, status=status.HTTP_201_CREATED
        )


class CalendarPublishView(APIView):
    permission_classes = [MODULE, HasPermission(P_CALENDAR)]

    @extend_schema(request=None, responses=s.CalendarSerializer)
    def post(self, request, pk: int):
        published = administration.publish_calendar(
            calendar=_calendar(pk), actor_user_id=_actor(request).user_id
        )
        return Response(s.CalendarSerializer(published).data)


class OfflineRecordView(APIView):
    permission_classes = [MODULE, HasPermission(P_OFFLINE)]

    @extend_schema(request=s.OfflineRecordSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request):
        body = s.OfflineRecordSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = dict(body.validated_data)
        half = data.pop("half", None)
        recorded = administration.record_offline(
            category=Category(data.pop("category")),
            half=Half(half) if half else None,
            recorded_by_user_id=_actor(request).user_id,
            **data,
        )
        return Response(
            s.LeaveRequestSerializer(recorded).data, status=status.HTTP_201_CREATED
        )


def _calendar(pk: int) -> HolidayCalendar:
    found = HolidayCalendar.objects.filter(pk=pk).first()
    if found is None:
        raise NotFoundError("No such calendar.")
    return found
