"""Check-out, termination and roster endpoints (lane D)."""
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.vms.api.visit.serializers import (
    CheckOutSerializer,
    SelfCheckOutSerializer,
    TerminateSerializer,
)
from modules.vms.auth import IsVisitorSession, VisitorSessionAuthentication
from modules.vms.selectors import roster
from modules.vms.services import checkout, termination

MODULE = HasModuleGrant("vms")


class CheckOutView(APIView):
    permission_classes = [MODULE, HasPermission("vms.gate.operate")]

    def post(self, request):
        ser = CheckOutSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        log = checkout.gate_checkout(security_actor=request.principal,
                                     credential=ser.validated_data["credential"],
                                     gate_id=ser.validated_data["gate_id"])
        return Response({"detail": "Checked out.", "visit_request_id":
                         log.visit_pass.visit_request_id})


class SelfCheckOutView(APIView):
    authentication_classes = [VisitorSessionAuthentication]
    permission_classes = [IsVisitorSession]

    def post(self, request):
        ser = SelfCheckOutSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        log = checkout.self_checkout(session=request.principal,
                                     pass_token=ser.validated_data["pass_token"])
        return Response({"detail": "Checked out.", "visit_request_id":
                         log.visit_pass.visit_request_id})


class TerminatePassView(APIView):
    permission_classes = [MODULE, HasPermission("vms.pass.terminate")]

    def post(self, request, pk):
        ser = TerminateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vp = termination.terminate(actor=request.principal, pass_id=pk,
                                   reason=ser.validated_data["reason"])
        return Response({"detail": "Pass terminated.", "pass_id": vp.pk,
                         "terminated_at": vp.terminated_at})


class OnSiteView(APIView):
    permission_classes = [MODULE, HasPermission("vms.monitor.view")]

    def get(self, request):
        zone = request.query_params.get("zone_id")
        rows = roster.on_site(zone=int(zone) if zone and zone.isdigit() else None)[:500]
        return Response([{
            "pass_id": p.pk, "visit_request_id": p.visit_request_id,
            "visitor_name": p.visit_request.visitor.full_name,
            "host_user_id": p.visit_request.host_user_id,
            "pass_type": p.pass_type, "valid_until": p.valid_until,
            "pass_active": p.is_active, "zone_id": p.last_zone_id,
        } for p in rows])
