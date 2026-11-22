"""HTTP API Views for File Tracking System (transport only: parse, scope, delegate)."""


from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError
from modules.filetracking.api.permissions import (
    MODULE,
    P_API_INTEGRATE,
    P_FILE_ARCHIVE,
    P_FILE_CREATE,
    P_FILE_FORWARD,
    P_FILE_RETURN,
    P_FILE_VIEW,
    P_GOVERNANCE_VIEW,
    require_permission,
)
from modules.filetracking.api.serializers import (
    ArchiveFileRequestSerializer,
    CreateFileRequestSerializer,
    FileAuditLogSerializer,
    FileMovementSerializer,
    ForwardFileRequestSerializer,
    IntegrationInitiateRequestSerializer,
    IntegrationInitiateResponseSerializer,
    ReturnFileRequestSerializer,
    TrackedFileDetailSerializer,
    TrackedFileListSerializer,
    UpdateDraftRequestSerializer,
)
from modules.filetracking.selectors import (
    get_archived_files,
    get_associated_file_or_404,
    get_audit_logs,
    get_draft_files,
    get_file_movements,
    get_inbox_files,
    get_outbox_files,
)
from modules.filetracking.services import (
    archive_file,
    create_file,
    discard_draft,
    forward_file,
    return_file,
    update_draft,
)


def _get_user_id(request) -> int:
    principal = getattr(request, "principal", None)
    if principal and getattr(principal, "user_id", None):
        return principal.user_id
    if getattr(request, "user", None) and getattr(request.user, "id", None):
        return request.user.id
    raise BadRequestError("Authenticated user identification required.", code="unauthenticated")


def _get_acting_designation(request) -> str:
    principal = getattr(request, "principal", None)
    if principal and getattr(principal, "active_role", None):
        return principal.active_role
    return "employee"


def _get_ip(request) -> str:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or "127.0.0.1"


class InboxView(APIView):
    permission_classes = require_permission(P_FILE_VIEW)

    @extend_schema(
        summary="List inbox files",
        description="Files currently held by user awaiting action.",
        responses={200: TrackedFileListSerializer(many=True)},
    )
    def get(self, request):
        user_id = _get_user_id(request)
        qs = get_inbox_files(user_id)
        return Response(TrackedFileListSerializer(qs, many=True).data)


class OutboxView(APIView):
    permission_classes = require_permission(P_FILE_VIEW)

    @extend_schema(
        summary="List outbox files",
        description="Active files previously created or sent by user.",
        responses={200: TrackedFileListSerializer(many=True)},
    )
    def get(self, request):
        user_id = _get_user_id(request)
        qs = get_outbox_files(user_id)
        return Response(TrackedFileListSerializer(qs, many=True).data)


class DraftsView(APIView):
    permission_classes = require_permission(P_FILE_CREATE)

    @extend_schema(
        summary="List draft files",
        description="Uncirculated draft files created by user.",
        responses={200: TrackedFileListSerializer(many=True)},
    )
    def get(self, request):
        user_id = _get_user_id(request)
        qs = get_draft_files(user_id)
        return Response(TrackedFileListSerializer(qs, many=True).data)


class ArchivedView(APIView):
    permission_classes = require_permission(P_FILE_VIEW)

    @extend_schema(
        summary="List archived files",
        description="Completed archived files associated with user.",
        responses={200: TrackedFileListSerializer(many=True)},
    )
    def get(self, request):
        user_id = _get_user_id(request)
        qs = get_archived_files(user_id)
        return Response(TrackedFileListSerializer(qs, many=True).data)


class FileCreateView(APIView):
    permission_classes = require_permission(P_FILE_CREATE)

    @extend_schema(
        summary="Create a new file",
        description="Create a file as draft or directly submit into circulation.",
        request=CreateFileRequestSerializer,
        responses={201: TrackedFileDetailSerializer},
    )
    def post(self, request):
        serializer = CreateFileRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user_id = _get_user_id(request)
        desig = _get_acting_designation(request)
        ip = _get_ip(request)

        file = create_file(
            creator_user_id=user_id,
            creator_designation=desig,
            subject=data["subject"],
            initial_comment=data["initial_comment"],
            is_draft=data.get("is_draft", False),
            recipient_user_id=data.get("recipient_user_id"),
            recipient_designation=data.get("recipient_designation", ""),
            attachments=data.get("attachments"),
            ip_address=ip,
        )
        return Response(TrackedFileDetailSerializer(file).data, status=status.HTTP_201_CREATED)


class FileDetailView(APIView):
    permission_classes = require_permission(P_FILE_VIEW)

    @extend_schema(
        summary="Retrieve file detail",
        description="Retrieve full file details and history if user is associated.",
        responses={200: TrackedFileDetailSerializer},
    )
    def get(self, request, file_id: int):
        user_id = _get_user_id(request)
        file = get_associated_file_or_404(file_id, user_id)
        return Response(TrackedFileDetailSerializer(file).data)


class FileDraftUpdateView(APIView):
    permission_classes = require_permission(P_FILE_CREATE)

    @extend_schema(
        summary="Update draft file",
        description="Edit subject or description on an uncirculated draft (owner only).",
        request=UpdateDraftRequestSerializer,
        responses={200: TrackedFileDetailSerializer},
    )
    def put(self, request, file_id: int):
        serializer = UpdateDraftRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user_id = _get_user_id(request)
        desig = _get_acting_designation(request)
        ip = _get_ip(request)

        file = update_draft(
            file_id=file_id,
            actor_user_id=user_id,
            actor_designation=desig,
            subject=data.get("subject"),
            description=data.get("description"),
            attachments=data.get("attachments"),
            ip_address=ip,
        )
        return Response(TrackedFileDetailSerializer(file).data)


class FileDraftDiscardView(APIView):
    permission_classes = require_permission(P_FILE_CREATE)

    @extend_schema(
        summary="Discard draft file",
        description="Delete an uncirculated draft file (owner only; fails if circulated).",
        responses={204: None},
    )
    def delete(self, request, file_id: int):
        user_id = _get_user_id(request)
        desig = _get_acting_designation(request)
        ip = _get_ip(request)

        discard_draft(
            file_id=file_id,
            actor_user_id=user_id,
            actor_designation=desig,
            ip_address=ip,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class FileForwardView(APIView):
    permission_classes = require_permission(P_FILE_FORWARD)

    @extend_schema(
        summary="Forward file",
        description="Forward an active file to another employee with mandatory comment.",
        request=ForwardFileRequestSerializer,
        responses={200: FileMovementSerializer},
    )
    def post(self, request, file_id: int):
        serializer = ForwardFileRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user_id = _get_user_id(request)
        desig = _get_acting_designation(request)
        ip = _get_ip(request)

        movement = forward_file(
            file_id=file_id,
            actor_user_id=user_id,
            actor_designation=desig,
            recipient_user_id=data["recipient_user_id"],
            recipient_designation=data.get("recipient_designation", ""),
            comment=data["comment"],
            attachments=data.get("attachments"),
            ip_address=ip,
        )
        return Response(FileMovementSerializer(movement).data)


class FileReturnView(APIView):
    permission_classes = require_permission(P_FILE_RETURN)

    @extend_schema(
        summary="Return file",
        description="Return an active received file to its previous sender with mandatory comment.",
        request=ReturnFileRequestSerializer,
        responses={200: FileMovementSerializer},
    )
    def post(self, request, file_id: int):
        serializer = ReturnFileRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user_id = _get_user_id(request)
        desig = _get_acting_designation(request)
        ip = _get_ip(request)

        movement = return_file(
            file_id=file_id,
            actor_user_id=user_id,
            actor_designation=desig,
            comment=data["comment"],
            attachments=data.get("attachments"),
            ip_address=ip,
        )
        return Response(FileMovementSerializer(movement).data)


class FileArchiveView(APIView):
    permission_classes = require_permission(P_FILE_ARCHIVE)

    @extend_schema(
        summary="Archive file",
        description="Archive a completed circulated file (owner only).",
        request=ArchiveFileRequestSerializer,
        responses={200: TrackedFileDetailSerializer},
    )
    def post(self, request, file_id: int):
        serializer = ArchiveFileRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user_id = _get_user_id(request)
        desig = _get_acting_designation(request)
        ip = _get_ip(request)

        file = archive_file(
            file_id=file_id,
            actor_user_id=user_id,
            actor_designation=desig,
            comment=data.get("comment"),
            ip_address=ip,
        )
        return Response(TrackedFileDetailSerializer(file).data)


class FileHistoryView(APIView):
    permission_classes = require_permission(P_FILE_VIEW)

    @extend_schema(
        summary="File movement history",
        description="View chronological movement history (associated users only).",
        responses={200: FileMovementSerializer(many=True)},
    )
    def get(self, request, file_id: int):
        user_id = _get_user_id(request)
        file = get_associated_file_or_404(file_id, user_id)
        movements = get_file_movements(file.id)
        return Response(FileMovementSerializer(movements, many=True).data)


class GovernanceAuditView(APIView):
    permission_classes = require_permission(P_GOVERNANCE_VIEW)

    @extend_schema(
        summary="Governance audit logs",
        description="View system audit trail entries for governance oversight.",
        responses={200: FileAuditLogSerializer(many=True)},
    )
    def get(self, request):
        file_id_str = request.query_params.get("file_id")
        file_id = None
        if file_id_str:
            try:
                file_id = int(file_id_str)
            except ValueError as exc:
                raise BadRequestError(
                    "file_id query parameter must be an integer.",
                    code="invalid_param",
                ) from exc

        logs = get_audit_logs(file_id=file_id)
        return Response(FileAuditLogSerializer(logs[:100], many=True).data)


class IntegrationInitiateView(APIView):
    permission_classes = [MODULE, require_permission(P_API_INTEGRATE)[1]]

    @extend_schema(
        summary="Initiate workflow tracking chain",
        description="External module initiates file-based tracking chain.",
        request=IntegrationInitiateRequestSerializer,
        responses={201: IntegrationInitiateResponseSerializer},
    )
    def post(self, request):
        serializer = IntegrationInitiateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        file = create_file(
            creator_user_id=data["initiator_user_id"],
            creator_designation=data["initiator_designation"],
            subject=data["subject"],
            initial_comment=data["initial_comment"],
            is_draft=False,
            recipient_user_id=data["recipient_user_id"],
            recipient_designation=data.get("recipient_designation", ""),
            ip_address=_get_ip(request),
        )

        response_data = {
            "file_id": file.id,
            "file_number": file.file_number,
            "status": file.status,
            "current_holder_user_id": file.current_holder_user_id,
        }
        return Response(response_data, status=status.HTTP_201_CREATED)
