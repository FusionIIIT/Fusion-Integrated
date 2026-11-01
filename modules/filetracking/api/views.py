"""API views for File Tracking System (FTS).

Implements FTS-UC-001..007, FTS-UC-009.
All reads pass through selectors; all writes pass through services.
"""
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.filetracking.api import serializers as s
from modules.filetracking.domain import (
    ArchivalNotAllowedError,
    DraftBoundaryViolationError,
    FileArchivedError,
    InitialCommentRequiredError,
    InvalidRecipientError,
    InvalidReturnTargetError,
    MovementCommentRequiredError,
    NotFileHolderError,
    SystemAdminOperationalActionBlockedError,
    UnauthorizedFileActionError,
    ValidationError,
)
from modules.filetracking.selectors import (
    get_file_tracking_history,
    get_visible_file,
    visible_archived,
    visible_audit_logs,
    visible_drafts,
    visible_files,
    visible_inbox,
    visible_outbox,
)
from modules.filetracking.services import (
    P_ARCHIVE,
    P_CREATE,
    P_FORWARD,
    P_GOV_VIEW,
    P_RETURN,
    P_VIEW,
    archive_file,
    create_draft,
    discard_draft,
    edit_draft,
    forward_file,
    return_file,
)

MODULE_GATE = HasModuleGrant("filetracking")


def _get_principal_info(request):
    principal = getattr(request, "principal", None)
    if principal is None:
        user_id = getattr(request.user, "id", 1)
        role = "faculty"
        is_admin = False
    else:
        user_id = principal.user_id
        role = (
            getattr(principal, "selected_role", None)
            or getattr(principal, "designation", "faculty")
        )
        is_admin = role in ("admin", "system_admin")
    return user_id, role, is_admin


def _map_domain_error(exc: Exception):
    bad_reqs = (
        InitialCommentRequiredError,
        MovementCommentRequiredError,
        InvalidRecipientError,
        ValidationError,
    )
    conflicts = (
        DraftBoundaryViolationError,
        FileArchivedError,
        ArchivalNotAllowedError,
        NotFileHolderError,
        InvalidReturnTargetError,
    )
    if isinstance(exc, bad_reqs):
        return BadRequestError(str(exc))
    if isinstance(exc, conflicts):
        return ConflictError(str(exc))
    if isinstance(exc, (SystemAdminOperationalActionBlockedError, UnauthorizedFileActionError)):
        return PermissionDeniedError(str(exc))
    return BadRequestError(str(exc))


class FileListView(APIView):
    """List files (inbox, outbox, drafts, archive) or create a new file draft."""

    permission_classes = [MODULE_GATE, HasPermission(P_VIEW, P_CREATE)]

    @extend_schema(
        summary="List files visible to user",
        parameters=[
            OpenApiParameter(
                name="tab",
                description="Inbox, outbox, drafts, or archive tab",
                required=False,
                type=str,
                enum=["inbox", "outbox", "drafts", "archive", "all"],
            ),
        ],
        responses={200: s.TrackedFileListSerializer(many=True)},
        tags=["filetracking"],
    )
    def get(self, request):
        user_id, _, _ = _get_principal_info(request)
        tab = request.query_params.get("tab", "inbox").lower()

        if tab == "inbox":
            qs = visible_inbox(user_id)
        elif tab == "outbox":
            qs = visible_outbox(user_id)
        elif tab == "drafts":
            qs = visible_drafts(user_id)
        elif tab == "archive":
            qs = visible_archived(user_id)
        else:
            qs = visible_files(user_id)

        serializer = s.TrackedFileListSerializer(qs, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Create a new file draft",
        request=s.CreateDraftSerializer,
        responses={201: s.TrackedFileDetailSerializer},
        tags=["filetracking"],
    )
    def post(self, request):
        user_id, role, is_admin = _get_principal_info(request)
        serializer = s.CreateDraftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            file_obj = create_draft(
                subject=serializer.validated_data["subject"],
                description=serializer.validated_data.get("description", ""),
                creator_user_id=user_id,
                creator_role=role,
                initial_comment=serializer.validated_data["initial_comment"],
                attachments_data=serializer.validated_data.get("attachments", []),
                is_system_admin=is_admin,
            )
        except Exception as exc:
            raise _map_domain_error(exc) from exc

        return Response(
            s.TrackedFileDetailSerializer(file_obj).data,
            status=status.HTTP_201_CREATED,
        )


class FileDetailView(APIView):
    """Retrieve details of an associated file (comments, movements, attachments)."""

    permission_classes = [MODULE_GATE, HasPermission(P_VIEW)]

    @extend_schema(
        summary="Get file detail",
        responses={200: s.TrackedFileDetailSerializer},
        tags=["filetracking"],
    )
    def get(self, request, pk: int):
        user_id, _, _ = _get_principal_info(request)
        file_obj = get_visible_file(user_id, pk)
        if not file_obj:
            raise NotFoundError("File not found or not accessible.")
        return Response(s.TrackedFileDetailSerializer(file_obj).data)


class DraftActionView(APIView):
    """Edit or discard a pre-circulation draft (FTS-UC-002)."""

    permission_classes = [MODULE_GATE, HasPermission(P_CREATE)]

    @extend_schema(
        summary="Edit draft file",
        request=s.EditDraftSerializer,
        responses={200: s.TrackedFileDetailSerializer},
        tags=["filetracking"],
    )
    def patch(self, request, pk: int):
        user_id, role, is_admin = _get_principal_info(request)
        file_obj = get_visible_file(user_id, pk)
        if not file_obj:
            raise NotFoundError("Draft not found or not accessible.")

        serializer = s.EditDraftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = edit_draft(
                file_id=pk,
                actor_user_id=user_id,
                actor_role=role,
                subject=serializer.validated_data.get("subject"),
                description=serializer.validated_data.get("description"),
                new_comment=serializer.validated_data.get("comment"),
                new_attachments=serializer.validated_data.get("attachments"),
                is_system_admin=is_admin,
            )
        except Exception as exc:
            raise _map_domain_error(exc) from exc

        return Response(s.TrackedFileDetailSerializer(updated).data)

    @extend_schema(
        summary="Discard draft file",
        responses={204: None},
        tags=["filetracking"],
    )
    def delete(self, request, pk: int):
        user_id, role, is_admin = _get_principal_info(request)
        file_obj = get_visible_file(user_id, pk)
        if not file_obj:
            raise NotFoundError("Draft not found or not accessible.")

        try:
            discard_draft(
                file_id=pk,
                actor_user_id=user_id,
                actor_role=role,
                is_system_admin=is_admin,
            )
        except Exception as exc:
            raise _map_domain_error(exc) from exc

        return Response(status=status.HTTP_204_NO_CONTENT)


class FileForwardView(APIView):
    """Forward file to another institute employee (FTS-UC-003)."""

    permission_classes = [MODULE_GATE, HasPermission(P_FORWARD)]

    @extend_schema(
        summary="Forward file to employee",
        request=s.ForwardFileSerializer,
        responses={200: s.FileMovementSerializer},
        tags=["filetracking"],
    )
    def post(self, request, pk: int):
        user_id, role, is_admin = _get_principal_info(request)
        file_obj = get_visible_file(user_id, pk)
        if not file_obj:
            raise NotFoundError("File not found or not accessible.")

        serializer = s.ForwardFileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            movement = forward_file(
                file_id=pk,
                sender_user_id=user_id,
                sender_role=role,
                receiver_user_id=serializer.validated_data["receiver_user_id"],
                receiver_role=serializer.validated_data["receiver_role"],
                comment=serializer.validated_data["comment"],
                attachments_data=serializer.validated_data.get("attachments"),
                is_system_admin=is_admin,
            )
        except Exception as exc:
            raise _map_domain_error(exc) from exc

        return Response(s.FileMovementSerializer(movement).data)


class FileReturnView(APIView):
    """Return received file to previous sender (FTS-UC-004)."""

    permission_classes = [MODULE_GATE, HasPermission(P_RETURN)]

    @extend_schema(
        summary="Return received file",
        request=s.ReturnFileSerializer,
        responses={200: s.FileMovementSerializer},
        tags=["filetracking"],
    )
    def post(self, request, pk: int):
        user_id, role, is_admin = _get_principal_info(request)
        file_obj = get_visible_file(user_id, pk)
        if not file_obj:
            raise NotFoundError("File not found or not accessible.")

        serializer = s.ReturnFileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            movement = return_file(
                file_id=pk,
                sender_user_id=user_id,
                sender_role=role,
                comment=serializer.validated_data["comment"],
                attachments_data=serializer.validated_data.get("attachments"),
                is_system_admin=is_admin,
            )
        except Exception as exc:
            raise _map_domain_error(exc) from exc

        return Response(s.FileMovementSerializer(movement).data)


class FileArchiveView(APIView):
    """Archive completed circulated file by owner (FTS-UC-007)."""

    permission_classes = [MODULE_GATE, HasPermission(P_ARCHIVE)]

    @extend_schema(
        summary="Archive completed file",
        request=None,
        responses={200: s.TrackedFileDetailSerializer},
        tags=["filetracking"],
    )
    def post(self, request, pk: int):
        user_id, role, is_admin = _get_principal_info(request)
        file_obj = get_visible_file(user_id, pk)
        if not file_obj:
            raise NotFoundError("File not found or not accessible.")

        try:
            archived = archive_file(
                file_id=pk,
                actor_user_id=user_id,
                actor_role=role,
                is_system_admin=is_admin,
            )
        except Exception as exc:
            raise _map_domain_error(exc) from exc

        return Response(s.TrackedFileDetailSerializer(archived).data)


class FileHistoryView(APIView):
    """Chronological file tracking movement history (FTS-UC-006)."""

    permission_classes = [MODULE_GATE, HasPermission(P_VIEW)]

    @extend_schema(
        summary="View file tracking history",
        responses={200: s.FileMovementSerializer(many=True)},
        tags=["filetracking"],
    )
    def get(self, request, pk: int):
        user_id, _, _ = _get_principal_info(request)
        movements = get_file_tracking_history(user_id, pk)
        if not movements.exists() and not get_visible_file(user_id, pk):
            raise NotFoundError("File not found or not accessible.")
        return Response(s.FileMovementSerializer(movements, many=True).data)


class GovernanceAuditLogsView(APIView):
    """System Admin governance usage and audit logs (FTS-UC-009)."""

    permission_classes = [MODULE_GATE, HasPermission(P_GOV_VIEW)]

    @extend_schema(
        summary="View governance audit logs",
        responses={200: s.FileAuditLogSerializer(many=True)},
        tags=["filetracking"],
    )
    def get(self, request):
        qs = visible_audit_logs()
        return Response(s.FileAuditLogSerializer(qs, many=True).data)
