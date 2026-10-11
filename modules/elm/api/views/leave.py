from __future__ import annotations

from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from core.api import csrf
from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from fusion_auth.client import IamUnavailable
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.directory import contracts as directory
from modules.elm.api import serializers as s
from modules.elm.models import Leave, LeaveCategory
from modules.elm.selectors import scoping
from modules.elm.services import leaves

MODULE = HasModuleGrant("elm")

P_VIEW_LEAVE_REQUESTS = "elm.leave_request.view"
P_MANAGE_LEAVE_REQUESTS = "elm.leave_request.manage"


def _actor(request):
    return getattr(request, "principal", None)


class LeaveListView(generics.ListAPIView):
    serializer_class = s.LeaveRequestSerializer
    permission_classes = [MODULE]

    def get_queryset(self):
        qs = scoping.leaves_for(_actor(self.request))
        user_id = self.request.query_params.get("user")
        status = self.request.query_params.get("status")
        if user_id:
            qs = qs.filter(user_id=user_id)
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("-created_at")

    def list(self, request, *args, **kwargs):
        actor = _actor(request)
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        rows = page if page is not None else list(queryset)

        # One batched directory call per page, and none for a student's own list.
        context = {"actor": actor, "view": self, "request": request}
        if scoping.is_staff(actor):
            users = [row.user_id for row in rows]
            user_data = directory.get_user_details(users)
            for row, details in zip(rows, user_data):
                row.user_details = details

        return self.get_paginated_response(self.get_serializer(rows).data)


class LeaveDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = s.LeaveRequestSerializer
    permission_classes = [MODULE]

    def get_queryset(self):
        return scoping.leaves_for(_actor(self.request))

    def update(self, request, *args, **kwargs):
        actor = _actor(request)
        payload = s.LeaveRequestWriteSerializer(data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)

        leave = leaves.update(
            leave_id=kwargs["pk"], actor=actor,
            scope=self.get_queryset(), **data)
        return Response(s.LeaveRequestSerializer(leave).data)


@extend_schema(request=None, responses=s.LeaveRequestSerializer)
class LeaveCreateView(generics.CreateAPIView):
    serializer_class = s.LeaveRequestWriteSerializer
    permission_classes = [MODULE]

    def create(self, request, *args, **kwargs):
        actor = _actor(request)
        payload = s.LeaveRequestWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)

        leave = leaves.create(
            user_id=actor.user_id, actor=actor,
            **data)
        return Response(s.LeaveRequestSerializer(leave).data)


@extend_schema(responses=s.EligibilityVerdictSerializer)
class LeaveEligibilityView(APIView):
    """PC-UC-003's precondition, made visible to the student."""

    permission_classes = [MODULE]

    def get(self, request, pk):
        actor = _actor(request)
        leave = scoping.leaves_for(actor).filter(pk=pk).first()
        if leave is None:
            raise NotFoundError("No such leave request.")
        policy = LeaveCategory.objects.filter(
            name=leave.leave_type).first()
        if policy is None:
            raise ConflictError("No leave category for this type.",
                                code="policy_missing")
        try:
            verdict = leaves.evaluate_for(
                leave=leave, user_id=actor.user_id, policy=policy)
        except IamUnavailable as exc:
            # A 503 is truthful; "ineligible" would be a lie acted on.
            return Response(
                {"error": {"code": "identity_service_unavailable",
                           "message": f"Academic records are unavailable: {exc}",
                           "details": [], "request_id": ""}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(verdict)


@extend_schema(responses=s.LeaveRequestSerializer)
class LeaveCancelView(APIView):
    permission_classes = [MODULE]

    def post(self, request, pk):
        actor = _actor(request)
        leave = leaves.cancel(
            leave_id=pk, actor=actor,
            scope=scoping.leaves_for(actor))
        return Response(s.LeaveRequestSerializer(leave).data)


@extend_schema(responses=s.LeaveRequestSerializer)
class LeaveExtendView(APIView):
    permission_classes = [MODULE]

    def post(self, request, pk):
        actor = _actor(request)
        leave = leaves.extend(
            leave_id=pk, actor=actor,
            scope=scoping.leaves_for(actor))
        return Response(s.LeaveRequestSerializer(leave).data)


@extend_schema(responses=s.LeaveRequestSerializer)
class LeaveResumeView(APIView):
    permission_classes = [MODULE]

    def post(self, request, pk):
        actor = _actor(request)
        leave = leaves.resume(
            leave_id=pk, actor=actor,
            scope=scoping.leaves_for(actor))
        return Response(s.LeaveRequestSerializer(leave).data)


@extend_schema(responses=s.LeaveRequestSerializer)
class LeaveWithdrawView(APIView):
    permission_classes = [MODULE]

    def post(self, request, pk):
        actor = _actor(request)
        leave = leaves.withdraw(
            leave_id=pk, actor=actor,
            scope=scoping.leaves_for(actor))
        return Response(s.LeaveRequestSerializer(leave).data)


@extend_schema(responses=s.LeaveRequestSerializer)
class LeaveApproveView(APIView):
    permission_classes = [MODULE]

    def post(self, request, pk):
        actor = _actor(request)
        leave = leaves.approve(
            leave_id=pk, actor=actor,
            scope=scoping.leaves_for(actor))
        return Response(s.LeaveRequestSerializer(leave).data)


@extend_schema(responses=s.LeaveRequestSerializer)
class LeaveRejectView(APIView):
    permission_classes = [MODULE]

    def post(self, request, pk):
        actor = _actor(request)
        leave = leaves.reject(
            leave_id=pk, actor=actor,
            scope=scoping.leaves_for(actor))
        return Response(s.LeaveRequestSerializer(leave).data)

