"""Visit extension endpoints (UC-034; BW-VMS-23)."""
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasPermission
from modules.vms.api.extensions.serializers import (
    ExtensionCreateSerializer,
    ExtensionDecisionSerializer,
    ExtensionSerializer,
)
from modules.vms.services import extensions

HOST_OR_ADMIN = ("vms.request.decide", "vms.extension.decide")


class ExtensionListCreateView(APIView):
    permission_classes = [HasPermission(*HOST_OR_ADMIN)]

    def get(self, request):
        qs = extensions.list_extensions(actor=request.principal,
                                        status=request.query_params.get("status"))
        return Response(ExtensionSerializer(qs[:200], many=True).data)

    def post(self, request):
        ser = ExtensionCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ext = extensions.request_extension(requester=request.principal, **ser.validated_data)
        return Response(ExtensionSerializer(ext).data, status=201)


class ExtensionDetailView(APIView):
    permission_classes = [HasPermission(*HOST_OR_ADMIN)]

    def get(self, request, pk):
        ext = extensions.get_extension(actor=request.principal, extension_id=pk)
        return Response(ExtensionSerializer(ext).data)


class ExtensionDecisionView(APIView):
    permission_classes = [HasPermission("vms.extension.decide")]

    def post(self, request, pk):
        ser = ExtensionDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ext = extensions.decide_extension(
            admin_actor=request.principal, extension_id=pk,
            decision=ser.validated_data["decision"], note=ser.validated_data["note"])
        return Response(ExtensionSerializer(ext).data)
