"""HTTP layer: parse, scope, delegate, serialise. Rules live in domain/ and
services/; every queryset comes from the selectors."""
from __future__ import annotations

from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api import serializers as s
from modules.elm.domain.state_machine import P_APPROVE, P_REVIEW, P_VIEW
from modules.elm.models import LeaveRequest
from modules.elm.selectors import leaves as selectors
from modules.elm.services import leaves as service

MODULE = HasModuleGrant("leave")
P_VIEW_SELF = "leave.request.view_self"
P_CREATE = "leave.request.create"


class _WithPrincipal:
    def get_serializer_context(self):
        return {**super().get_serializer_context(), "principal": self.request.principal}


@extend_schema(parameters=[
    OpenApiParameter("mine", bool, description="Only the caller's own requests"),
    OpenApiParameter("status", str, description="Filter by status")])
class LeaveRequestListView(_WithPrincipal, generics.ListAPIView):
    """Employees see their own requests; reviewers see the queue."""

    permission_classes = [MODULE, HasPermission(P_VIEW_SELF, P_VIEW, P_REVIEW, P_APPROVE)]
    serializer_class = s.LeaveRequestSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveRequest.objects.none()
        p = self.request.principal
        mine = self.request.query_params.get("mine") in ("1", "true")
        qs = selectors.own_requests(p) if mine else selectors.visible_requests(p)
        if wanted := self.request.query_params.get("status"):
            qs = qs.filter(status__in=wanted.split(","))
        return qs.prefetch_related("transitions")


@extend_schema(request=s.LeaveApplySerializer, responses={201: s.LeaveRequestSerializer})
class ApplyView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]

    def post(self, request):
        payload = s.LeaveApplySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        req = service.submit(request.principal, **payload.validated_data)
        return Response(
            s.LeaveRequestSerializer(req, context={"principal": request.principal}).data,
            status=status.HTTP_201_CREATED)


class LeaveRequestDetailView(_WithPrincipal, generics.RetrieveAPIView):
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF, P_VIEW, P_REVIEW, P_APPROVE)]
    serializer_class = s.LeaveRequestSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveRequest.objects.none()
        return selectors.visible_requests(self.request.principal)


@extend_schema(request=s.LeaveTransitionSerializer, responses=s.LeaveRequestSerializer)
class TransitionView(APIView):
    """Recommend, approve, reject or withdraw. Who may do which is decided by
    the state machine, not here."""

    permission_classes = [MODULE]

    def post(self, request, pk):
        payload = s.LeaveTransitionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        req = service.transition(request_id=pk, principal=request.principal,
                                 **payload.validated_data)
        return Response(
            s.LeaveRequestSerializer(req, context={"principal": request.principal}).data)


@extend_schema(parameters=[OpenApiParameter("year", int)],
               responses=s.LeaveBalanceSerializer(many=True))
class BalanceView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    def get(self, request):
        raw = request.query_params.get("year") or timezone.localdate().year
        try:
            year = int(raw)
        except ValueError as exc:
            raise BadRequestError("year must be a number.") from exc
        rows = service.balances(request.principal, year)
        return Response(s.LeaveBalanceSerializer(rows, many=True).data)
