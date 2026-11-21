from __future__ import annotations

import csv

from django.http import HttpResponse
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from core.api.pagination import CursorPagination
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.superadmin.api import serializers as s
from modules.superadmin.selectors import (
    archival as archival_sel,
)
from modules.superadmin.selectors import (
    audit as audit_sel,
)
from modules.superadmin.selectors import (
    config as config_sel,
)
from modules.superadmin.selectors import (
    purge as purge_sel,
)
from modules.superadmin.services import (
    archival as archival_svc,
)
from modules.superadmin.services import (
    config as config_svc,
)
from modules.superadmin.services import (
    historical_archive as hist_svc,
)
from modules.superadmin.services import (
    purge as purge_svc,
)


class UserArchivalPagination(CursorPagination):
    ordering = "-user_id"


MODULE = HasModuleGrant("superadmin")


class DashboardView(APIView):
    permission_classes = [MODULE, HasPermission("superadmin.dashboard.view")]

    @extend_schema(responses={200: s.DashboardSummarySerializer})
    def get(self, request):
        metrics = audit_sel.get_dashboard_metrics(request.principal)
        return Response(metrics)


class ArchivedUserListView(APIView):
    permission_classes = [MODULE]

    @extend_schema(responses={200: s.ArchivedUserSerializer(many=True)})
    def get(self, request):
        if not request.principal.has_permission("superadmin.archival.view"):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        status_filter = request.query_params.get("status")
        search = request.query_params.get("search")
        qs = archival_sel.list_archived_users(
            request.principal, status=status_filter, search=search
        )
        paginator = UserArchivalPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = s.ArchivedUserSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(request=s.ArchiveUserCreateSerializer, responses={201: s.ArchivedUserSerializer})
    def post(self, request):
        if not request.principal.has_permission("superadmin.archival.add"):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        ser = s.ArchiveUserCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        record = archival_svc.archive_user(request.principal, **ser.validated_data)
        return Response(s.ArchivedUserSerializer(record).data, status=status.HTTP_201_CREATED)


class ArchivedUserDetailView(APIView):
    permission_classes = [MODULE, HasPermission("superadmin.archival.view")]

    @extend_schema(responses={200: s.ArchivedUserSerializer})
    def get(self, request, user_id: int):
        record = archival_sel.get_archived_user(request.principal, user_id)
        if record is None:
            raise NotFoundError(f"Archived user {user_id} not found.")
        return Response(s.ArchivedUserSerializer(record).data)


class ArchivedUserRestoreView(APIView):
    permission_classes = [MODULE, HasPermission("superadmin.archival.change")]

    @extend_schema(request=s.RestoreUserSerializer, responses={200: s.ArchivedUserSerializer})
    def post(self, request, user_id: int):
        ser = s.RestoreUserSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        record = archival_svc.restore_archived_user(
            request.principal,
            user_id=user_id,
            restoration_reason=ser.validated_data["restoration_reason"],
        )
        return Response(s.ArchivedUserSerializer(record).data)


class HistoricalArchiveListView(APIView):
    permission_classes = [MODULE]

    @extend_schema(responses={200: s.HistoricalArchiveSerializer(many=True)})
    def get(self, request):
        if not request.principal.has_permission("superadmin.archival.view"):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        category = request.query_params.get("category")
        qs = archival_sel.list_historical_archives(request.principal, category=category)
        paginator = CursorPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = s.HistoricalArchiveSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        request=s.HistoricalArchiveCreateSerializer, responses={201: s.HistoricalArchiveSerializer}
    )
    def post(self, request):
        if not request.principal.has_permission("superadmin.archival.add"):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        ser = s.HistoricalArchiveCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        archive = hist_svc.create_historical_archive(request.principal, **ser.validated_data)
        return Response(s.HistoricalArchiveSerializer(archive).data, status=status.HTTP_201_CREATED)


class HistoricalArchiveRestoreView(APIView):
    permission_classes = [MODULE, HasPermission("superadmin.archival.change")]

    @extend_schema(request=None, responses={200: s.HistoricalArchiveSerializer})
    def post(self, request, pk: int):
        archive = hist_svc.restore_historical_archive(request.principal, archive_id=pk)
        return Response(s.HistoricalArchiveSerializer(archive).data)


class PurgeRequestListView(APIView):
    permission_classes = [MODULE]

    @extend_schema(responses={200: s.PurgeRequestSerializer(many=True)})
    def get(self, request):
        if not request.principal.has_permission("superadmin.purge.view"):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        status_filter = request.query_params.get("status")
        qs = purge_sel.list_purge_requests(request.principal, status=status_filter)
        paginator = CursorPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = s.PurgeRequestSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        request=s.PurgeRequestCreateSerializer, responses={201: s.PurgeRequestSerializer}
    )
    def post(self, request):
        if not request.principal.has_permission("superadmin.purge.add"):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        ser = s.PurgeRequestCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        req = purge_svc.create_purge_request(request.principal, **ser.validated_data)
        return Response(s.PurgeRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class PurgeRequestDecisionView(APIView):
    permission_classes = [MODULE, HasPermission("superadmin.purge.change")]

    @extend_schema(request=s.PurgeDecisionSerializer, responses={200: s.PurgeRequestSerializer})
    def post(self, request, pk: int):
        ser = s.PurgeDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        req = purge_svc.decide_purge_request(
            request.principal,
            request_id=pk,
            approve=ser.validated_data["approve"],
            comments=ser.validated_data.get("comments", ""),
        )
        return Response(s.PurgeRequestSerializer(req).data)


class PurgeRequestExecuteView(APIView):
    permission_classes = [MODULE, HasPermission("superadmin.purge.add")]

    @extend_schema(request=s.PurgeExecuteSerializer, responses={200: s.PurgeRequestSerializer})
    def post(self, request, pk: int):
        ser = s.PurgeExecuteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        req = purge_svc.execute_purge(
            request.principal,
            request_id=pk,
            execution_summary=ser.validated_data.get("execution_summary"),
        )
        return Response(s.PurgeRequestSerializer(req).data)


class PolicyParameterListView(APIView):
    permission_classes = [MODULE]

    @extend_schema(responses={200: s.PolicyParameterSerializer(many=True)})
    def get(self, request):
        if not request.principal.has_permission("superadmin.policy.view"):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        policies = config_sel.list_active_policy_params()
        serializer = s.PolicyParameterSerializer(policies, many=True)
        return Response(serializer.data)

    @extend_schema(
        request=s.PolicySupersedeSerializer, responses={201: s.PolicyParameterSerializer}
    )
    def post(self, request):
        if not request.principal.has_permission("superadmin.policy.change"):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        ser = s.PolicySupersedeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        new_param = config_svc.supersede_policy_param(request.principal, **ser.validated_data)
        return Response(s.PolicyParameterSerializer(new_param).data, status=status.HTTP_201_CREATED)


class AuditLogListView(APIView):
    permission_classes = [MODULE, HasPermission("superadmin.audit.view")]

    @extend_schema(responses={200: s.SuperAdminAuditLogSerializer(many=True)})
    def get(self, request):
        actor_id_raw = request.query_params.get("actor_id")
        actor_id = None
        if actor_id_raw is not None:
            try:
                actor_id = int(actor_id_raw)
            except ValueError as err:
                raise BadRequestError("actor_id must be an integer.") from err
        action = request.query_params.get("action")
        qs = audit_sel.list_audit_logs(request.principal, actor_id=actor_id, action=action)
        paginator = CursorPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = s.SuperAdminAuditLogSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AuditLogExportView(APIView):
    permission_classes = [MODULE, HasPermission("superadmin.audit.view")]

    @extend_schema(responses={(200, "text/csv"): OpenApiTypes.STR})
    def get(self, request):
        qs = audit_sel.list_audit_logs(request.principal)[:5000]
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="superadmin_audit_logs.csv"'
        writer = csv.writer(response)
        writer.writerow(
            [
                "id",
                "timestamp",
                "actor_id",
                "actor_username",
                "action",
                "target_id",
                "result",
                "reason",
            ]
        )
        for e in qs:
            writer.writerow(
                [
                    e.id,
                    e.timestamp.isoformat(),
                    e.actor_id,
                    e.actor_username,
                    e.action,
                    e.target_id,
                    e.result,
                    e.reason,
                ]
            )
        return response
