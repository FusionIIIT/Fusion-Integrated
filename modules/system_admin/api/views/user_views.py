"""User management API views."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.system_admin.api.serializers import (
    BulkCreateResultSerializer,
    BulkCreateUsersSerializer,
    CreateUserSerializer,
    UpdateUserSerializer,
    UserAccountSerializer,
    UserStatusSerializer,
)
from modules.system_admin.domain.exceptions import (
    DomainValidationError,
    DuplicateUserError,
    SystemAdminDomainError,
    UserNotFoundError,
)
from modules.system_admin.selectors.user_selectors import get_user_by_id, list_users
from modules.system_admin.services.user_service import (
    bulk_create_users,
    create_basic_user,
    deactivate_user,
    reactivate_user,
    update_user_profile,
)

MODULE = HasModuleGrant("system_admin")


def _actor_id(request) -> int:
    principal = getattr(request, "principal", None)
    return getattr(principal, "user_id", 1) or 1


def _ip(request) -> str | None:
    return request.META.get("REMOTE_ADDR")


class UserListView(APIView):
    permission_classes = [MODULE, HasPermission("system_admin.user.view")]
    serializer_class = UserAccountSerializer

    @extend_schema(responses={200: UserAccountSerializer(many=True)})
    def get(self, request):
        query = request.query_params.get("q")
        user_type = request.query_params.get("user_type")
        usr_status = request.query_params.get("status")
        department = request.query_params.get("department")
        limit = min(int(request.query_params.get("limit", 50)), 100)
        offset = max(int(request.query_params.get("offset", 0)), 0)

        users, total = list_users(
            query=query,
            user_type=user_type,
            status=usr_status,
            department=department,
            limit=limit,
            offset=offset,
        )
        return Response({
            "results": UserAccountSerializer(users, many=True).data,
            "total": total,
            "limit": limit,
            "offset": offset,
        })

    def post(self, request):
        return UserCreateView().post(request)


class UserCreateView(APIView):
    permission_classes = [MODULE, HasPermission("system_admin.user.add")]

    @extend_schema(request=CreateUserSerializer, responses={201: UserAccountSerializer})
    def post(self, request):
        serializer = CreateUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            user = create_basic_user(
                institute_id=data["institute_id"],
                username=data["username"],
                email=data["email"],
                user_type=data["user_type"],
                name=data.get("name", ""),
                contact_number=data.get("contact_number", ""),
                department=data.get("department", ""),
                programme=data.get("programme", ""),
                discipline=data.get("discipline", ""),
                batch_year=data.get("batch_year"),
                user_id=data.get("user_id"),
                actor_id=_actor_id(request),
                ip_address=_ip(request),
            )
        except (DuplicateUserError, DomainValidationError, SystemAdminDomainError) as e:
            raise BadRequestError(str(e)) from e

        return Response(UserAccountSerializer(user).data, status=status.HTTP_201_CREATED)


class UserDetailView(APIView):
    permission_classes = [MODULE]

    @extend_schema(responses={200: UserAccountSerializer})
    def get(self, request, user_id: int):
        self.check_permissions(request)
        if not HasPermission("system_admin.user.view")().has_permission(request, self):
            return Response(
                {"detail": "Permission denied: system_admin.user.view required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        user = get_user_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found.")
        return Response(UserAccountSerializer(user).data)

    @extend_schema(request=UpdateUserSerializer, responses={200: UserAccountSerializer})
    def patch(self, request, user_id: int):
        self.check_permissions(request)
        if not HasPermission("system_admin.user.change")().has_permission(request, self):
            return Response(
                {"detail": "Permission denied: system_admin.user.change required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = UpdateUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = update_user_profile(
                user_id=user_id,
                data=serializer.validated_data,
                actor_id=_actor_id(request),
                ip_address=_ip(request),
            )
        except UserNotFoundError as e:
            raise NotFoundError(str(e)) from e
        except (DomainValidationError, SystemAdminDomainError) as e:
            raise BadRequestError(str(e)) from e

        return Response(UserAccountSerializer(user).data)


class UserStatusView(APIView):
    permission_classes = [MODULE, HasPermission("system_admin.user.change")]
    serializer_class = UserStatusSerializer

    @extend_schema(request=UserStatusSerializer, responses={200: UserAccountSerializer})
    def post(self, request, user_id: int | None = None, pk: int | None = None):
        uid = user_id if user_id is not None else pk
        serializer = UserStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data["action"]
        reason = serializer.validated_data.get("reason", "Status change")

        curr_user = get_user_by_id(uid)
        if not curr_user:
            raise NotFoundError(f"User {uid} not found.")

        try:
            if curr_user.status == "archived":
                from datetime import UTC, datetime, timedelta

                from modules.system_admin.models.archive import ArchivedUserRecord
                from modules.system_admin.services.archive_service import restore_archived_user
                ArchivedUserRecord.objects.get_or_create(
                    user_id=uid,
                    defaults={
                        "institute_id": curr_user.institute_id,
                        "username": curr_user.username,
                        "email": curr_user.email,
                        "user_type": curr_user.user_type,
                        "reason": "Archived",
                        "archived_by": 1,
                        "archived_at": datetime.now(UTC),
                        "reversible_until": datetime.now(UTC) + timedelta(days=90),
                        "is_permanent": False,
                        "snapshot": {},
                    },
                )
                restore_archived_user(
                    user_id=uid,
                    reason=reason,
                    actor_id=_actor_id(request),
                    ip_address=_ip(request),
                )
                if action in ("deactivate", "deactivated"):
                    u_obj = get_user_by_id(uid)
                    u_obj.status = "deactivated"
                    u_obj.save(update_fields=["status", "updated_at"])
                user = get_user_by_id(uid)
            elif action in ("deactivate", "deactivated", "suspend", "suspended"):
                user = deactivate_user(
                    user_id=uid,
                    reason=reason,
                    actor_id=_actor_id(request),
                    ip_address=_ip(request),
                )
            elif action in ("archive", "archived"):
                from modules.system_admin.services.archive_service import archive_user
                archive_user(
                    user_id=uid,
                    reason=reason,
                    actor_id=_actor_id(request),
                    ip_address=_ip(request),
                )
                user = get_user_by_id(uid)
            else:
                user = reactivate_user(
                    user_id=uid,
                    reason=reason,
                    actor_id=_actor_id(request),
                    ip_address=_ip(request),
                )
        except UserNotFoundError as e:
            raise NotFoundError(str(e)) from e
        except (DomainValidationError, SystemAdminDomainError) as e:
            raise BadRequestError(str(e)) from e

        return Response(UserAccountSerializer(user).data)

    @extend_schema(request=UserStatusSerializer, responses={200: UserAccountSerializer})
    def patch(self, request, user_id: int | None = None, pk: int | None = None):
        return self.post(request, user_id=user_id, pk=pk)


class UserBulkCreateView(APIView):
    permission_classes = [MODULE, HasPermission("system_admin.user.add")]

    @extend_schema(
        request=BulkCreateUsersSerializer,
        responses={201: BulkCreateResultSerializer},
    )
    def post(self, request):
        serializer = BulkCreateUsersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rows = serializer.validated_data["users"]

        try:
            result = bulk_create_users(
                rows=rows,
                actor_id=_actor_id(request),
                ip_address=_ip(request),
            )
        except (DomainValidationError, SystemAdminDomainError) as e:
            raise BadRequestError(str(e)) from e

        return Response(result, status=status.HTTP_201_CREATED)
