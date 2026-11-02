"""Pre-registration. TODO lane A / decision D-1: move to visitor sessions
(`VisitorSessionAuthentication`); until then any authenticated principal may
file and list, because the permission that used to guard this was removed."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import IsAuthenticatedPrincipal
from modules.vms.api.visitor.serializers import (
    PreRegistrationSerializer, VisitRequestSerializer,
)
from modules.vms.services import legacy_flow
from modules.vms.services.common import scope


class PreRegistrationView(APIView):
    permission_classes = [IsAuthenticatedPrincipal]

    def get(self, request):
        rows = (scope.requests_as_visitor(request.principal)
                .select_related("visitor").order_by("-created_at"))
        return Response({"results": VisitRequestSerializer(rows, many=True).data})

    def post(self, request):
        ser = PreRegistrationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vr = legacy_flow.pre_register(actor=request.principal, data=ser.validated_data)
        return Response(VisitRequestSerializer(vr).data, status=status.HTTP_201_CREATED)
