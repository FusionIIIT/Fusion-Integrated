"""HTTP views for FTS."""
from __future__ import annotations

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.directory import contracts as directory
from modules.fts.api import serializers as s
from modules.fts.api.permissions import IsInstituteEmployee
from modules.fts.selectors import scoping
from modules.fts.services import file_service


class InboxListView(APIView):
    permission_classes = [HasModuleGrant("fts"), HasPermission("fts.file.view")]

    @extend_schema(
        summary="List inbox files",
        description="Return circulating files currently held by the authenticated employee.",
        responses={200: s.FTSFileListSerializer(many=True)},
    )
    def get(self, request):
        files = scoping.visible_inbox_files(request.principal.user_id)
        serializer = s.FTSFileListSerializer(files, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OutboxListView(APIView):
    permission_classes = [HasModuleGrant("fts"), HasPermission("fts.file.view")]

    @extend_schema(
        summary="List outbox files",
        description="Return files sent or forwarded by the authenticated employee.",
        responses={200: s.FTSFileListSerializer(many=True)},
    )
    def get(self, request):
        files = scoping.visible_outbox_files(request.principal.user_id)
        serializer = s.FTSFileListSerializer(files, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DraftsListView(APIView):
    permission_classes = [HasModuleGrant("fts"), HasPermission("fts.file.view")]

    @extend_schema(
        summary="List draft files",
        description="Return uncirculated draft files created by the authenticated employee.",
        responses={200: s.FTSFileListSerializer(many=True)},
    )
    def get(self, request):
        files = scoping.visible_draft_files(request.principal.user_id)
        serializer = s.FTSFileListSerializer(files, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class FileCreateView(APIView):
    permission_classes = [
        HasModuleGrant("fts"),
        HasPermission("fts.file.create"),
        IsInstituteEmployee,
    ]

    @extend_schema(
        summary="Create file or save draft",
        description="Create a new institutional file in draft or directly into circulation.",
        request=s.CreateFileSerializer,
        responses={
            201: s.FTSFileDetailSerializer,
            400: OpenApiResponse(description="Validation error or missing comment"),
            403: OpenApiResponse(description="Non-employee or administrative user rejected"),
        },
    )
    def post(self, request):
        serializer = s.CreateFileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        p = request.principal
        is_employee = p.kind in ("faculty", "staff")
        is_admin = p.kind == "admin" or p.active_role in ("admin", "system_admin")

        file_obj = file_service.create_file(
            subject=data["subject"],
            description=data.get("description", ""),
            initial_comment=data["initial_comment"],
            creator_id=p.user_id,
            creator_designation=p.active_role or "",
            is_draft=data.get("is_draft", False),
            receiver_id=data.get("receiver_id"),
            receiver_designation=data.get("receiver_designation", ""),
            attachments=data.get("attachments", []),
            is_employee=is_employee,
            is_system_admin=is_admin,
        )
        out_serializer = s.FTSFileDetailSerializer(file_obj)
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)


class FileDetailView(APIView):
    permission_classes = [HasModuleGrant("fts"), HasPermission("fts.file.view")]

    @extend_schema(
        summary="Get file details",
        description="Return file metadata, movements, comments and attachments if associated.",
        responses={
            200: s.FTSFileDetailSerializer,
            404: OpenApiResponse(description="File not found or unassociated user"),
        },
    )
    def get(self, request, file_identifier: str):
        file_obj = scoping.get_visible_file(file_identifier, request.principal.user_id)
        if not file_obj:
            raise NotFoundError("The requested file was not found or is inaccessible.")
        serializer = s.FTSFileDetailSerializer(file_obj)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DraftActionView(APIView):
    permission_classes = [
        HasModuleGrant("fts"),
        HasPermission("fts.file.update"),
        IsInstituteEmployee,
    ]

    @extend_schema(
        summary="Edit draft file",
        description="Edit subject, description, comment or attachments on an uncirculated draft.",
        request=s.EditDraftSerializer,
        responses={
            200: s.FTSFileDetailSerializer,
            404: OpenApiResponse(description="Draft not found"),
            409: OpenApiResponse(description="Not in draft state"),
        },
    )
    def patch(self, request, file_identifier: str):
        serializer = s.EditDraftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        file_obj = file_service.edit_draft(
            file_id_or_pk=file_identifier,
            user_id=request.principal.user_id,
            subject=data.get("subject"),
            description=data.get("description"),
            comment=data.get("comment"),
            attachments=data.get("attachments"),
        )
        return Response(s.FTSFileDetailSerializer(file_obj).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Discard draft file",
        description="Permanently discard an uncirculated draft file.",
        responses={
            204: OpenApiResponse(description="Draft successfully discarded"),
            404: OpenApiResponse(description="Draft not found"),
            409: OpenApiResponse(description="Not in draft state"),
        },
    )
    def delete(self, request, file_identifier: str):
        if "fts.file.delete" not in request.principal.permissions:
            from core.api.exceptions import PermissionDeniedError
            raise PermissionDeniedError("Permission fts.file.delete required to discard drafts.")
        file_service.discard_draft(
            file_id_or_pk=file_identifier,
            user_id=request.principal.user_id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class ForwardFileView(APIView):
    permission_classes = [
        HasModuleGrant("fts"),
        HasPermission("fts.file.update"),
        IsInstituteEmployee,
    ]

    @extend_schema(
        summary="Forward file",
        description="Forward an active file to the next institute employee.",
        request=s.ForwardFileSerializer,
        responses={
            200: s.FileMovementSerializer,
            400: OpenApiResponse(description="Validation error or self-forwarding"),
            403: OpenApiResponse(description="Not the current holder"),
            404: OpenApiResponse(description="File not found"),
        },
    )
    def post(self, request, file_identifier: str):
        serializer = s.ForwardFileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        p = request.principal
        is_employee = p.kind in ("faculty", "staff")
        is_admin = p.kind == "admin" or p.active_role in ("admin", "system_admin")

        movement = file_service.forward_file(
            file_id_or_pk=file_identifier,
            sender_id=p.user_id,
            sender_designation=p.active_role or "",
            receiver_id=data["receiver_id"],
            receiver_designation=data.get("receiver_designation", ""),
            remarks=data["remarks"],
            attachments=data.get("attachments", []),
            is_employee=is_employee,
            is_system_admin=is_admin,
        )
        return Response(s.FileMovementSerializer(movement).data, status=status.HTTP_200_OK)


class ReturnFileView(APIView):
    permission_classes = [
        HasModuleGrant("fts"),
        HasPermission("fts.file.update"),
        IsInstituteEmployee,
    ]

    @extend_schema(
        summary="Return file",
        description="Return an active file to its immediate previous sender.",
        request=s.ReturnFileSerializer,
        responses={
            200: s.FileMovementSerializer,
            400: OpenApiResponse(description="Missing comment or self-return"),
            403: OpenApiResponse(description="Not current holder"),
            404: OpenApiResponse(description="File not found"),
        },
    )
    def post(self, request, file_identifier: str):
        serializer = s.ReturnFileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        p = request.principal
        is_employee = p.kind in ("faculty", "staff")
        is_admin = p.kind == "admin" or p.active_role in ("admin", "system_admin")

        movement = file_service.return_file(
            file_id_or_pk=file_identifier,
            sender_id=p.user_id,
            sender_designation=p.active_role or "",
            remarks=data["remarks"],
            attachments=data.get("attachments", []),
            is_employee=is_employee,
            is_system_admin=is_admin,
        )
        return Response(s.FileMovementSerializer(movement).data, status=status.HTTP_200_OK)


class ArchiveFileView(APIView):
    permission_classes = [
        HasModuleGrant("fts"),
        HasPermission("fts.file.manage"),
        IsInstituteEmployee,
    ]

    @extend_schema(
        summary="Archive completed file",
        description="Archive a completed circulating file (owner only).",
        request=s.ArchiveFileSerializer,
        responses={
            200: s.FTSFileDetailSerializer,
            403: OpenApiResponse(description="Actor is not the file owner"),
            404: OpenApiResponse(description="File not found"),
            409: OpenApiResponse(description="File is not in circulating state"),
        },
    )
    def post(self, request, file_identifier: str):
        serializer = s.ArchiveFileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        p = request.principal
        is_employee = p.kind in ("faculty", "staff")
        is_admin = p.kind == "admin" or p.active_role in ("admin", "system_admin")

        file_obj = file_service.archive_file(
            file_id_or_pk=file_identifier,
            actor_id=p.user_id,
            actor_designation=p.active_role or "",
            remarks=data.get("remarks", ""),
            is_employee=is_employee,
            is_system_admin=is_admin,
        )
        return Response(s.FTSFileDetailSerializer(file_obj).data, status=status.HTTP_200_OK)


class UserSearchView(APIView):
    permission_classes = [HasModuleGrant("fts"), HasPermission("fts.file.view")]

    @extend_schema(
        summary="Search recipient employees",
        description="Lookup active faculty and staff members for file routing.",
        responses={200: OpenApiResponse(description="List of employee objects")},
    )
    def get(self, request):
        q = request.query_params.get("q", "").strip()
        users = directory.search(q=q, kind=None, limit=20)
        employees = [
            {
                "user_id": u.user_id,
                "username": u.username,
                "display_name": u.display_name,
                "kind": u.kind,
                "department": u.department,
            }
            for u in users
            if u.kind in ("faculty", "staff")
        ]
        return Response(employees, status=status.HTTP_200_OK)


class AuditLogListView(APIView):
    permission_classes = [HasModuleGrant("fts"), HasPermission("fts.audit.view")]

    @extend_schema(
        summary="View system audit logs",
        description="Governance audit log access for system administrators.",
        responses={200: s.FTSAuditLogSerializer(many=True)},
    )
    def get(self, request):
        actor_id_raw = request.query_params.get("actor_id")
        actor_id = None
        if actor_id_raw:
            if not actor_id_raw.isdigit():
                msg = "actor_id query parameter must be an integer."
                raise BadRequestError(msg, code="invalid_actor_id")
            actor_id = int(actor_id_raw)

        logs = scoping.get_system_audit_logs(actor_id=actor_id)
        serializer = s.FTSAuditLogSerializer(logs[:100], many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
