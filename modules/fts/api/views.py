"""API views for FTS operations."""
from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError
from modules.fts.api.permissions import (
    IsInstituteEmployee,
    RequireFileArchive,
    RequireFileCreate,
    RequireFileForward,
    RequireFileReturn,
    RequireFileView,
    RequireFtsModule,
    RequireGovernanceView,
    RequireIntegrationAccess,
)
from modules.fts.api.serializers import (
    CreateFileRequestSerializer,
    FileAuditLogSerializer,
    FileDetailSerializer,
    FileListSerializer,
    FileMovementSerializer,
    ForwardFileRequestSerializer,
    ReturnFileRequestSerializer,
    UpdateDraftRequestSerializer,
    UsageMetricsSerializer,
)
from modules.fts.selectors.audit import get_audit_logs, get_usage_metrics
from modules.fts.selectors.files import get_draft_files, get_inbox_files, get_outbox_files
from modules.fts.selectors.history import get_file_history
from modules.fts.selectors.scoping import get_file_for_user
from modules.fts.services.archival import archive_file
from modules.fts.services.files import create_file, discard_draft, update_draft
from modules.fts.services.movements import forward_file, return_file


class FileListCreateView(APIView):
    permission_classes = [RequireFtsModule, RequireFileCreate, IsInstituteEmployee]
    throttle_scope = "fts_file_create"

    @extend_schema(
        summary="Create a new file or draft",
        request=CreateFileRequestSerializer,
        responses={201: FileDetailSerializer},
    )
    def post(self, request):
        serializer = CreateFileRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        p = request.principal
        file_obj = create_file(
            subject=data["subject"],
            description=data.get("description", ""),
            comment_text=data["comment"],
            actor_user_id=p.user_id,
            actor_username=p.username,
            actor_role=p.active_role or "",
            actor_kind=p.kind,
            is_admin_actor="admin" in p.roles,
            is_draft=data.get("is_draft", False),
            recipient_user_id=data.get("recipient_user_id"),
            recipient_username=data.get("recipient_username", ""),
            recipient_role=data.get("recipient_role", ""),
            attachments=data.get("attachments"),
        )
        return Response(FileDetailSerializer(file_obj).data, status=status.HTTP_201_CREATED)


class DraftListView(APIView):
    permission_classes = [RequireFtsModule, RequireFileCreate, IsInstituteEmployee]

    @extend_schema(
        summary="List user's draft files",
        responses={200: FileListSerializer(many=True)},
    )
    def get(self, request):
        files = get_draft_files(request.principal.user_id)
        return Response(FileListSerializer(files, many=True).data)


class InboxListView(APIView):
    permission_classes = [RequireFtsModule, RequireFileView, IsInstituteEmployee]

    @extend_schema(
        summary="List active files in user's inbox",
        responses={200: FileListSerializer(many=True)},
    )
    def get(self, request):
        files = get_inbox_files(request.principal.user_id)
        return Response(FileListSerializer(files, many=True).data)


class OutboxListView(APIView):
    permission_classes = [RequireFtsModule, RequireFileView, IsInstituteEmployee]

    @extend_schema(
        summary="List files in user's outbox",
        responses={200: FileListSerializer(many=True)},
    )
    def get(self, request):
        files = get_outbox_files(request.principal.user_id)
        return Response(FileListSerializer(files, many=True).data)


class FileDetailView(APIView):
    permission_classes = [RequireFtsModule, RequireFileView]

    @extend_schema(summary="Retrieve file details", responses={200: FileDetailSerializer})
    def get(self, request, pk: int):
        p = request.principal
        is_admin = "admin" in p.roles or p.has_permission("fts.governance.view")
        file_obj = get_file_for_user(pk, p.user_id, is_admin=is_admin)
        return Response(FileDetailSerializer(file_obj).data)

    @extend_schema(
        summary="Update a pre-circulation draft",
        request=UpdateDraftRequestSerializer,
        responses={200: FileDetailSerializer},
    )
    def put(self, request, pk: int):
        serializer = UpdateDraftRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        p = request.principal
        file_obj = update_draft(
            file_id=pk,
            actor_user_id=p.user_id,
            actor_username=p.username,
            actor_role=p.active_role or "",
            subject=data.get("subject"),
            description=data.get("description"),
            comment_text=data.get("comment"),
            attachments=data.get("attachments"),
        )
        return Response(FileDetailSerializer(file_obj).data)


class FileDiscardView(APIView):
    permission_classes = [RequireFtsModule, RequireFileCreate, IsInstituteEmployee]
    throttle_scope = "fts_file_create"

    @extend_schema(
        summary="Discard an uncirculated draft",
        request=None,
        responses={200: FileDetailSerializer},
    )
    def post(self, request, pk: int):
        p = request.principal
        file_obj = discard_draft(
            file_id=pk,
            actor_user_id=p.user_id,
            actor_username=p.username,
            actor_role=p.active_role or "",
        )
        return Response(FileDetailSerializer(file_obj).data)


class FileForwardView(APIView):
    permission_classes = [RequireFtsModule, RequireFileForward, IsInstituteEmployee]
    throttle_scope = "fts_file_forward"

    @extend_schema(
        summary="Forward file onward",
        request=ForwardFileRequestSerializer,
        responses={200: FileMovementSerializer},
    )
    def post(self, request, pk: int):
        serializer = ForwardFileRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        p = request.principal
        movement = forward_file(
            file_id=pk,
            actor_user_id=p.user_id,
            actor_username=p.username,
            actor_role=p.active_role or "",
            actor_kind=p.kind,
            is_admin_actor="admin" in p.roles,
            to_user_id=data["to_user_id"],
            to_username=data["to_username"],
            to_role=data["to_role"],
            comment_text=data["comment"],
            attachments=data.get("attachments"),
        )
        return Response(FileMovementSerializer(movement).data)


class FileReturnView(APIView):
    permission_classes = [RequireFtsModule, RequireFileReturn, IsInstituteEmployee]
    throttle_scope = "fts_file_forward"

    @extend_schema(
        summary="Return received file to sender",
        request=ReturnFileRequestSerializer,
        responses={200: FileMovementSerializer},
    )
    def post(self, request, pk: int):
        serializer = ReturnFileRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        p = request.principal
        movement = return_file(
            file_id=pk,
            actor_user_id=p.user_id,
            actor_username=p.username,
            actor_role=p.active_role or "",
            actor_kind=p.kind,
            is_admin_actor="admin" in p.roles,
            comment_text=data["comment"],
            attachments=data.get("attachments"),
        )
        return Response(FileMovementSerializer(movement).data)


class FileArchiveView(APIView):
    permission_classes = [RequireFtsModule, RequireFileArchive, IsInstituteEmployee]
    throttle_scope = "fts_file_forward"

    @extend_schema(
        summary="Archive completed circulated file (owner only)",
        request=None,
        responses={200: FileDetailSerializer},
    )
    def post(self, request, pk: int):
        p = request.principal
        file_obj = archive_file(
            file_id=pk,
            actor_user_id=p.user_id,
            actor_username=p.username,
            actor_role=p.active_role or "",
            actor_kind=p.kind,
            is_admin_actor="admin" in p.roles,
        )
        return Response(FileDetailSerializer(file_obj).data)


class FileHistoryView(APIView):
    permission_classes = [RequireFtsModule, RequireFileView]

    @extend_schema(
        summary="View file tracking history",
        responses={200: FileMovementSerializer(many=True)},
    )
    def get(self, request, pk: int):
        p = request.principal
        is_admin = "admin" in p.roles or p.has_permission("fts.governance.view")
        get_file_for_user(pk, p.user_id, is_admin=is_admin)
        history = get_file_history(pk)
        return Response(FileMovementSerializer(history, many=True).data)


class GovernanceAuditLogsView(APIView):
    permission_classes = [RequireFtsModule, RequireGovernanceView]

    @extend_schema(
        summary="View FTS audit logs",
        parameters=[
            OpenApiParameter("file_id", int, required=False, description="Filter logs by file ID")
        ],
        responses={200: FileAuditLogSerializer(many=True)},
    )
    def get(self, request):
        raw_file_id = request.query_params.get("file_id")
        file_id = None
        if raw_file_id is not None:
            try:
                file_id = int(raw_file_id)
            except ValueError as e:
                raise BadRequestError("file_id query parameter must be a valid integer.") from e
        logs = get_audit_logs(file_id=file_id)
        return Response(FileAuditLogSerializer(logs, many=True).data)


class GovernanceUsageView(APIView):
    permission_classes = [RequireFtsModule, RequireGovernanceView]

    @extend_schema(summary="View FTS usage statistics", responses={200: UsageMetricsSerializer})
    def get(self, request):
        metrics = get_usage_metrics()
        return Response(UsageMetricsSerializer(metrics).data)


class IntegrationCreateFileView(APIView):
    permission_classes = [RequireIntegrationAccess]

    @extend_schema(
        summary="Create and track file for consuming Fusion modules",
        request=CreateFileRequestSerializer,
        responses={201: FileDetailSerializer},
    )
    def post(self, request):
        serializer = CreateFileRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        p = request.principal
        file_obj = create_file(
            subject=data["subject"],
            description=data.get("description", ""),
            comment_text=data["comment"],
            actor_user_id=p.user_id,
            actor_username=p.username,
            actor_role=p.active_role or "",
            actor_kind="faculty",
            is_draft=data.get("is_draft", False),
            recipient_user_id=data.get("recipient_user_id"),
            recipient_username=data.get("recipient_username", ""),
            recipient_role=data.get("recipient_role", ""),
            attachments=data.get("attachments"),
        )
        return Response(FileDetailSerializer(file_obj).data, status=status.HTTP_201_CREATED)
