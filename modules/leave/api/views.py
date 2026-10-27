"""Leave API views."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.api import serializers as s
from modules.leave.models import LeaveCategory
from modules.leave.selectors.applications import applications_for, balances_for
from modules.leave.services import applications as leave_services

MODULE = HasModuleGrant("leave_management")

P_VIEW_SELF = "leave_management.application.view_self"
P_VIEW = "leave_management.application.view"
P_CREATE = "leave_management.application.create"
P_RESPOND = "leave_management.application.respond"
P_REVIEW = "leave_management.application.review"
P_DELETE = "leave_management.application.delete"
P_BALANCE_VIEW = "leave_management.balance.view"
P_BALANCE_MANAGE = "leave_management.balance.manage"


def _actor(request):
    return getattr(request, "principal", None)


@extend_schema(responses=s.LeaveCategorySerializer(many=True))
class CategoryListView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF, P_VIEW)]

    def get(self, request):
        categories = LeaveCategory.objects.all().order_by("code")
        return Response(s.LeaveCategorySerializer(categories, many=True).data)


@extend_schema(responses=s.LeaveBalanceSerializer(many=True))
class BalanceListView(APIView):
    permission_classes = [MODULE, HasPermission(P_BALANCE_VIEW, P_BALANCE_MANAGE, P_VIEW_SELF)]

    def get(self, request):
        actor = _actor(request)
        balances = balances_for(actor)
        return Response(s.LeaveBalanceSerializer(balances, many=True).data)


@extend_schema(responses=s.LeaveApplicationSerializer(many=True))
class ApplicationListView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW, P_VIEW_SELF)]

    def get(self, request):
        actor = _actor(request)
        qs = applications_for(actor)
        status_param = request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        user_id_param = request.query_params.get("user_id")
        if user_id_param and actor and actor.has_permission(P_VIEW):
            qs = qs.filter(user_id=int(user_id_param))
        return Response(
            s.LeaveApplicationSerializer(qs, many=True, context={"actor": actor}).data
        )


@extend_schema(request=s.LeaveApplicationCreateSerializer, responses=s.LeaveApplicationSerializer)
class ApplicationCreateView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]

    def post(self, request):
        actor = _actor(request)
        payload = s.LeaveApplicationCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = leave_services.apply(user_id=actor.user_id, **payload.validated_data)
        return Response(
            s.LeaveApplicationSerializer(app, context={"actor": actor}).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(responses=s.LeaveApplicationSerializer)
class ApplicationDetailView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW, P_VIEW_SELF)]

    def get(self, request, pk: int):
        actor = _actor(request)
        app = applications_for(actor).filter(pk=pk).first()
        if app is None:
            raise NotFoundError("No such application.")
        return Response(s.LeaveApplicationSerializer(app, context={"actor": actor}).data)


@extend_schema(
    request=s.LeaveApplicationTransitionInputSerializer,
    responses=s.LeaveApplicationSerializer,
)
class ApplicationTransitionView(APIView):
    permission_classes = [MODULE, HasPermission(P_REVIEW, P_CREATE, P_DELETE, P_RESPOND)]

    def post(self, request, pk: int):
        actor = _actor(request)
        payload = s.LeaveApplicationTransitionInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = leave_services.transition(
            application_id=pk,
            actor=actor,
            scope=applications_for(actor),
            **payload.validated_data,
        )
        return Response(s.LeaveApplicationSerializer(app, context={"actor": actor}).data)


@extend_schema(responses=s.LeaveApplicationTransitionSerializer(many=True))
class ApplicationHistoryView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW, P_VIEW_SELF)]

    def get(self, request, pk: int):
        actor = _actor(request)
        app = applications_for(actor).filter(pk=pk).first()
        if app is None:
            raise NotFoundError("No such application.")
        transitions = app.transitions.all().order_by("at")
        return Response(s.LeaveApplicationTransitionSerializer(transitions, many=True).data)
