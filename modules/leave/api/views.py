from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.api.serializers import LeaveRequestCreateSerializer, LeaveRequestSerializer
from modules.leave.selectors.requests import visible_requests
from modules.leave.services import requests as service

MODULE = HasModuleGrant("leave")
P_VIEW_SELF = "leave.request.view_self"
P_CREATE = "leave.request.create"
P_DELETE = "leave.request.delete"


@extend_schema(responses=LeaveRequestSerializer(many=True))
class LeaveRequestListCreateView(APIView):
    def get_permissions(self):
        permission = P_VIEW_SELF if self.request.method == "GET" else P_CREATE
        return [MODULE(), HasPermission(permission)()]

    def get(self, request):
        rows = visible_requests(request.principal)
        return Response({"results": LeaveRequestSerializer(rows, many=True).data})

    @extend_schema(request=LeaveRequestCreateSerializer,
                   responses={201: LeaveRequestSerializer})
    def post(self, request):
        payload = LeaveRequestCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = service.create(actor=request.principal, **payload.validated_data)
        return Response(LeaveRequestSerializer(row).data, status=status.HTTP_201_CREATED)


class LeaveRequestWithdrawView(APIView):
    permission_classes = [MODULE, HasPermission(P_DELETE)]

    @extend_schema(responses=LeaveRequestSerializer)
    def post(self, request, pk: int):
        row = service.withdraw(actor=request.principal, request_id=pk)
        return Response(LeaveRequestSerializer(row).data)
