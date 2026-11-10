"""Fusion Clean Architecture - File Tracking System (FTS) API Views."""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from modules.fts.api.serializers import (
    ArchiveFileSerializer,
    CreateDraftSerializer,
    ForwardFileSerializer,
    FTSFileSerializer,
    ReturnFileSerializer,
)
from modules.fts.models import FTSFile
from modules.fts.selectors.drafts import get_user_draft_files
from modules.fts.selectors.inbox_outbox import (
    get_user_inbox_files,
    get_user_outbox_files,
)
from modules.fts.selectors.movements import get_file_movement_history
from modules.fts.services.archival import archive_file
from modules.fts.services.drafts import create_file_draft
from modules.fts.services.movements import forward_file, return_file


class FTSFileViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for managing FTS file operations and queries."""

    queryset = FTSFile.objects.all().order_by("-updated_at")
    serializer_class = FTSFileSerializer

    def _get_current_user_id(self, request: Request) -> str:
        """Extracts employee ID from auth context or request headers."""
        if hasattr(request.user, "username") and request.user.username:
            return str(request.user.username)
        return request.headers.get("X-Employee-ID", "system_user")

    @action(detail=False, methods=["get"])
    def inbox(self, request: Request) -> Response:
        """Endpoint to get current active files in custody of requesting employee."""
        user_id = self._get_current_user_id(request)
        files = get_user_inbox_files(user_id=user_id)
        return Response(files)

    @action(detail=False, methods=["get"])
    def outbox(self, request: Request) -> Response:
        """Endpoint to get active files sent by requesting employee to others."""
        user_id = self._get_current_user_id(request)
        files = get_user_outbox_files(user_id=user_id)
        return Response(files)

    @action(detail=False, methods=["get"])
    def drafts(self, request: Request) -> Response:
        """Endpoint to get saved drafts created by requesting employee."""
        user_id = self._get_current_user_id(request)
        files = get_user_draft_files(creator_id=user_id)
        return Response(files)

    @action(detail=False, methods=["post"], url_path="create-draft")
    def create_draft(self, request: Request) -> Response:
        """Endpoint to create a new file draft with mandatory initial comment."""
        serializer = CreateDraftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user_id = self._get_current_user_id(request)
        try:
            result = create_file_draft(
                creator_id=user_id,
                creator_role=data["creator_role"],
                subject=data["subject"],
                initial_comment=data["initial_comment"],
                priority=data["priority"],
                category=data["category"],
                description=data.get("description", ""),
            )
            return Response(result, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def forward(self, request: Request, pk: str | None = None) -> Response:
        """Endpoint to forward an active file to another employee."""
        serializer = ForwardFileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user_id = self._get_current_user_id(request)
        try:
            result = forward_file(
                file_id=int(pk),
                sender_id=user_id,
                sender_role=data["sender_role"],
                receiver_id=data["receiver_id"],
                receiver_role=data["receiver_role"],
                comment=data["comment"],
            )
            return Response(result, status=status.HTTP_200_OK)
        except (ValueError, PermissionError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def return_file_action(self, request: Request, pk: str | None = None) -> Response:
        """Endpoint to return a file to a previous sender."""
        serializer = ReturnFileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user_id = self._get_current_user_id(request)
        try:
            result = return_file(
                file_id=int(pk),
                sender_id=user_id,
                sender_role=data["sender_role"],
                comment=data["comment"],
                target_receiver_id=data.get("target_receiver_id"),
            )
            return Response(result, status=status.HTTP_200_OK)
        except (ValueError, PermissionError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def archive(self, request: Request, pk: str | None = None) -> Response:
        """Endpoint to archive a completed file."""
        serializer = ArchiveFileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user_id = self._get_current_user_id(request)
        try:
            result = archive_file(
                file_id=int(pk),
                user_id=user_id,
                user_role=data["user_role"],
                remarks=data["remarks"],
            )
            return Response(result, status=status.HTTP_200_OK)
        except (ValueError, PermissionError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"])
    def history(self, request: Request, pk: str | None = None) -> Response:
        """Endpoint to view the chronological movement and comment history of a file."""
        audit_trail = get_file_movement_history(file_id=int(pk))
        return Response(audit_trail)
