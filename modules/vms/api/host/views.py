"""Host side of a request: pending list and the approve/reject decision."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasPermission
from modules.vms.api.host.serializers import (
    DecisionSerializer, HostRequestSerializer, VisitPassSerializer,
)
from modules.vms.models import VisitRequest
from modules.vms.services import legacy_flow
from modules.vms.services.common import scope


class HostPendingListView(APIView):
    permission_classes = [HasPermission("vms.request.decide")]

    def get(self, request):
        rows = (scope.requests_as_host(request.principal)
                .filter(status=VisitRequest.Status.PENDING)
                .select_related("visitor").order_by("scheduled_start"))
        return Response({"results": HostRequestSerializer(rows, many=True).data})


class HostDecisionView(APIView):
    permission_classes = [HasPermission("vms.request.decide")]

    def post(self, request, pk):
        ser = DecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        vr, vp = legacy_flow.decide(actor=request.principal, request_id=pk,
                                    decision=d["decision"], note=d["note"])
        if vp is None:
            return Response(HostRequestSerializer(vr).data)
        return Response(VisitPassSerializer(vp).data, status=status.HTTP_201_CREATED)
