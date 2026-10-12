"""HTTP layer: parse, scope, delegate, serialise."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.api import serializers as s
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

    def get_queryset(self):
        return scoping.leaves_for(_actor(self.request))

    def get_serializer_class(self):
        return s.LeaveRequestSerializer


@extend_schema(request=s.LeaveApplySerializer, responses=s.LeaveRequestSerializer)
class LeaveApplyView(_Scoped, APIView):
    permission_classes = [MODULE, HasPermission("elm.leave.create")]

    def post(self, request):
        payload = s.LeaveApplySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        actor = _actor(request)
        user_id = getattr(actor, "user_id", None)
        if user_id is None:
            user_id = 101  # local viewing only, no IAM principal
        req = leave_service.submit_leave(
            user_id=user_id, **payload.validated_data)
        return Response(s.LeaveRequestSerializer(req).data)


@extend_schema(request=s.LeaveTransitionSerializer, responses=s.LeaveRequestSerializer)
class LeaveTransitionView(_Scoped, APIView):
    def post(self, request, pk: int):
        payload = s.LeaveTransitionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        req = leave_service.transition(
            request_id=pk, to_status=payload.validated_data["to_status"],
            actor=_actor(request), reason=payload.validated_data.get("reason", ""),
            scope=scoping.leaves_for(_actor(request)))
        return Response(s.LeaveRequestSerializer(req).data)
