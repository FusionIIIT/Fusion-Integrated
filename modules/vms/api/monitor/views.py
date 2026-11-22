"""Live monitoring endpoints. Thin: parse, call services/monitor.py, shape."""
from django.utils.dateparse import parse_datetime
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.vms.api.monitor import serializers as s
from modules.vms.services import monitor as svc

MODULE = HasModuleGrant("vms")


def _int(request, name):
    raw = request.query_params.get(name)
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except ValueError:
        raise BadRequestError(f"{name} must be an integer.") from None


class DashboardView(APIView):
    permission_classes = [MODULE, HasPermission("vms.monitor.view")]

    def get(self, request):
        return Response(svc.dashboard(actor=request.principal, zone_id=_int(request, "zone_id")))


class OnSiteView(APIView):
    permission_classes = [MODULE, HasPermission("vms.monitor.view")]

    def get(self, request):
        rows = svc.on_site(actor=request.principal, zone_id=_int(request, "zone_id"))
        return Response({"count": len(rows), "results": s.OnSiteSerializer(rows, many=True).data})


class MovementsView(APIView):
    permission_classes = [MODULE, HasPermission("vms.monitor.view")]

    def get(self, request):
        since = request.query_params.get("since")
        if since:
            since = parse_datetime(since)
            if since is None:
                raise BadRequestError("since must be an ISO 8601 datetime.")
        rows = svc.movements(actor=request.principal, pass_id=_int(request, "pass_id"),
                             zone_id=_int(request, "zone_id"), since=since or None)
        return Response({"results": s.MovementSerializer(rows, many=True).data})


class OutOfBoundsView(APIView):
    permission_classes = [MODULE, HasPermission("vms.monitor.view")]

    def get(self, request):
        rows = svc.out_of_bounds(actor=request.principal)
        data = s.OutOfBoundsSerializer(rows, many=True).data
        return Response({"count": len(rows), "results": data})
