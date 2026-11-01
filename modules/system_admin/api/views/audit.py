"""Audit and dashboard views for System Admin module."""
import csv
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasPermission
from modules.system_admin.api.permissions import IsSuperAdminOperator
from modules.system_admin.api.serializers import AuditLogReadSerializer
from modules.system_admin.selectors import (
    get_admin_dashboard_metrics,
    list_audit_logs,
)


class AuditLogListView(APIView):
    permission_classes = [IsSuperAdminOperator, HasPermission("system_admin.audit.view")]

    def get(self, request):
        actor = request.query_params.get("actor")
        action = request.query_params.get("action")
        result = request.query_params.get("result")

        logs = list_audit_logs(actor_username=actor, action=action, result=result)
        return Response(AuditLogReadSerializer(logs[:200], many=True).data)


class AuditReportExportView(APIView):
    """AFR-SA-065C: Export audit report to CSV format."""
    permission_classes = [IsSuperAdminOperator, HasPermission("system_admin.audit.report")]

    def get(self, request):
        logs = list_audit_logs()[:1000]

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="super_admin_audit_log.csv"'

        writer = csv.writer(response)
        writer.writerow(["ID", "Timestamp", "Actor ID", "Actor Username", "Action", "Result", "Target Type", "Target ID", "Reason"])
        for l in logs:
            writer.writerow([
                l.id,
                l.timestamp.isoformat(),
                l.actor_user_id,
                l.actor_username,
                l.action,
                l.result,
                l.target_type,
                l.target_id,
                l.reason,
            ])

        return response


class AdminDashboardView(APIView):
    """CFR-SA-018, AFR-SA-066: Super Admin Dashboard metrics."""
    permission_classes = [IsSuperAdminOperator, HasPermission("system_admin.audit.view")]

    def get(self, request):
        metrics = get_admin_dashboard_metrics()
        return Response(metrics)
