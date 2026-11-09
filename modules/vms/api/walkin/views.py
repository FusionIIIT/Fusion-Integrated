"""Walk-in registration and approval endpoints (lane D; BW-VMS-06/07/08)."""
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.vms.api.walkin.serializers import (
    WalkinDecisionSerializer,
    WalkinRegisterSerializer,
    request_payload,
)
from modules.vms.services import walkin

MODULE = HasModuleGrant("vms")


class WalkinRegistrationsView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [HasPermission("vms.walkin.register")()]
        return [HasPermission("vms.walkin.register", "vms.walkin.contingency_decide")()]

    def get(self, request):
        qs = walkin.list_registrations(actor=request.principal,
                                       status=request.query_params.get("status"))
        return Response([request_payload(vr) for vr in qs[:200]])

    def post(self, request):
        ser = WalkinRegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = dict(ser.validated_data)
        host = data.pop("host_user_id")
        vr = walkin.register(security_actor=request.principal, data=data, host_user_id=host)
        return Response(request_payload(vr), status=201)


class WalkinHostDecisionView(APIView):
    permission_classes = [MODULE, HasPermission("vms.request.decide")]

    def post(self, request, pk):
        ser = WalkinDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vr, _ = walkin.host_decide_walkin(
            request.principal, pk, ser.validated_data["decision"], ser.validated_data["note"])
        return Response(request_payload(vr))


class WalkinContingencyView(APIView):
    permission_classes = [MODULE, HasPermission("vms.walkin.contingency_decide")]

    def post(self, request, pk):
        ser = WalkinDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vr, _ = walkin.contingency_decide(
            admin_actor=request.principal, request_id=pk,
            decision=ser.validated_data["decision"], note=ser.validated_data["note"])
        return Response(request_payload(vr))
