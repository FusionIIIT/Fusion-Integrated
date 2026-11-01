"""Role views for System Admin module."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasPermission, IsAuthenticatedPrincipal
from modules.system_admin.api.permissions import IsSuperAdminOperator
from modules.system_admin.api.serializers import (
    AssignRoleSerializer,
    ExtendRoleSerializer,
    ReassignRoleSerializer,
    RevokeRoleSerializer,
    RoleAssignmentReadSerializer,
    RoleDefinitionSerializer,
    SwitchActiveRoleSerializer,
)
from modules.system_admin.selectors import (
    list_role_assignments,
    list_role_definitions,
    list_vacant_singular_roles,
)
from modules.system_admin.services import (
    assign_role,
    extend_role_validity,
    reassign_role,
    revoke_role,
    switch_active_role,
)


class RoleDefinitionListView(APIView):
    permission_classes = [IsSuperAdminOperator, HasPermission("system_admin.role.view")]

    def get(self, request):
        module = request.query_params.get("module")
        roles = list_role_definitions(module=module)
        return Response(RoleDefinitionSerializer(roles, many=True).data)


class RoleVacanciesView(APIView):
    permission_classes = [IsSuperAdminOperator, HasPermission("system_admin.role.view")]

    def get(self, request):
        scope_type = request.query_params.get("scope_type", "institute")
        scope_id = request.query_params.get("scope_id", "")
        vacant = list_vacant_singular_roles(scope_type=scope_type, scope_id=scope_id)
        return Response(RoleDefinitionSerializer(vacant, many=True).data)


class RoleAssignmentListCreateView(APIView):
    permission_classes = [IsSuperAdminOperator, HasPermission("system_admin.role.view")]

    def get(self, request):
        user_id = request.query_params.get("user_id")
        role_code = request.query_params.get("role_code")
        st = request.query_params.get("status")

        assignments = list_role_assignments(
            user_id=int(user_id) if user_id and user_id.isdigit() else None,
            role_code=role_code,
            status=st,
        )
        return Response(RoleAssignmentReadSerializer(assignments[:100], many=True).data)

    def post(self, request):
        serializer = AssignRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assignment = assign_role(
            **serializer.validated_data,
            actor_user_id=getattr(request.principal, "erp_user_id", 0),
            actor_username=getattr(request.principal, "username", "super_admin"),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(RoleAssignmentReadSerializer(assignment).data, status=status.HTTP_201_CREATED)


class RoleReassignView(APIView):
    permission_classes = [IsSuperAdminOperator, HasPermission("system_admin.role.reassign")]

    def post(self, request, assignment_id: int):
        serializer = ReassignRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_a, new_a = reassign_role(
            current_assignment_id=assignment_id,
            new_user_id=serializer.validated_data["new_user_id"],
            effective_date=serializer.validated_data["effective_date"],
            reason=serializer.validated_data["reason"],
            audit_access_days=serializer.validated_data.get("audit_access_days", 30),
            actor_user_id=getattr(request.principal, "erp_user_id", 0),
            actor_username=getattr(request.principal, "username", "super_admin"),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response({
            "previous_assignment": RoleAssignmentReadSerializer(old_a).data,
            "new_assignment": RoleAssignmentReadSerializer(new_a).data,
        })


class RoleRevokeView(APIView):
    permission_classes = [IsSuperAdminOperator, HasPermission("system_admin.role.revoke")]

    def post(self, request, assignment_id: int):
        serializer = RevokeRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assignment = revoke_role(
            assignment_id=assignment_id,
            effective_date=serializer.validated_data["effective_date"],
            reason=serializer.validated_data["reason"],
            pending_task_disposition=serializer.validated_data.get("pending_task_disposition", "transfer"),
            is_emergency=serializer.validated_data.get("is_emergency", False),
            actor_user_id=getattr(request.principal, "erp_user_id", 0),
            actor_username=getattr(request.principal, "username", "super_admin"),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(RoleAssignmentReadSerializer(assignment).data)


class RoleExtendView(APIView):
    permission_classes = [IsSuperAdminOperator, HasPermission("system_admin.role.extend")]

    def post(self, request, assignment_id: int):
        serializer = ExtendRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assignment = extend_role_validity(
            assignment_id=assignment_id,
            new_end_date=serializer.validated_data["new_end_date"],
            reason=serializer.validated_data["reason"],
            actor_user_id=getattr(request.principal, "erp_user_id", 0),
            actor_username=getattr(request.principal, "username", "super_admin"),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(RoleAssignmentReadSerializer(assignment).data)


class ActiveRoleSwitchView(APIView):
    permission_classes = [IsAuthenticatedPrincipal]

    def post(self, request):
        serializer = SwitchActiveRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = getattr(request.principal, "erp_user_id", 0)
        context = switch_active_role(user_id, serializer.validated_data["role_code"])
        return Response(context)
