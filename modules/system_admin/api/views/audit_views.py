"""Audit log and security monitoring views."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.system_admin.api.serializers import (
    FailedLoginLogSerializer,
    SystemAuditLogSerializer,
)
from modules.system_admin.selectors.audit_selectors import (
    list_audit_logs,
    list_failed_logins,
)

MODULE = HasModuleGrant("system_admin")


class AuditLogListView(APIView):
    permission_classes = [MODULE, HasPermission("system_admin.audit.view")]

    @extend_schema(responses={200: SystemAuditLogSerializer(many=True)})
    def get(self, request):
        action = request.query_params.get("action")
        target_id = request.query_params.get("target_id")
        result = request.query_params.get("result")
        actor_id_param = request.query_params.get("actor_id")
        actor_id = int(actor_id_param) if actor_id_param else None

        limit = min(int(request.query_params.get("limit", 100)), 200)
        offset = max(int(request.query_params.get("offset", 0)), 0)

        logs, total = list_audit_logs(
            actor_id=actor_id,
            action=action,
            target_id=target_id,
            result=result,
            limit=limit,
            offset=offset,
        )
        return Response({
            "results": SystemAuditLogSerializer(logs, many=True).data,
            "total": total,
            "limit": limit,
            "offset": offset,
        })


class FailedLoginListView(APIView):
    permission_classes = [MODULE, HasPermission("system_admin.audit.view")]

    @extend_schema(responses={200: FailedLoginLogSerializer(many=True)})
    def get(self, request):
        username = request.query_params.get("username")
        limit = min(int(request.query_params.get("limit", 50)), 100)
        logs = list_failed_logins(username=username, limit=limit)
        return Response(FailedLoginLogSerializer(logs, many=True).data)
