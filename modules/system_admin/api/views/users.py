"""User views for System Admin module."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.system_admin.api.permissions import IsSuperAdminOperator
from modules.system_admin.api.serializers import (
    BasicUserCreateSerializer,
    BasicUserReadSerializer,
    BasicUserUpdateSerializer,
    BulkOperationLogSerializer,
    BulkStatusUpdateSerializer,
    BulkUserCreateSerializer,
    UserStatusActionSerializer,
)
from modules.system_admin.selectors import (
    get_user_by_id,
    list_basic_users,
)
from modules.system_admin.services import (
    bulk_create_users,
    bulk_status_update,
    create_basic_user,
    deactivate_user,
    reactivate_user,
    update_user_profile,
)


class UserListCreateView(APIView):
    permission_classes = [IsSuperAdminOperator, HasPermission("system_admin.user.view")]

    def get(self, request):
        user_type = request.query_params.get("user_type")
        usr_status = request.query_params.get("status")
        department = request.query_params.get("department")
        batch_year = request.query_params.get("batch_year")
        q = request.query_params.get("q")

        users = list_basic_users(
            user_type=user_type,
            status=usr_status,
            department=department,
            batch_year=int(batch_year) if batch_year and batch_year.isdigit() else None,
            q=q,
        )
        serializer = BasicUserReadSerializer(users[:100], many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = BasicUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = create_basic_user(
            **serializer.validated_data,
            actor_user_id=getattr(request.principal, "erp_user_id", 0),
            actor_username=getattr(request.principal, "username", "super_admin"),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(BasicUserReadSerializer(user).data, status=status.HTTP_201_CREATED)


class UserDetailView(APIView):
    permission_classes = [IsSuperAdminOperator, HasPermission("system_admin.user.view")]

    def get(self, request, user_id: int):
        user = get_user_by_id(user_id)
        if not user:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(BasicUserReadSerializer(user).data)

    def patch(self, request, user_id: int):
        serializer = BasicUserUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = dict(serializer.validated_data)
        reason = data.pop("reason", "")

        user = update_user_profile(
            user_id=user_id,
            actor_user_id=getattr(request.principal, "erp_user_id", 0),
            actor_username=getattr(request.principal, "username", "super_admin"),
            fields_to_update=data,
            reason=reason,
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(BasicUserReadSerializer(user).data)


class UserDeactivateView(APIView):
    permission_classes = [IsSuperAdminOperator, HasPermission("system_admin.user.deactivate")]

    def post(self, request, user_id: int):
        serializer = UserStatusActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = deactivate_user(
            user_id=user_id,
            actor_user_id=getattr(request.principal, "erp_user_id", 0),
            actor_username=getattr(request.principal, "username", "super_admin"),
            reason=serializer.validated_data["reason"],
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(BasicUserReadSerializer(user).data)


class UserReactivateView(APIView):
    permission_classes = [IsSuperAdminOperator, HasPermission("system_admin.user.reactivate")]

    def post(self, request, user_id: int):
        serializer = UserStatusActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = reactivate_user(
            user_id=user_id,
            actor_user_id=getattr(request.principal, "erp_user_id", 0),
            actor_username=getattr(request.principal, "username", "super_admin"),
            reason=serializer.validated_data["reason"],
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(BasicUserReadSerializer(user).data)


class BulkUserCreateView(APIView):
    permission_classes = [IsSuperAdminOperator, HasPermission("system_admin.user.bulk_manage")]

    def post(self, request):
        serializer = BulkUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        log_entry = bulk_create_users(
            records=serializer.validated_data["records"],
            actor_user_id=getattr(request.principal, "erp_user_id", 0),
            actor_username=getattr(request.principal, "username", "super_admin"),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(BulkOperationLogSerializer(log_entry).data, status=status.HTTP_201_CREATED)


class BulkUserStatusUpdateView(APIView):
    permission_classes = [IsSuperAdminOperator, HasPermission("system_admin.user.bulk_manage")]

    def post(self, request):
        serializer = BulkStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        log_entry = bulk_status_update(
            user_ids=serializer.validated_data["user_ids"],
            target_status=serializer.validated_data["target_status"],
            reason=serializer.validated_data["reason"],
            actor_user_id=getattr(request.principal, "erp_user_id", 0),
            actor_username=getattr(request.principal, "username", "super_admin"),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(BulkOperationLogSerializer(log_entry).data, status=status.HTTP_200_OK)
