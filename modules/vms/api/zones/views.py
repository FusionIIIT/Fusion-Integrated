"""Zone access check and elevation endpoints."""
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasPermission
from modules.vms.api.zones import serializers as s
from modules.vms.selectors import gate as gate_sel
from modules.vms.services import zone_access
from modules.vms.services.common import authz

LIST_LIMIT = 200


class AccessCheckView(APIView):
    permission_classes = [HasPermission("vms.gate.operate")]

    def post(self, request):
        ser = s.AccessCheckSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        res = zone_access.check_zone(
            actor=request.principal, pass_id=d["pass_id"], zone_id=d["zone_id"],
            reader_id=d["reader_id"], gate_id=d.get("gate_id"), at=d.get("at"))
        body = {"allowed": res["allowed"], "visit_log_id": res["visit_log"].pk,
                "vip_override": res["vip_override"],
                "failures": [{"code": f.code, "rule": f.rule, "message": f.message}
                             for f in res["failures"]]}
        return Response(body, status=200 if res["allowed"] else 403)


class ElevationListCreateView(APIView):
    permission_classes = [HasPermission("vms.zone.elevate")]

    def get(self, request):
        authz.require_role(request.principal, "admin")
        pass_id = request.query_params.get("pass_id")
        rows = gate_sel.elevations(
            pass_id=int(pass_id) if pass_id and pass_id.isdigit() else None,
            active_only=request.query_params.get("active") in ("1", "true"))[:LIST_LIMIT]
        return Response({"results": s.ElevationSerializer(rows, many=True).data})

    def post(self, request):
        ser = s.ElevationCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        el = zone_access.grant_elevation(admin_actor=request.principal, **ser.validated_data)
        return Response(s.ElevationSerializer(el).data, status=201)


class ElevationRevokeView(APIView):
    permission_classes = [HasPermission("vms.zone.elevate")]

    def post(self, request, pk):
        el = zone_access.revoke_elevation(admin_actor=request.principal, elevation_id=pk)
        return Response(s.ElevationSerializer(el).data)
