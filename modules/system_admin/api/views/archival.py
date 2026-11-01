"""Archival views for System Admin module."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasPermission
from modules.system_admin.api.permissions import (
    IsITHeadAuthorizer,
    IsSuperAdminOperator,
)
from modules.system_admin.api.serializers import (
    ArchivedRecordReadSerializer,
    ArchiveHistoricalDataSerializer,
    ArchiveUserRequestSerializer,
    AuthorizePurgeSerializer,
    BasicUserReadSerializer,
    PurgeRequestReadSerializer,
    RequestPurgeSerializer,
    RestoreUserRequestSerializer,
)
from modules.system_admin.selectors import (
    list_archived_records,
    list_archived_users,
    list_purge_requests,
)
from modules.system_admin.services import (
    archive_historical_data,
    archive_user,
    authorize_permanent_purge,
    request_permanent_purge,
    restore_archived_user,
    restore_historical_data,
)


class ArchivedRecordListView(APIView):
    permission_classes = [IsSuperAdminOperator, HasPermission("system_admin.archive.view")]

    def get(self, request):
        cat = request.query_params.get("category")
        records = list_archived_records(category=cat)
        return Response(ArchivedRecordReadSerializer(records[:100], many=True).data)


class ArchivedUserListView(APIView):
    permission_classes = [IsSuperAdminOperator, HasPermission("system_admin.archive.view")]

    def get(self, request):
        user_type = request.query_params.get("user_type")
        department = request.query_params.get("department")
        search = request.query_params.get("search")

        users = list_archived_users(user_type=user_type, department=department, search=search)
        return Response(BasicUserReadSerializer(users[:100], many=True).data)


class ArchiveUserActionView(APIView):
    permission_classes = [IsSuperAdminOperator, HasPermission("system_admin.archive.create")]

    def post(self, request, user_id: int):
        serializer = ArchiveUserRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user, archive = archive_user(
            user_id=user_id,
            retention_years=serializer.validated_data.get("retention_years", 7),
            reversible_window_days=serializer.validated_data.get("reversible_window_days", 180),
            reason=serializer.validated_data["reason"],
            reauthenticated=serializer.validated_data.get("reauthenticated", True),
            actor_user_id=getattr(request.principal, "erp_user_id", 0),
            actor_username=getattr(request.principal, "username", "super_admin"),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response({
            "user": BasicUserReadSerializer(user).data,
            "archive": ArchivedRecordReadSerializer(archive).data,
        })


class RestoreUserActionView(APIView):
    permission_classes = [IsSuperAdminOperator, HasPermission("system_admin.archive.restore")]

    def post(self, request, user_id: int):
        serializer = RestoreUserRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = restore_archived_user(
            user_id=user_id,
            reason=serializer.validated_data["reason"],
            reauthenticated=serializer.validated_data.get("reauthenticated", True),
            actor_user_id=getattr(request.principal, "erp_user_id", 0),
            actor_username=getattr(request.principal, "username", "super_admin"),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(BasicUserReadSerializer(user).data)


class ArchiveHistoricalDataView(APIView):
    permission_classes = [IsSuperAdminOperator, HasPermission("system_admin.archive.create")]

    def post(self, request):
        serializer = ArchiveHistoricalDataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        record = archive_historical_data(
            category=serializer.validated_data["category"],
            identifier=serializer.validated_data["identifier"],
            data_payload=serializer.validated_data["data_payload"],
            retention_years=serializer.validated_data.get("retention_years", 7),
            backup_reference=serializer.validated_data.get("backup_reference", ""),
            reason=serializer.validated_data.get("reason", ""),
            reauthenticated=serializer.validated_data.get("reauthenticated", True),
            actor_user_id=getattr(request.principal, "erp_user_id", 0),
            actor_username=getattr(request.principal, "username", "super_admin"),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(ArchivedRecordReadSerializer(record).data, status=status.HTTP_201_CREATED)


class RestoreHistoricalDataView(APIView):
    permission_classes = [IsSuperAdminOperator, HasPermission("system_admin.archive.restore")]

    def post(self, request, archive_id: int):
        reason = request.data.get("reason", "")
        reauthenticated = request.data.get("reauthenticated", True)

        record = restore_historical_data(
            archive_id=archive_id,
            reason=reason,
            reauthenticated=reauthenticated,
            actor_user_id=getattr(request.principal, "erp_user_id", 0),
            actor_username=getattr(request.principal, "username", "super_admin"),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(ArchivedRecordReadSerializer(record).data)


class PurgeRequestListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsSuperAdminOperator(), HasPermission("system_admin.purge.request")()]
        return [IsSuperAdminOperator(), HasPermission("system_admin.archive.view")()]

    def get(self, request):
        reqs = list_purge_requests()
        return Response(PurgeRequestReadSerializer(reqs, many=True).data)

    def post(self, request):
        serializer = RequestPurgeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        req = request_permanent_purge(
            archive_id=serializer.validated_data["archive_id"],
            reason=serializer.validated_data["reason"],
            reauthenticated=serializer.validated_data.get("reauthenticated", True),
            actor_user_id=getattr(request.principal, "erp_user_id", 0),
            actor_username=getattr(request.principal, "username", "super_admin"),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(PurgeRequestReadSerializer(req).data, status=status.HTTP_201_CREATED)


class PurgeAuthorizeView(APIView):
    permission_classes = [IsITHeadAuthorizer]

    def post(self, request, request_id: int):
        serializer = AuthorizePurgeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        req = authorize_permanent_purge(
            purge_request_id=request_id,
            decision=serializer.validated_data["decision"],
            it_head_user_id=getattr(request.principal, "erp_user_id", 1),
            it_head_username=getattr(request.principal, "username", "it_head"),
            rejection_reason=serializer.validated_data.get("rejection_reason", ""),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(PurgeRequestReadSerializer(req).data)
