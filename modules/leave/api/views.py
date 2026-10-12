from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.api import serializers as s
from modules.leave.selectors import scoping
from modules.leave.services import applications, decisions, resumption

MODULE = HasModuleGrant("leave")
REQUEST_PERMISSIONS = HasPermission(
    "leave.request.view_self",
    "leave.request.review",
    "leave.request.route",
    "leave.request.sanction",
    "leave.offline.record",
)


def _actor(request):
    return getattr(request, "principal", None)


def _int_param(params, name):
    """A non-integer filter is a 400, not a ValueError deep in the ORM."""
    raw = params.get(name)
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise BadRequestError(f"{name} must be a number.", code="invalid_filter") from exc


class RequestListView(generics.ListCreateAPIView):
    serializer_class = s.LeaveRequestSerializer
    permission_classes = [MODULE, REQUEST_PERMISSIONS]

    def get_queryset(self):
        return scoping.requests_for(_actor(self.request)).order_by("-created_at")

    @extend_schema(request=s.ApplySerializer, responses=s.LeaveRequestSerializer)
    def create(self, request, *args, **kwargs):
        payload = s.ApplySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        request_obj = applications.apply(actor=_actor(request), **payload.validated_data)
        return Response(s.LeaveRequestSerializer(request_obj).data, status=status.HTTP_201_CREATED)


class RequestWithdrawView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.create")]

    @extend_schema(request=s.WithdrawSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk):
        payload = s.WithdrawSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        request_obj = applications.withdraw(request_id=pk, actor=_actor(request))
        return Response(s.LeaveRequestSerializer(request_obj).data)


class RequestCancelView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.create")]

    @extend_schema(request=s.WithdrawSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk):
        payload = s.WithdrawSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        request_obj = applications.request_cancellation(request_id=pk, actor=_actor(request))
        return Response(s.LeaveRequestSerializer(request_obj).data)


class SubstituteResponseView(APIView):
    permission_classes = [MODULE, HasPermission("leave.substitute.respond")]

    @extend_schema(request=s.SubstituteResponseSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk):
        payload = s.SubstituteResponseSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        request_obj = applications.respond_substitute(
            request_id=pk, actor=_actor(request), accept=payload.validated_data["accept"]
        )
        return Response(s.LeaveRequestSerializer(request_obj).data)


class RequestReviewView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.review")]

    @extend_schema(request=s.ReviewSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk):
        payload = s.ReviewSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        request_obj = decisions.review(
            request_id=pk,
            actor=_actor(request),
            outcome=payload.validated_data["outcome"],
            note=payload.validated_data.get("note", ""),
            scope=scoping.requests_for(_actor(request)),
        )
        return Response(s.LeaveRequestSerializer(request_obj).data)


class RequestRouteView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.route")]

    @extend_schema(request=s.RouteSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk):
        payload = s.RouteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        request_obj = decisions.route(
            request_id=pk,
            actor=_actor(request),
            note=payload.validated_data.get("note", ""),
            scope=scoping.requests_for(_actor(request)),
        )
        return Response(s.LeaveRequestSerializer(request_obj).data)


class RequestSanctionView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.sanction")]

    @extend_schema(request=s.SanctionSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk):
        payload = s.SanctionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        request_obj = decisions.sanction(
            request_id=pk,
            actor=_actor(request),
            decision=payload.validated_data["decision"],
            note=payload.validated_data.get("note", ""),
            scope=scoping.requests_for(_actor(request)),
        )
        return Response(s.LeaveRequestSerializer(request_obj).data)


class ResumptionSubmitView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.create")]

    @extend_schema(request=s.ResumptionSubmitSerializer, responses=s.ResumptionSerializer)
    def post(self, request, pk):
        payload = s.ResumptionSubmitSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        resumption_obj = resumption.submit_resumption(
            request_id=pk, actor=_actor(request), resumed_on=payload.validated_data["resumed_on"]
        )
        return Response(s.ResumptionSerializer(resumption_obj).data)
