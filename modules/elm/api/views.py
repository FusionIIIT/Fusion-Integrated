from __future__ import annotations

from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api import csrf
from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from fusion_auth.client import IamUnavailable
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.placement.api import serializers as s
from modules.placement.api.permissions import ScopedCollection
from modules.placement.authentication import (
    COOKIE_NAME as RECRUITER_COOKIE,
)
from modules.placement.authentication import (
    COOKIE_PATH as RECRUITER_COOKIE_PATH,
)
from modules.placement.authentication import (
    RecruiterAuthentication,
)
from modules.placement.models import (
    PlacementPolicy,
    RecruiterAccount,
)
from modules.placement.selectors import scoping
from modules.placement.services import announcements as announcement_service
from modules.placement.services import applications as application_service
from modules.placement.services import candidates
from modules.placement.services import companies as company_service
from modules.placement.services import interviews as interview_service
from modules.placement.services import offers as offer_service
from modules.placement.services import postings as posting_service
from modules.placement.services import recruiters as recruiter_service
from modules.placement.services import stats as stats_service

MODULE = HasModuleGrant("elm")

P_VIEW_LEAVE_REQUESTS = "elm.leave_request.view"
P_CREATE_LEAVE_REQUESTS = "elm.leave_request.create"
P_UPDATE_LEAVE_REQUESTS = "elm.leave_request.update"
P_DELETE_LEAVE_REQUESTS = "elm.leave_request.delete"
P_VIEW_LEAVE_TYPES = "elm.leave_type.view"
P_CREATE_LEAVE_TYPES = "elm.leave_type.create"
P_UPDATE_LEAVE_TYPES = "elm.leave_type.update"
P_DELETE_LEAVE_TYPES = "elm.leave_type.delete"
P_VIEW_LEAVE_BALANCES = "elm.leave_balance.view"
P_UPDATE_LEAVE_BALANCES = "elm.leave_balance.update"

def _actor(request):
    return getattr(request, "principal", None)

def _int_param(params, name):
    raw = params.get(name)
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise BadRequestError(f"{name} must be a number.",
                              code="invalid_filter") from exc

def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    hops = api_settings.NUM_PROXIES or 0
    if forwarded and hops:
        addrs = [a.strip() for a in forwarded.split(",") if a.strip()]
        if addrs:
            return addrs[-min(hops, len(addrs))]
    return request.META.get("REMOTE_ADDR")

class _Scoped(generics.GenericAPIView):
    authentication_classes = [RecruiterAuthentication,
                              *generics.GenericAPIView.authentication_classes]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["actor"] = _actor(self.request)
        return ctx

class LeaveRequestListView(_Scoped, generics.ListCreateAPIView):
    serializer_class = s.LeaveRequestSerializer
    permission_classes = [MODULE, ScopedCollection(P_VIEW_LEAVE_REQUESTS, P_CREATE_LEAVE_REQUESTS)]

    def get_queryset(self):
        return scoping.leave_requests_for(_actor(self.request))

    def create(self, request, *args, **kwargs):
        actor = _actor(request)
        payload = s.LeaveRequestWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)
        leave_request = application_service.create(
            actor=actor, **data)
        return Response(s.LeaveRequestSerializer(leave_request).data,
                        status=status.HTTP_201_CREATED)

class LeaveRequestDetailView(_Scoped, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = s.LeaveRequestSerializer
    permission_classes = [MODULE, ScopedCollection(P_VIEW_LEAVE_REQUESTS, P_UPDATE_LEAVE_REQUESTS, P_DELETE_LEAVE_REQUESTS)]

    def get_queryset(self):
        return scoping.leave_requests_for(_actor(self.request))

class LeaveTypeListView(_Scoped, generics.ListCreateAPIView):
    serializer_class = s.LeaveTypeSerializer
    permission_classes = [MODULE, ScopedCollection(P_VIEW_LEAVE_TYPES, P_CREATE_LEAVE_TYPES)]

    def get_queryset(self):
        return scoping.leave_types_for(_actor(self.request))

    def create(self, request, *args, **kwargs):
        actor = _actor(request)
        payload = s.LeaveTypeWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)
        leave_type = application_service.create(
            actor=actor, **data)
        return Response(s.LeaveTypeSerializer(leave_type).data,
                        status=status.HTTP_201_CREATED)

class LeaveTypeDetailView(_Scoped, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = s.LeaveTypeSerializer
    permission_classes = [MODULE, ScopedCollection(P_VIEW_LEAVE_TYPES, P_UPDATE_LEAVE_TYPES, P_DELETE_LEAVE_TYPES)]

    def get_queryset(self):
        return scoping.leave_types_for(_actor(self.request))

class LeaveBalanceListView(_Scoped, generics.ListAPIView):
    serializer_class = s.LeaveBalanceSerializer
    permission_classes = [MODULE, ScopedCollection(P_VIEW_LEAVE_BALANCES)]

    def get_queryset(self):
        return scoping.leave_balances_for(_actor(self.request))

class LeaveBalanceDetailView(_Scoped, generics.RetrieveUpdateAPIView):
    serializer_class = s.LeaveBalanceSerializer
    permission_classes = [MODULE, ScopedCollection(P_VIEW_LEAVE_BALANCES, P_UPDATE_LEAVE_BALANCES)]

    def get_queryset(self):
        return scoping.leave_balances_for(_actor(self.request))
