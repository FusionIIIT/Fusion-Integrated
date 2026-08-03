"""Conduct incidents and placement sanctions (rules 18, 19, 21).

Recording an incident and imposing a sanction are separate endpoints, because
they are separate decisions in the policy: rule 19 says a student "may be"
debarred and rule 21 vests it in the Chairperson. POSTing an incident returns
the recommendation and changes nothing else.
"""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.placement.api import serializers as s
from modules.placement.models import ConductIncident
from modules.placement.services import conduct as conduct_service

MODULE = HasModuleGrant("placement_cell")
P_DEBAR = "placement_cell.registration.debar"


def _actor(request):
    return getattr(request, "principal", None)


class IncidentListView(APIView):
    """GET  the incidents on record   POST a new one."""

    permission_classes = [MODULE, HasPermission(P_DEBAR)]

    @extend_schema(responses=s.ConductIncidentSerializer(many=True))
    def get(self, request):
        rows = ConductIncident.objects.select_related("posting")
        user_id = request.query_params.get("user_id")
        if user_id:
            rows = rows.filter(user_id=user_id)
        rows = rows.order_by("-created_at")[:200]
        return Response({
            "results": s.ConductIncidentSerializer(rows, many=True).data})

    @extend_schema(request=s.RecordIncidentSerializer,
                   responses={201: s.IncidentRecordedSerializer})
    def post(self, request):
        payload = s.RecordIncidentSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        incident, recommendation = conduct_service.record(
            actor=_actor(request), **payload.validated_data)
        return Response(
            {
                "incident": s.ConductIncidentSerializer(incident).data,
                "recommendation": {
                    "sanction": recommendation.sanction.value,
                    "rule": recommendation.rule,
                    "message": recommendation.message,
                    "automatic": recommendation.automatic,
                },
            },
            status=status.HTTP_201_CREATED)


@extend_schema(request=s.WaiveIncidentSerializer,
               responses=s.ConductIncidentSerializer)
class IncidentWaiveView(APIView):
    """Rule 19's written-notice exception."""

    permission_classes = [MODULE, HasPermission(P_DEBAR)]

    def post(self, request, pk):
        payload = s.WaiveIncidentSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        incident = conduct_service.waive(
            incident_id=pk, actor=_actor(request),
            reason=payload.validated_data["reason"])
        return Response(s.ConductIncidentSerializer(incident).data)


@extend_schema(request=s.ApplySanctionSerializer,
               responses=s.RegistrationSerializer)
class SanctionView(APIView):
    """Impose the sanction. The human decision the policy calls for."""

    permission_classes = [MODULE, HasPermission(P_DEBAR)]

    def post(self, request):
        payload = s.ApplySanctionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        registration = conduct_service.apply_sanction(
            actor=_actor(request), **payload.validated_data)
        return Response(s.RegistrationSerializer(registration).data)


@extend_schema(request=s.LiftSanctionSerializer,
               responses=s.RegistrationSerializer)
class SanctionLiftView(APIView):
    """Anything a human can impose, a human can undo."""

    permission_classes = [MODULE, HasPermission(P_DEBAR)]

    def post(self, request):
        payload = s.LiftSanctionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        registration = conduct_service.lift(
            actor=_actor(request), **payload.validated_data)
        return Response(s.RegistrationSerializer(registration).data)
