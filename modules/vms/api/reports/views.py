"""Report endpoints (VMS-UC-007). GET only: reports never change data."""
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.csv import stream
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.vms.api.reports import serializers as s
from modules.vms.services import reports

MODULE = HasModuleGrant("vms")


def _params(request) -> dict:
    q = s.ReportQuery(data=request.query_params)
    q.is_valid(raise_exception=True)
    return q.params()


class ReportCatalogueView(APIView):
    permission_classes = [MODULE, HasPermission("vms.report.view")]
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        return Response(reports.catalogue(request.principal))


class ReportRunView(APIView):
    permission_classes = [MODULE, HasPermission("vms.report.view")]
    http_method_names = ["get", "head", "options"]

    def get(self, request, key):
        return Response(reports.run(request.principal, key, _params(request)))


class ReportExportView(APIView):
    permission_classes = [MODULE, HasPermission("vms.report.export")]
    http_method_names = ["get", "head", "options"]

    def get(self, request, key):
        fmt = request.query_params.get("fmt", "csv")
        out = reports.export(request.principal, key, _params(request), fmt)
        return stream(filename=out["filename"], header=out["header"], rows=out["rows"])
