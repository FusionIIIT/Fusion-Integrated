"""Host side of a request: assigned list, decision, bulk decision, pre-authorisations,
and the Admin urgent exception (UC-035)."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.pagination import CursorPagination
from fusion_auth.permissions import HasPermission
from modules.vms.api.host import serializers as s
from modules.vms.selectors import requests as selectors
from modules.vms.services import approval, preauth


def _page(view, request, rows, serializer):
    paginator = CursorPagination()
    page = paginator.paginate_queryset(rows, request, view=view)
    return paginator.get_paginated_response(serializer(page, many=True).data)


class HostRequestListView(APIView):
    permission_classes = [HasPermission("vms.request.view_assigned")]

    def get(self, request):
        rows = selectors.host_requests(
            request.principal.user_id, request.query_params.get("status") or None)
        return _page(self, request, rows, s.HostRequestSerializer)


class HostDecisionView(APIView):
    permission_classes = [HasPermission("vms.request.decide")]

    def post(self, request, pk):
        ser = s.DecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        vr, vp = approval.decide(
            host_actor=request.principal, request_id=pk, decision=d["decision"],
            note=d["note"], zones=d.get("zones"), window=d.get("window"))
        if vp is None:
            return Response(s.HostRequestSerializer(vr).data)
        return Response(s.VisitPassSerializer(vp).data, status=status.HTTP_201_CREATED)


class HostBulkDecisionView(APIView):
    permission_classes = [HasPermission("vms.request.decide")]

    def post(self, request):
        ser = s.BulkDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        results = approval.bulk_decide(host_actor=request.principal, ids=d["ids"],
                                       decision=d["decision"], note=d["note"])
        return Response({"results": results})


class UrgentDecisionView(APIView):
    """Admin exception for a same-day urgent request. The IAM permission is
    checked here, the time-bound Admin role in the service."""
    permission_classes = [HasPermission("vms.urgent.decide")]

    def post(self, request, pk):
        ser = s.UrgentDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vr = approval.decide_urgent(admin_actor=request.principal, request_id=pk,
                                    **ser.validated_data)
        return Response(s.HostRequestSerializer(vr).data)


class PreAuthorizationListCreateView(APIView):
    permission_classes = [HasPermission("vms.preauth.manage")]

    def get(self, request):
        rows = selectors.host_pre_authorizations(
            request.principal.user_id,
            active_only=request.query_params.get("active") in ("1", "true"))
        return _page(self, request, rows, s.PreAuthorizationSerializer)

    def post(self, request):
        ser = s.PreAuthorizationCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        pa = preauth.create(host_actor=request.principal, data=ser.validated_data)
        return Response(s.PreAuthorizationSerializer(pa).data,
                        status=status.HTTP_201_CREATED)


class PreAuthorizationRevokeView(APIView):
    permission_classes = [HasPermission("vms.preauth.manage")]

    def post(self, request, pk):
        pa = preauth.revoke(host_actor=request.principal, preauth_id=pk)
        return Response(s.PreAuthorizationSerializer(pa).data)

