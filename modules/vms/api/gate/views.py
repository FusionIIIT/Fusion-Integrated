"""Gate validate and check-out. TODO lane B: replace with services/gate.py."""
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasPermission
from modules.vms.api.gate.serializers import (
    GateCheckoutSerializer, GateValidateSerializer,
)
from modules.vms.services import legacy_flow


class GateValidateView(APIView):
    permission_classes = [HasPermission("vms.gate.operate")]

    def post(self, request):
        ser = GateValidateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            request_id = legacy_flow.gate_validate(actor=request.principal,
                                                   data=ser.validated_data)
        except legacy_flow.GateDenied as denied:
            return Response({"detail": denied.reason}, status=403)
        if request_id is None:
            return Response({"detail": "Pass not found."}, status=403)
        return Response({"detail": "Checked in.", "visit_request_id": request_id})


class GateCheckoutView(APIView):
    permission_classes = [HasPermission("vms.gate.operate")]

    def post(self, request):
        ser = GateCheckoutSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        legacy_flow.gate_checkout(actor=request.principal,
                                  qr_token=ser.validated_data["qr_token"])
        return Response({"detail": "Checked out."})
