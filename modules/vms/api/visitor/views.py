"""Visitor-facing endpoints. Visitors are not IAM principals (decision D-1): the
login endpoints are anonymous and throttled, everything else needs the
`vms_visitor` session cookie (`VisitorSessionAuthentication`)."""
from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from core.api import csrf
from core.api.exceptions import ConflictError, NotFoundError
from core.api.pagination import CursorPagination
from modules.vms.api.visitor import serializers as s
from modules.vms.auth import (
    COOKIE_NAME,
    COOKIE_PATH,
    IsVisitorSession,
    VisitorSessionAuthentication,
)
from modules.vms.models import VisitRequest
from modules.vms.selectors import passes as pass_selectors
from modules.vms.selectors import requests as selectors
from modules.vms.services import registration, visitor_session


class VisitorLoginThrottle(AnonRateThrottle):
    """Per-IP limit on OTP traffic; the rate is DEFAULT_THROTTLE_RATES["vms_visitor_login"]."""
    scope = "vms_visitor_login"


class _VisitorView(APIView):
    authentication_classes = [VisitorSessionAuthentication]
    permission_classes = [IsVisitorSession]


class OtpRequestView(APIView):
    authentication_classes: list = []
    permission_classes: list = []
    throttle_classes = [VisitorLoginThrottle]

    def post(self, request):
        ser = s.OtpRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        visitor_session.request_otp(email=ser.validated_data["email"])
        # Same answer whether or not the address was known.
        return Response({"detail": "If the address is valid, a code was sent."},
                        status=status.HTTP_202_ACCEPTED)


class OtpVerifyView(APIView):
    authentication_classes: list = []
    permission_classes: list = []
    throttle_classes = [VisitorLoginThrottle]

    def post(self, request):
        ser = s.OtpVerifySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        raw, session = visitor_session.verify(**ser.validated_data)
        response = Response({"expires_at": session.expires_at,
                             "csrf_token": csrf.token_for(raw)})
        response.set_cookie(
            COOKIE_NAME, raw,
            max_age=int((session.expires_at - timezone.now()).total_seconds()),
            httponly=True, samesite="Lax", secure=not settings.DEBUG, path=COOKIE_PATH)
        return response


class PreRegistrationView(_VisitorView):
    def post(self, request):
        ser = s.PreRegistrationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vr = registration.submit(session_visitor=request.visitor, data=ser.validated_data)
        code = (status.HTTP_202_ACCEPTED
                if vr.status == VisitRequest.Status.AWAITING_ADMIN
                else status.HTTP_201_CREATED)
        return Response(s.VisitRequestSerializer(vr).data, status=code)


class RequestListView(_VisitorView):
    def get(self, request):
        rows = selectors.visitor_requests(
            request.visitor.pk, request.query_params.get("status") or None)
        paginator = CursorPagination()
        page = paginator.paginate_queryset(rows, request, view=self)
        return paginator.get_paginated_response(
            s.VisitRequestSerializer(page, many=True).data)


def _own_request(request, pk):
    vr = selectors.visitor_request(request.visitor.pk, pk)
    if vr is None:
        raise NotFoundError()
    return vr


class RequestDetailView(_VisitorView):
    @extend_schema(operation_id="vms_visitor_requests_detail")
    def get(self, request, pk):
        return Response(s.VisitRequestDetailSerializer(_own_request(request, pk)).data)


class RequestPassView(_VisitorView):
    """UC-012: only for an approved request with an active pass; marks it viewed."""

    def get(self, request, pk):
        vr = _own_request(request, pk)
        vp = pass_selectors.visible_pass(vr)
        if vp is None:
            raise ConflictError("No active pass is available for this request.",
                                code="pass_not_available")
        registration.record_pass_viewed(visitor=request.visitor, visit_request=vr,
                                        visit_pass=vp)
        return Response(s.PassSerializer(vp).data)
