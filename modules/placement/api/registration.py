"""Registering for a season (rules 1, 20, 21).

A student registers themselves and can always ask what route is open to them.
The two routes that turn on a payment — rule 20's late fee and rule 21's
re-registration — are staff endpoints, because both require the office to have
seen a challan.

`user_id` is never read from the body on the self-service paths; it comes from
the credential, or a student could register or withdraw somebody else.
"""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.placement.api import serializers as s
from modules.placement.models import PlacementRegistration
from modules.placement.services import registration as service

MODULE = HasModuleGrant("placement_cell")
P_SELF = "placement_cell.registration.self"
P_MANAGE = "placement_cell.registration.manage"


def _actor(request):
    return getattr(request, "principal", None)


def _terms_payload(terms) -> dict:
    return {"route": terms.route.value, "reason": terms.reason,
            "message": terms.message, "fee": terms.fee,
            "allowed": terms.allowed}


@extend_schema(responses=s.RegistrationTermsSerializer)
class MyRegistrationTermsView(APIView):
    """Can I register, and on what terms? Read-only."""

    permission_classes = [MODULE, HasPermission(P_SELF)]

    def get(self, request):
        season = request.query_params.get("season")
        if not season:
            from core.api.exceptions import BadRequestError
            raise BadRequestError("season is required.", code="season_required")
        terms = service.assess(season=season, user_id=_actor(request).user_id)
        return Response(_terms_payload(terms))


@extend_schema(responses=s.RegistrationSerializer(many=True))
class MyRegistrationsView(APIView):
    """The caller's own registrations. Scoped by the credential, not a filter."""

    permission_classes = [MODULE, HasPermission(P_SELF)]

    def get(self, request):
        rows = (PlacementRegistration.objects
                .filter(user_id=_actor(request).user_id)
                .select_related("policy").order_by("-created_at"))
        return Response({"results": s.RegistrationSerializer(rows, many=True).data})

    @extend_schema(request=s.RegisterSerializer,
                   responses={201: s.RegistrationSerializer})
    def post(self, request):
        payload = s.RegisterSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        registration = service.register(
            season=payload.validated_data["season"],
            user_id=_actor(request).user_id)
        return Response(s.RegistrationSerializer(registration).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(request=s.OptOutSerializer, responses=s.RegistrationSerializer)
class MyOptOutView(APIView):
    """Withdrawing. Rule 21 makes coming back cost a fee and allows it once,
    so the client should say so before confirming."""

    permission_classes = [MODULE, HasPermission(P_SELF)]

    def post(self, request):
        payload = s.OptOutSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        registration = service.opt_out(
            user_id=_actor(request).user_id, **payload.validated_data)
        return Response(s.RegistrationSerializer(registration).data)


@extend_schema(request=s.FeeApprovalSerializer,
               responses=s.RegistrationSerializer)
class LateRegistrationView(APIView):
    """Rule 20 — the office approves a late registration against a challan."""

    permission_classes = [MODULE, HasPermission(P_MANAGE)]

    def post(self, request):
        payload = s.FeeApprovalSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        registration = service.approve_late(actor=_actor(request),
                                            **payload.validated_data)
        return Response(s.RegistrationSerializer(registration).data)


@extend_schema(request=s.FeeApprovalSerializer,
               responses=s.RegistrationSerializer)
class ReRegistrationView(APIView):
    """Rule 21 — once only, at the Chairperson's discretion."""

    permission_classes = [MODULE, HasPermission(P_MANAGE)]

    def post(self, request):
        payload = s.FeeApprovalSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        registration = service.reregister(actor=_actor(request),
                                          **payload.validated_data)
        return Response(s.RegistrationSerializer(registration).data)
