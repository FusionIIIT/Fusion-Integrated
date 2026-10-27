"""HTTP layer: parse, scope, delegate, serialise."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.api import serializers as s
from modules.leave.models import LeaveRequest
from modules.leave.selectors import leaves as scoping
from modules.leave.services import leaves as leave_service

MODULE = HasModuleGrant("elm")


def _actor(request):
    return getattr(request, "principal", None)


class _Scoped(generics.GenericAPIView):
    permission_classes = [MODULE]


@extend_schema(responses=s.LeaveRequestSerializer(many=True))
class LeaveListView(_Scoped, generics.ListAPIView):
    permission_classes = [MODULE, HasPermission("elm.leave.view_self")]
    serializer_class = s.LeaveRequestSerializer

    def get_queryset(self):
        return scoping.leaves_for(_actor(self.request))


@extend_schema(responses=s.LeaveRequestSerializer)
class LeaveDetailView(_Scoped, generics.RetrieveAPIView):
    permission_classes = [MODULE, HasPermission("elm.leave.view_self")]
    serializer_class = s.LeaveRequestSerializer

    def get_queryset(self):
        return scoping.leaves_for(_actor(self.request))


@extend_schema(request=s.LeaveApplySerializer, responses=s.LeaveRequestSerializer)
class LeaveApplyView(_Scoped, APIView):
    permission_classes = [MODULE, HasPermission("elm.leave.create")]

    def post(self, request):
        payload = s.LeaveApplySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        actor = _actor(request)
        user_id = getattr(actor, "user_id", None)
        if user_id is None:
            user_id = 101  # local viewing harness default
        req = leave_service.submit_leave(
            user_id=user_id, **payload.validated_data
        )
        return Response(s.LeaveRequestSerializer(req).data, status=status.HTTP_201_CREATED)


@extend_schema(request=s.SubstituteActionSerializer, responses=s.LeaveRequestSerializer)
class SubstituteActionView(_Scoped, APIView):
    """Consent gate for nominated substitutes (BR-EL-014, BR-EL-015)."""
    permission_classes = [MODULE]

    def post(self, request, pk: int):
        payload = s.SubstituteActionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        actor = _actor(request)
        user_id = getattr(actor, "user_id", 101)
        req = leave_service.respond_as_substitute(
            request_id=pk,
            substitute_user_id=user_id,
            accept=payload.validated_data["accept"],
            remarks=payload.validated_data.get("remarks", ""),
        )
        return Response(s.LeaveRequestSerializer(req).data)


@extend_schema(request=s.LeaveTransitionSerializer, responses=s.LeaveRequestSerializer)
class LeaveTransitionView(_Scoped, APIView):
    """Execute lifecycle transition: recommendation, sanction, cancellation, withdrawal."""
    def post(self, request, pk: int):
        payload = s.LeaveTransitionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        req = leave_service.transition(
            request_id=pk,
            to_status=payload.validated_data["to_status"],
            actor=_actor(request),
            reason=payload.validated_data.get("reason", ""),
            scope=scoping.leaves_for(_actor(request)),
        )
        return Response(s.LeaveRequestSerializer(req).data)


@extend_schema(responses=s.LeaveBalanceSerializer(many=True))
class LeaveBalanceListView(_Scoped, APIView):
    """Retrieve personal leave balance cards (BR-EL-001..009)."""
    permission_classes = [MODULE, HasPermission("elm.leave.view_self")]

    def get(self, request):
        actor = _actor(request)
        user_id = getattr(actor, "user_id", 101)
        leave_service.initialize_user_balances(user_id, 2026)
        balances = scoping.balances_for(user_id)
        return Response(s.LeaveBalanceSerializer(balances, many=True).data)
