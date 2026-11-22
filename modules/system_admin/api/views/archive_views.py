"""Archival, restoration, and permanent purge views."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.system_admin.api.serializers import (
    ArchivedUserSerializer,
    ArchiveUserActionSerializer,
    CreatePurgeRequestSerializer,
    HistoricalDatasetSerializer,
    PurgeAuthorizeSerializer,
    PurgeRequestSerializer,
    RestoreUserActionSerializer,
    UserAccountSerializer,
)
from modules.system_admin.domain.exceptions import (
    ArchivalReversibilityExpiredError,
    DomainValidationError,
    PurgeDualAuthError,
    RetentionNotElapsedError,
    UserNotEligibleForArchivalError,
    UserNotFoundError,
)
from modules.system_admin.selectors.archive_selectors import (
    list_archived_users,
    list_historical_archives,
    list_purge_requests,
)
from modules.system_admin.services.archive_service import (
    archive_historical_dataset,
    archive_user,
    authorize_permanent_purge,
    request_permanent_purge,
    restore_archived_user,
)

MODULE = HasModuleGrant("system_admin")


def _actor_id(request) -> int:
    principal = getattr(request, "principal", None)
    return getattr(principal, "user_id", 1) or 1


def _ip(request) -> str | None:
    return request.META.get("REMOTE_ADDR")


class ArchiveListView(APIView):
    permission_classes = [MODULE, HasPermission("system_admin.archive.view")]

    @extend_schema(responses={200: ArchivedUserSerializer(many=True)})
    def get(self, request):
        mode = request.query_params.get("mode")
        if mode == "datasets":
            datasets = list_historical_archives()
            return Response(HistoricalDatasetSerializer(datasets, many=True).data)
        if mode == "purge_requests":
            purges = list_purge_requests()
            return Response(PurgeRequestSerializer(purges, many=True).data)

        query = request.query_params.get("q")
        user_type = request.query_params.get("user_type")
        retention = request.query_params.get("retention_option")
        limit = min(int(request.query_params.get("limit", 50)), 100)
        offset = max(int(request.query_params.get("offset", 0)), 0)

        records, total = list_archived_users(
            query=query,
            user_type=user_type,
            retention_option=retention,
            limit=limit,
            offset=offset,
        )
        return Response({
            "results": ArchivedUserSerializer(records, many=True).data,
            "total": total,
            "limit": limit,
            "offset": offset,
        })


class ArchiveUserView(APIView):
    permission_classes = [MODULE, HasPermission("system_admin.archive.manage")]

    @extend_schema(request=ArchiveUserActionSerializer, responses={201: ArchivedUserSerializer})
    def post(self, request):
        serializer = ArchiveUserActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            record = archive_user(
                user_id=data["user_id"],
                reason=data["reason"],
                retention_option=data.get("retention_option", "standard_7yr"),
                reversible_days=data.get("reversible_days", 90),
                actor_id=_actor_id(request),
                ip_address=_ip(request),
            )
        except UserNotFoundError as e:
            raise NotFoundError(str(e)) from e
        except (UserNotEligibleForArchivalError, DomainValidationError) as e:
            raise BadRequestError(str(e)) from e

        return Response(ArchivedUserSerializer(record).data, status=status.HTTP_201_CREATED)


class RestoreUserView(APIView):
    permission_classes = [MODULE, HasPermission("system_admin.archive.manage")]

    @extend_schema(request=RestoreUserActionSerializer, responses={200: UserAccountSerializer})
    def post(self, request, user_id: int):
        serializer = RestoreUserActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            user = restore_archived_user(
                user_id=user_id,
                reason=data["reason"],
                actor_id=_actor_id(request),
                ip_address=_ip(request),
            )
        except ArchivalReversibilityExpiredError as e:
            raise BadRequestError(str(e)) from e
        except DomainValidationError as e:
            raise BadRequestError(str(e)) from e

        return Response(UserAccountSerializer(user).data)


class ArchiveDatasetView(APIView):
    permission_classes = [MODULE, HasPermission("system_admin.archive.manage")]

    @extend_schema(
        request=HistoricalDatasetSerializer,
        responses={201: HistoricalDatasetSerializer},
    )
    def post(self, request):
        serializer = HistoricalDatasetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            dataset = archive_historical_dataset(
                category=data["category"],
                description=data["description"],
                date_range_start=data["date_range_start"],
                date_range_end=data["date_range_end"],
                backup_reference=data["backup_reference"],
                record_count=data.get("record_count", 0),
                actor_id=_actor_id(request),
                ip_address=_ip(request),
            )
        except DomainValidationError as e:
            raise BadRequestError(str(e)) from e

        return Response(
            HistoricalDatasetSerializer(dataset).data,
            status=status.HTTP_201_CREATED,
        )


class PurgeRequestView(APIView):
    permission_classes = [MODULE, HasPermission("system_admin.archive.manage")]

    @extend_schema(request=CreatePurgeRequestSerializer, responses={201: PurgeRequestSerializer})
    def post(self, request):
        serializer = CreatePurgeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            purge_req = request_permanent_purge(
                dataset_identifier=data["dataset_identifier"],
                retention_years=data["retention_years"],
                reason=data["reason"],
                actor_id=_actor_id(request),
                ip_address=_ip(request),
            )
        except RetentionNotElapsedError as e:
            raise BadRequestError(str(e)) from e
        except DomainValidationError as e:
            raise BadRequestError(str(e)) from e

        return Response(
            PurgeRequestSerializer(purge_req).data,
            status=status.HTTP_201_CREATED,
        )


class PurgeAuthorizeView(APIView):
    permission_classes = [MODULE, HasPermission("system_admin.archive.manage")]

    @extend_schema(request=PurgeAuthorizeSerializer, responses={200: PurgeRequestSerializer})
    def post(self, request, purge_id: int):
        serializer = PurgeAuthorizeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            decided = authorize_permanent_purge(
                purge_request_id=purge_id,
                approve=data["approve"],
                it_head_user_id=_actor_id(request),
                remarks=data.get("remarks", ""),
                ip_address=_ip(request),
            )
        except PurgeDualAuthError as e:
            raise ConflictError(str(e)) from e
        except DomainValidationError as e:
            raise BadRequestError(str(e)) from e

        return Response(PurgeRequestSerializer(decided).data)
