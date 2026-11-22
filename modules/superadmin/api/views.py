"""API Views for Super Admin module."""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.superadmin.api.permissions import RequiresStepUpAuth
from modules.superadmin.api.serializers import (
    AssignRoleSerializer,
    AuditLogSerializer,
    AuthorizePurgeSerializer,
    BulkOperationResultSerializer,
    BulkStatusUpdateSerializer,
    BulkUserCreateSerializer,
    CreateUserAccountSerializer,
    DashboardMetricsSerializer,
    ExtendRoleSerializer,
    HistoricalArchiveSerializer,
    PurgeRequestSerializer,
    ReassignRoleSerializer,
    RequestPurgeSerializer,
    RoleAssignmentSerializer,
    StatusReasonSerializer,
    SystemParameterSerializer,
    UpdateSystemParameterSerializer,
    UpdateUserProfileSerializer,
    UserAccountSerializer,
)
from modules.superadmin.models import UserAccountRecord
from modules.superadmin.selectors import (
    get_user_by_id,
    list_archives,
    list_audit_logs,
    list_purge_requests,
    list_roles,
    list_system_parameters,
    list_users,
)
from modules.superadmin.services import (
    archive_historical_data,
    archive_user,
    assign_role,
    authorize_permanent_purge,
    bulk_create_users,
    bulk_update_user_status,
    create_user_account,
    deactivate_user,
    extend_role_validity,
    reactivate_user,
    reassign_role_with_handover,
    request_permanent_purge,
    restore_archived_user,
    restore_historical_data,
    revoke_role,
    update_system_parameter,
    update_user_profile,
)


class UserListView(APIView):
    def get_permissions(self):
        perms = [HasModuleGrant("superadmin")]
        if self.request and self.request.method == "POST":
            perms.append(HasPermission("superadmin.user.create"))
        else:
            perms.append(HasPermission("superadmin.user.view"))
        return perms

    @extend_schema(
        summary="List user accounts",
        parameters=[
            OpenApiParameter("search", str, required=False),
            OpenApiParameter("user_type", str, required=False),
            OpenApiParameter("status", str, required=False),
        ],
        responses={200: UserAccountSerializer(many=True)},
    )
    def get(self, request):
        users = list_users(
            request.principal,
            search=request.query_params.get("search", ""),
            user_type=request.query_params.get("user_type", ""),
            status=request.query_params.get("status", ""),
        )
        return Response(UserAccountSerializer(users, many=True).data)

    @extend_schema(
        summary="Create new basic user account",
        request=CreateUserAccountSerializer,
        responses={201: UserAccountSerializer},
    )
    def post(self, request):
        serializer = CreateUserAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        account = create_user_account(
            actor_user_id=request.principal.user_id,
            user_id=d["user_id"],
            institute_id=d["institute_id"],
            email=d["email"],
            user_type=d["user_type"],
            department=d.get("department", ""),
            program=d.get("program", ""),
            batch=d.get("batch", ""),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(UserAccountSerializer(account).data, status=status.HTTP_201_CREATED)


class UserDetailView(APIView):
    def get_permissions(self):
        perms = [HasModuleGrant("superadmin")]
        if self.request and self.request.method in ("PATCH", "PUT"):
            perms.append(HasPermission("superadmin.user.update"))
        else:
            perms.append(HasPermission("superadmin.user.view"))
        return perms

    @extend_schema(summary="Get user account detail", responses={200: UserAccountSerializer})
    def get(self, request, user_id: int):
        account = get_user_by_id(request.principal, user_id)
        if not account:
            raise NotFoundError(f"User {user_id} not found.", code="user_not_found")
        return Response(UserAccountSerializer(account).data)

    @extend_schema(
        summary="Update editable profile fields",
        request=UpdateUserProfileSerializer,
        responses={200: UserAccountSerializer},
    )
    def patch(self, request, user_id: int):
        serializer = UpdateUserProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        account = update_user_profile(
            actor_user_id=request.principal.user_id,
            user_id=user_id,
            department=d.get("department"),
            program=d.get("program"),
            batch=d.get("batch"),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(UserAccountSerializer(account).data)


class UserDeactivateView(APIView):
    permission_classes = [
        HasModuleGrant("superadmin"),
        HasPermission("superadmin.user.delete"),
        RequiresStepUpAuth,
    ]
    throttle_scope = "superadmin_write"

    @extend_schema(
        summary="Deactivate user account",
        request=StatusReasonSerializer,
        responses={200: UserAccountSerializer},
    )
    def post(self, request, user_id: int):
        serializer = StatusReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = deactivate_user(
            actor_user_id=request.principal.user_id,
            user_id=user_id,
            reason=serializer.validated_data["reason"],
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(UserAccountSerializer(account).data)


class UserReactivateView(APIView):
    permission_classes = [HasModuleGrant("superadmin"), HasPermission("superadmin.user.restore")]
    throttle_scope = "superadmin_write"

    @extend_schema(
        summary="Reactivate deactivated user account",
        request=StatusReasonSerializer,
        responses={200: UserAccountSerializer},
    )
    def post(self, request, user_id: int):
        serializer = StatusReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = reactivate_user(
            actor_user_id=request.principal.user_id,
            user_id=user_id,
            reason=serializer.validated_data["reason"],
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(UserAccountSerializer(account).data)


class UserArchiveView(APIView):
    permission_classes = [
        HasModuleGrant("superadmin"),
        HasPermission("superadmin.archive.create"),
        RequiresStepUpAuth,
    ]
    throttle_scope = "superadmin_write"

    @extend_schema(
        summary="Archive deactivated user (BW-SA-08 Transition 1)",
        request=StatusReasonSerializer,
        responses={200: UserAccountSerializer},
    )
    def post(self, request, user_id: int):
        serializer = StatusReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = archive_user(
            actor_user_id=request.principal.user_id,
            user_id=user_id,
            reason=serializer.validated_data["reason"],
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(UserAccountSerializer(account).data)


class UserRestoreView(APIView):
    permission_classes = [
        HasModuleGrant("superadmin"),
        HasPermission("superadmin.archive.restore"),
        RequiresStepUpAuth,
    ]
    throttle_scope = "superadmin_write"

    @extend_schema(
        summary="Restore archived user within reversibility window (BW-SA-07)",
        request=StatusReasonSerializer,
        responses={200: UserAccountSerializer},
    )
    def post(self, request, user_id: int):
        serializer = StatusReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = restore_archived_user(
            actor_user_id=request.principal.user_id,
            user_id=user_id,
            reason=serializer.validated_data["reason"],
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(UserAccountSerializer(account).data)


class BulkUserCreateView(APIView):
    permission_classes = [
        HasModuleGrant("superadmin"),
        HasPermission("superadmin.user.import"),
        RequiresStepUpAuth,
    ]
    throttle_scope = "superadmin_write"

    @extend_schema(
        summary="Bulk create users from CSV data",
        request=BulkUserCreateSerializer,
        responses={200: BulkOperationResultSerializer},
    )
    def post(self, request):
        csv_file = request.FILES.get("file")
        if not csv_file:
            # Fall back to raw body text.
            csv_text = request.data.get("csv_data") or request.body.decode("utf-8")
        else:
            csv_text = csv_file.read().decode("utf-8")

        if not csv_text:
            raise BadRequestError("No CSV content provided.", code="empty_csv")

        result = bulk_create_users(
            actor_user_id=request.principal.user_id,
            csv_content=csv_text,
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(result)


class BulkUserStatusView(APIView):
    permission_classes = [
        HasModuleGrant("superadmin"),
        HasPermission("superadmin.user.update"),
        RequiresStepUpAuth,
    ]
    throttle_scope = "superadmin_write"

    @extend_schema(
        summary="Bulk update user activation statuses",
        request=BulkStatusUpdateSerializer,
        responses={200: BulkOperationResultSerializer},
    )
    def post(self, request):
        serializer = BulkStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        result = bulk_update_user_status(
            actor_user_id=request.principal.user_id,
            user_ids=d["user_ids"],
            target_status=d["target_status"],
            reason=d["reason"],
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(result)


class RoleListView(APIView):
    permission_classes = [HasModuleGrant("superadmin"), HasPermission("superadmin.role.view")]

    @extend_schema(
        summary="List role assignments",
        parameters=[
            OpenApiParameter("user_id", int, required=False),
            OpenApiParameter("role_name", str, required=False),
            OpenApiParameter("status", str, required=False),
        ],
        responses={200: RoleAssignmentSerializer(many=True)},
    )
    def get(self, request):
        uid = request.query_params.get("user_id")
        user_id_val = int(uid) if uid and uid.isdigit() else None
        roles = list_roles(
            request.principal,
            user_id=user_id_val,
            role_name=request.query_params.get("role_name", ""),
            status=request.query_params.get("status", ""),
        )
        return Response(RoleAssignmentSerializer(roles, many=True).data)

    @extend_schema(
        summary="Assign additional role",
        request=AssignRoleSerializer,
        responses={201: RoleAssignmentSerializer},
    )
    def post(self, request):
        serializer = AssignRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        assignment = assign_role(
            actor_user_id=request.principal.user_id,
            user_id=d["user_id"],
            role_name=d["role_name"],
            valid_from=d["valid_from"],
            valid_to=d.get("valid_to"),
            scope_type=d.get("scope_type", ""),
            scope_id=d.get("scope_id", ""),
            is_singular=d.get("is_singular", False),
            reason=d.get("reason", ""),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(RoleAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)


class RoleExtendView(APIView):
    permission_classes = [HasModuleGrant("superadmin"), HasPermission("superadmin.role.update")]
    throttle_scope = "superadmin_write"

    @extend_schema(
        summary="Extend role assignment validity",
        request=ExtendRoleSerializer,
        responses={200: RoleAssignmentSerializer},
    )
    def post(self, request, assignment_id: int):
        serializer = ExtendRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = extend_role_validity(
            actor_user_id=request.principal.user_id,
            assignment_id=assignment_id,
            new_valid_to=serializer.validated_data["new_valid_to"],
            reason=serializer.validated_data["reason"],
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(RoleAssignmentSerializer(assignment).data)


class RoleRevokeView(APIView):
    permission_classes = [
        HasModuleGrant("superadmin"),
        HasPermission("superadmin.role.revoke"),
        RequiresStepUpAuth,
    ]
    throttle_scope = "superadmin_write"

    @extend_schema(
        summary="Revoke held role assignment",
        request=StatusReasonSerializer,
        responses={200: RoleAssignmentSerializer},
    )
    def post(self, request, assignment_id: int):
        serializer = StatusReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = revoke_role(
            actor_user_id=request.principal.user_id,
            assignment_id=assignment_id,
            reason=serializer.validated_data["reason"],
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(RoleAssignmentSerializer(assignment).data)


class RoleReassignView(APIView):
    permission_classes = [HasModuleGrant("superadmin"), HasPermission("superadmin.role.assign")]
    throttle_scope = "superadmin_write"

    @extend_schema(
        summary="Reassign role with handover",
        request=ReassignRoleSerializer,
        responses={200: RoleAssignmentSerializer},
    )
    def post(self, request, assignment_id: int):
        serializer = ReassignRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        _, new_assignment = reassign_role_with_handover(
            actor_user_id=request.principal.user_id,
            assignment_id=assignment_id,
            successor_user_id=d["successor_user_id"],
            effective_date=d["effective_date"],
            handover_summary=d.get("handover_summary", ""),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(RoleAssignmentSerializer(new_assignment).data)


class ArchiveListView(APIView):
    permission_classes = [HasModuleGrant("superadmin"), HasPermission("superadmin.archive.view")]

    @extend_schema(
        summary="List historical archives", responses={200: HistoricalArchiveSerializer(many=True)}
    )
    def get(self, request):
        archives = list_archives(
            request.principal,
            entity_type=request.query_params.get("entity_type", ""),
            status=request.query_params.get("status", ""),
        )
        return Response(HistoricalArchiveSerializer(archives, many=True).data)

    @extend_schema(
        summary="Archive historical dataset",
        request=HistoricalArchiveSerializer,
        responses={201: HistoricalArchiveSerializer},
    )
    def post(self, request):
        record = archive_historical_data(
            actor_user_id=request.principal.user_id,
            entity_type=request.data.get("entity_type", ""),
            record_identifier=request.data.get("record_identifier", ""),
            payload=request.data.get("payload", {}),
            backup_reference=request.data.get("backup_reference", ""),
            retention_period_days=int(request.data.get("retention_period_days", 1825)),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(HistoricalArchiveSerializer(record).data, status=status.HTTP_201_CREATED)


class ArchiveRestoreView(APIView):
    permission_classes = [
        HasModuleGrant("superadmin"),
        HasPermission("superadmin.archive.restore"),
        RequiresStepUpAuth,
    ]
    throttle_scope = "superadmin_write"

    @extend_schema(
        summary="Restore archived historical dataset",
        request=StatusReasonSerializer,
        responses={200: HistoricalArchiveSerializer},
    )
    def post(self, request, archive_id: int):
        serializer = StatusReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = restore_historical_data(
            actor_user_id=request.principal.user_id,
            archive_id=archive_id,
            reason=serializer.validated_data["reason"],
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(HistoricalArchiveSerializer(record).data)


class PurgeRequestListView(APIView):
    permission_classes = [HasModuleGrant("superadmin"), HasPermission("superadmin.purge.create")]
    throttle_scope = "superadmin_write"

    @extend_schema(
        summary="List purge requests", responses={200: PurgeRequestSerializer(many=True)}
    )
    def get(self, request):
        reqs = list_purge_requests(request.principal, status=request.query_params.get("status", ""))
        return Response(PurgeRequestSerializer(reqs, many=True).data)

    @extend_schema(
        summary="Request permanent data purge",
        request=RequestPurgeSerializer,
        responses={201: PurgeRequestSerializer},
    )
    def post(self, request):
        archive_id = int(request.data.get("archive_id", 0))
        reason = request.data.get("reason", "")
        req = request_permanent_purge(
            actor_user_id=request.principal.user_id,
            archive_id=archive_id,
            reason=reason,
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(PurgeRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class PurgeAuthorizeView(APIView):
    # UC-SA-023: IT Head dual-authorization for permanent purge.
    permission_classes = [
        HasModuleGrant("superadmin"),
        HasPermission("superadmin.purge.approve"),
        RequiresStepUpAuth,
    ]
    throttle_scope = "superadmin_write"

    @extend_schema(
        summary="Authorize or reject purge request",
        request=AuthorizePurgeSerializer,
        responses={200: PurgeRequestSerializer},
    )
    def post(self, request, request_id: int):
        serializer = AuthorizePurgeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        req = authorize_permanent_purge(
            actor_user_id=request.principal.user_id,
            request_id=request_id,
            action=d["action"],
            rejection_reason=d.get("reason", ""),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(PurgeRequestSerializer(req).data)


class AuditLogListView(APIView):
    permission_classes = [HasModuleGrant("superadmin"), HasPermission("superadmin.audit_log.view")]

    @extend_schema(
        summary="List immutable audit logs", responses={200: AuditLogSerializer(many=True)}
    )
    def get(self, request):
        logs = list_audit_logs(
            request.principal,
            event_type=request.query_params.get("event_type", ""),
            target_entity=request.query_params.get("target_entity", ""),
        )
        return Response(AuditLogSerializer(logs, many=True).data)


class SystemParameterListView(APIView):
    def get_permissions(self):
        perms = [HasModuleGrant("superadmin")]
        if self.request and self.request.method == "POST":
            perms.append(HasPermission("superadmin.system_config.update"))
        else:
            perms.append(HasPermission("superadmin.system_config.view"))
        return perms

    @extend_schema(
        summary="List active system parameters",
        responses={200: SystemParameterSerializer(many=True)},
    )
    def get(self, request):
        params = list_system_parameters(request.principal)
        return Response(SystemParameterSerializer(params, many=True).data)

    @extend_schema(
        summary="Configure versioned system parameter",
        request=UpdateSystemParameterSerializer,
        responses={201: SystemParameterSerializer},
    )
    def post(self, request):
        serializer = UpdateSystemParameterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        param = update_system_parameter(
            actor_user_id=request.principal.user_id,
            parameter_key=d["parameter_key"],
            parameter_value=d["parameter_value"],
            effective_from=d.get("effective_from"),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(SystemParameterSerializer(param).data, status=status.HTTP_201_CREATED)


class UserExportView(APIView):
    permission_classes = [HasModuleGrant("superadmin"), HasPermission("superadmin.user.export")]

    @extend_schema(
        summary="Export user accounts directory", responses={200: UserAccountSerializer(many=True)}
    )
    def get(self, request):
        users = list_users(
            request.principal,
            search=request.query_params.get("search", ""),
            user_type=request.query_params.get("user_type", ""),
            status=request.query_params.get("status", ""),
        )
        return Response(UserAccountSerializer(users, many=True).data)


class ArchiveExportView(APIView):
    permission_classes = [HasModuleGrant("superadmin"), HasPermission("superadmin.archive.export")]

    @extend_schema(
        summary="Export historical archives",
        responses={200: HistoricalArchiveSerializer(many=True)},
    )
    def get(self, request):
        archives = list_archives(
            request.principal,
            entity_type=request.query_params.get("entity_type", ""),
            status=request.query_params.get("status", ""),
        )
        return Response(HistoricalArchiveSerializer(archives, many=True).data)


class AuditLogExportView(APIView):
    permission_classes = [
        HasModuleGrant("superadmin"),
        HasPermission("superadmin.audit_log.export"),
    ]

    @extend_schema(
        summary="Export immutable audit logs", responses={200: AuditLogSerializer(many=True)}
    )
    def get(self, request):
        logs = list_audit_logs(
            request.principal,
            event_type=request.query_params.get("event_type", ""),
            target_entity=request.query_params.get("target_entity", ""),
        )
        return Response(AuditLogSerializer(logs, many=True).data)


class DashboardMetricsView(APIView):
    permission_classes = [HasModuleGrant("superadmin"), HasPermission("superadmin.user.view")]

    @extend_schema(
        summary="Administrative dashboard metrics", responses={200: DashboardMetricsSerializer}
    )
    def get(self, request):
        total_users = UserAccountRecord.objects.count()
        active_users = UserAccountRecord.objects.filter(activation_status="ACTIVE").count()
        deactivated = UserAccountRecord.objects.filter(activation_status="DEACTIVATED").count()
        archived_rev = UserAccountRecord.objects.filter(
            activation_status="ARCHIVED_REVERSIBLE"
        ).count()
        archived_perm = UserAccountRecord.objects.filter(
            activation_status="ARCHIVED_PERMANENT"
        ).count()

        return Response(
            {
                "total_users": total_users,
                "active_users": active_users,
                "deactivated_users": deactivated,
                "archived_reversible_users": archived_rev,
                "archived_permanent_users": archived_perm,
            }
        )
